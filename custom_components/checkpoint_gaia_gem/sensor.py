import logging
from datetime import timedelta
import aiohttp

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.const import PERCENTAGE

from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_USERNAME, CONF_PASSWORD
from .api import CheckpointGaiaAPI

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=60)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the sensors from a config entry."""
    host = config_entry.data[CONF_HOST]
    port = config_entry.data[CONF_PORT]
    username = config_entry.data[CONF_USERNAME]
    password = config_entry.data[CONF_PASSWORD]

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
        name=f"checkpoint_gaia_gem_{host}",
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

    async_add_entities(sensors)

class CheckpointSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, name, key, unit, icon):
        super().__init__(coordinator)
        self._name = name
        self._key = key
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        # Create a unique ID so users can customize the sensor in the UI
        self._attr_unique_id = f"{coordinator.name}_{key}"

    @property
    def name(self):
        return f"Check Point {self._name}"

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)
