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
        self.base_url = f"https://{host}:{port}/gaia_api"
        self.sid = None

    async def _request(self, session, endpoint, payload=None):
        url = f"{self.base_url}/{endpoint}"
        headers = {"Content-Type": "application/json"}
        if self.sid:
            headers["X-chkp-sid"] = self.sid

        async with session.post(url, json=payload or {}, headers=headers, ssl=False) as response:
            response.raise_for_status()
            return await response.json()

    async def login(self, session):
        """Gaia API Login"""
        data = await self._request(session, "login", {
            "user": self.username, 
            "password": self.password
        })
        self.sid = data.get("sid")

    async def logout(self, session):
        """Gaia API Logout"""
        if self.sid:
            await self._request(session, "logout")
            self.sid = None

    async def get_metrics(self, session):
        """Execute Bash script via Gaia API and parse Base64 output"""
        
        # Updated script: Uses colon delimiters to safely extract values
        script = """
        echo '{'
        echo '"cpu_usage": "'$(cpstat os -f perf 2>/dev/null | grep "CPU Usage" | awk -F: '{print $2}' | awk '{print $1}')'",'
        echo '"memory_usage": "'$(cpstat os -f perf 2>/dev/null | grep "Memory Usage" | awk -F: '{print $2}' | awk '{print $1}')'",'
        echo '"connections": "'$(fw tab -t connections -s 2>/dev/null | awk 'NR==2 {print $4}')'",'
        echo '"cps": "'$(cpstat os -f perf 2>/dev/null | grep "Connections/Sec" | awk -F: '{print $2}' | awk '{print $1}')'",'
        echo '"vpn_status": "'$(cpstat vpn -f product 2>/dev/null | grep "Product Status" | awk -F: '{print $2}' | sed 's/^ *//')'",'
        echo '"blade_versions": "'$(cpinfo -y all 2>/dev/null | grep -i "content version" | head -n 1 | awk -F: '{print $2}' | sed 's/^ *//')'"'
        echo '}'
        """
        
        payload = {"script": script}
        try:
            response = await self._request(session, "run-script", payload)
        except Exception as e:
            _LOGGER.error("Gaia API run-script failed: %s", e)
            return {}

        task_id = response.get("task-id")
        if not task_id:
            return {}
            
        for _ in range(10):
            await asyncio.sleep(2)
            try:
                task_response = await self._request(session, "show-task", {"task-id": task_id})
                task = task_response.get("tasks", [{}])[0]
                status = task.get("status")
                
                if status == "succeeded":
                    details = task.get("task-details", [{}])[0]
                    b64_output = details.get("output", "")
                    raw_output = base64.b64decode(b64_output).decode('utf-8').strip()
                    return json.loads(raw_output)
                
                if status in ["failed", "partially succeeded"]:
                    _LOGGER.error("Gaia Task failed: %s", task.get("progress-description"))
                    break
            except Exception as e:
                continue
                
        return {}
