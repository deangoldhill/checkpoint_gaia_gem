import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
import aiohttp

from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_USERNAME, CONF_PASSWORD
from .api import CheckpointGaiaAPI

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str,
    vol.Required(CONF_PORT, default=443): int,
    vol.Required(CONF_USERNAME): str,
    vol.Required(CONF_PASSWORD): str,
})

async def validate_input(hass: HomeAssistant, data: dict):
    """Validate the user input allows us to connect."""
    api = CheckpointGaiaAPI(data[CONF_HOST], data[CONF_PORT], data[CONF_USERNAME], data[CONF_PASSWORD])
    async with aiohttp.ClientSession() as session:
        await api.login(session)
        if not api.sid:
            raise ValueError("invalid_auth")
        await api.logout(session)

class CheckpointConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
                return self.async_create_entry(title=user_input[CONF_HOST], data=user_input)
            except ValueError as e:
                errors["base"] = str(e)
            except Exception:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )
