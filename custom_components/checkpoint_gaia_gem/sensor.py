import logging
from datetime import timedelta
import aiohttp

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.const import PERCENTAGE, CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_PORT

# This dot tells Python to look in the exact same folder for api.py
from .api import CheckpointGaiaAPI

_LOGGER = logging.getLogger(__name__)
DOMAIN = "checkpoint_gaia_gem"
SCAN_INTERVAL = timedelta(seconds=60)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Check Point sensors from a UI config entry."""
    # Read configuration from the UI setup
    config = config_entry.data
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

    # Fetch initial data so we have state when entities are added
    await coordinator.async_config_entry_first_refresh()

    # If the CheckpointSensor class is missing from the bottom of the file, this line crashes!
    sensors = [
        CheckpointSensor(coordinator, host, "CPU Usage", "cpu_usage", PERCENTAGE, "mdi:cpu-64-bit"),
        CheckpointSensor(coordinator, host, "Memory Usage", "memory_usage", PERCENTAGE, "mdi:memory"),
        CheckpointSensor(coordinator, host, "Concurrent Connections", "connections", "Conns", "mdi:lan-connect"),
        CheckpointSensor(coordinator, host, "Connections Per Second", "cps", "CPS", "mdi:chart-timeline-variant"),
        CheckpointSensor(coordinator, host, "VPN Status", "vpn_status", None, "mdi:vpn"),
        CheckpointSensor(coordinator, host, "Blade Content Version", "blade_versions", None, "mdi:shield-check"),
    ]

    async_add_entities(sensors, True)


# ===========================================================================
# THIS IS THE CLASS THAT WAS MISSING! IT MUST REMAIN AT THE BOTTOM OF THE FILE
# ===========================================================================
class CheckpointSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Check Point Sensor."""

    def __init__(self, coordinator, host, name, key, unit, icon):
        super().__init__(coordinator)
        self._host = host
        self._name = name
        self._key = key
        self._unit = unit
        self._icon = icon

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"Check Point {self._host} {self._name}"

    @property
    def unique_id(self):
        """Return a unique ID to allow GUI editing."""
        return f"{self._host}_{self._key}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get(self._key)
        return None

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return self._icon
