from __future__ import annotations
import asyncio
import logging
from homeassistant.components.time import TimeEntity
from homeassistant.core import callback, HomeAssistant
from .const import DOMAIN, DATA_CLIENT, DATA_COORDINATORS, COORDINATOR_CHARGESESSIONS
from datetime import time as dt_time
from .base import OhmeEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry,
    async_add_entities
):
    """Setup time entities and configure coordinator."""
    account_id = config_entry.data['email']

    coordinators = hass.data[DOMAIN][account_id][DATA_COORDINATORS]
    client = hass.data[DOMAIN][account_id][DATA_CLIENT]

    async_add_entities(
        [TargetTime(coordinators[COORDINATOR_CHARGESESSIONS], hass, client)],
        update_before_add=True
    )


class TargetTime(OhmeEntity, TimeEntity):
    """Target time entity."""
    _attr_translation_key = "target_time"
    _attr_id = "target_time"
    _attr_icon = "mdi:alarm-check"

    async def async_set_value(self, value: dt_time) -> None:
        """Update the current value."""
        await self._client.async_set_target(target_time=(int(value.hour), int(value.minute)))
        await asyncio.sleep(1)
        await self.coordinator.async_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Get value from client state."""
        hour, minute = self._client.target_time
        if hour or minute:
            self._state = dt_time(hour=hour, minute=minute, second=0)
        self.async_write_ha_state()

    @property
    def native_value(self):
        return self._state
