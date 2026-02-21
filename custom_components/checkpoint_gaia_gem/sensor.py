import logging
from datetime import timedelta
import aiohttp

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.const import PERCENTAGE, CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_PORT

from .api import CheckpointGaiaAPI

_LOGGER = logging.getLogger(__name__)
DOMAIN = "checkpoint_gaia_gem"
SCAN_INTERVAL = timedelta(seconds=60)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Check Point sensors from a config entry."""
    # Read configuration from the UI setup
    config = entry.data
    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT, 443)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)

    api = CheckpointGaiaAPI(host, port, username, password)

    async def async_update_data():
        async with aiohttp.ClientSession() as session:
            try:
                await api.login(session)
                data = await api.get_metrics(session)
                await api.logout(session)
                return data
            except Exception as e:
                _LOGGER.error("Error communicating with Check Point API: %s", e)
                return {}

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=SCAN_INTERVAL,
    )

    await coordinator.async_refresh()

    sensors = [
        CheckpointSensor(coordinator, "CPU Usage", "cpu_usage", PERCENTAGE, "mdi:cpu-64-bit"),
        CheckpointSensor(coordinator, "Memory Usage", "memory_usage", PERCENTAGE, "mdi:memory"),
        CheckpointSensor(coordinator, "Concurrent Connections", "connections", "Conns", "mdi:lan-connect"),
        CheckpointSensor(coordinator, "Connections Per Second", "cps", "CPS", "mdi:chart-timeline-variant"),
        CheckpointSensor(coordinator, "VPN Status", "vpn_status", None, "mdi:vpn"),
        CheckpointSensor(coordinator, "Blade Content Version", "blade_versions", None, "mdi:shield-check"),
    ]

    async_add_entities(sensors, True)

# ... (Keep your existing CheckpointSensor class here) ...
