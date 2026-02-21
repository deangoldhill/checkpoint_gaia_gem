import aiohttp
import logging
import json
import base64
import asyncio

_LOGGER = logging.getLogger(__name__)

class CheckpointGaiaAPI:
    def __init__(self, host, port, username, password):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        # Correctly pointing to the Gaia API path, not the Management API
        self.base_url = f"https://{host}:{port}/gaia_api"
        self.sid = None

    async def _request(self, session, endpoint, payload=None):
        url = f"{self.base_url}/{endpoint}"
        headers = {"Content-Type": "application/json"}
        if self.sid:
            headers["X-chkp-sid"] = self.sid

        # Ensure ssl=False if using a self-signed firewall cert
        async with session.post(url, json=payload or {}, headers=headers, ssl=False) as response:
            response.raise_for_status()
            return await response.json()

    async def login(self, session):
        """Authenticate against the Gaia API."""
        data = await self._request(session, "login", {
            "user": self.username, 
            "password": self.password
        })
        self.sid = data.get("sid")

    async def logout(self, session):
        """Close the Gaia API session."""
        if self.sid:
            await self._request(session, "logout")
            self.sid = None

    async def get_metrics(self, session):
        """Fetches firewall metrics using Gaia API's run-script."""
        
        # A lightweight shell script payload to retrieve the 6 specific metrics you requested
        script = """
        echo '{'
        echo '"cpu_usage": "'$(cpstat os -f perf | awk '/CPU Usage/ {print $3}')'",'
        echo '"memory_usage": "'$(cpstat os -f perf | awk '/Memory Usage/ {print $3}')'",'
        echo '"connections": "'$(fw tab -t connections -s | awk 'NR==2 {print $4}')'",'
        echo '"cps": "'$(cpstat os -f perf | awk '/Connections\\/Sec/ {print $2}')'",'
        echo '"vpn_status": "'$(cpstat vpn -f product | awk '/Product Status/ {print $3}')'",'
        echo '"blade_versions": "'$(cpinfo -y all | grep -i "content version" | head -n 1 | sed 's/.*: //')'"'
        echo '}'
        """
        
        # 1. Start the script task
        payload = {"script": script}
        try:
            response = await self._request(session, "run-script", payload)
        except Exception as e:
            _LOGGER.error("Failed to execute run-script on Gaia API: %s", e)
            return {}

        task_id = response.get("task-id")
        if not task_id:
            _LOGGER.error("No task-id returned from Gaia API")
            return {}
            
        # 2. Poll the show-task endpoint until execution finishes (max 20 seconds)
        for _ in range(10):
            await asyncio.sleep(2)
            try:
                task_response = await self._request(session, "show-task", {"task-id": task_id})
            except Exception:
                continue
                
            tasks = task_response.get("tasks", [])
            if not tasks:
                continue
                
            task = tasks[0]
            status = task.get("status")
            
            # 3. Handle completion and Base64 Decode the payload
            if status == "succeeded":
                try:
                    # The Gaia API returns script outputs heavily nested and base64 encoded
                    b64_output = task["task-details"][0]["output"]
                    raw_output = base64.b64decode(b64_output).decode('utf-8').strip()
                    
                    return json.loads(raw_output)
                except (KeyError, json.JSONDecodeError, base64.binascii.Error) as e:
                    _LOGGER.error("Failed to parse base64 Gaia API output. Error: %s", e)
                    return {}
            
            elif status in ["failed", "partially succeeded"]:
                _LOGGER.error("Gaia API run-script task failed: %s", task.get("progress-description"))
                return {}
                
        _LOGGER.error("Gaia API run-script task timed out")
        return {}
