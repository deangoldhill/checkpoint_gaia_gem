import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_PORT

DOMAIN = "checkpoint_gaia_gem"

class CheckpointGaiaFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Check Point Gaia Gem."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # If the user submitted the form, create the integration entry
            return self.async_create_entry(title=f"Check Point ({user_input[CONF_HOST]})", data=user_input)

        # The UI form schema
        data_schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Optional(CONF_PORT, default=443): int,
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
