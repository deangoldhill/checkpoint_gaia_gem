import aiohttp
import logging
import json

_LOGGER = logging.getLogger(__name__)

class CheckpointGaiaAPI:
    def __init__(self, host, port, username, password):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.base_url = f"https://{host}:{port}/web_api"
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
        data = await self._request(session, "login", {
            "user": self.username, 
            "password": self.password,
            "read-only": True
        })
        self.sid = data.get("sid")

    async def logout(self, session):
        if self.sid:
            await self._request(session, "logout")
            self.sid = None

    async def get_metrics(self, session):
        script = """
        echo '{'
        echo '"cpu_usage": "'$(cpstat os -f perf | awk '/CPU Usage/ {print $3}')'",'
        echo '"memory_usage": "'$(cpstat os -f perf | awk '/Memory Usage/ {print $3}')'",'
        echo '"connections": "'$(fw tab -t connections -s | awk 'NR==2 {print $4}')'",'
        echo '"cps": "'$(cpstat os -f perf | awk '/Connections\/Sec/ {print $2}')'",'
        echo '"vpn_status": "'$(cpstat vpn -f product | awk '/Product Status/ {print $3}')'",'
        echo '"blade_versions": "'$(cpinfo -y all | grep -i "content version" | head -n 1 | sed 's/.*: //')'"'
        echo '}'
        """
        payload = {
            "script-name": "ha_metrics_poll",
            "script": script,
            "targets": "localhost"
        }
        
        response = await self._request(session, "run-script", payload)
        
        try:
            raw_output = response["tasks"][0]["task-details"][0]["statusDescription"]
            return json.loads(raw_output)
        except (KeyError, json.JSONDecodeError) as e:
            _LOGGER.error("Failed to parse Check Point metrics: %s", e)
            return {}
