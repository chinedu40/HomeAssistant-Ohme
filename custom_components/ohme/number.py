from __future__ import annotations
import asyncio
from homeassistant.components.number import NumberEntity, NumberDeviceClass
from homeassistant.components.number.const import NumberMode
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import callback, HomeAssistant
from .const import DOMAIN, DATA_CLIENT, DATA_COORDINATORS, COORDINATOR_ACCOUNTINFO, COORDINATOR_CHARGESESSIONS
from .base import OhmeEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry,
    async_add_entities
):
    """Setup numbers and configure coordinator."""
    account_id = config_entry.data['email']

    coordinators = hass.data[DOMAIN][account_id][DATA_COORDINATORS]
    client = hass.data[DOMAIN][account_id][DATA_CLIENT]

    numbers = [
        TargetPercentNumber(coordinators[COORDINATOR_CHARGESESSIONS], hass, client),
        PreconditioningNumber(coordinators[COORDINATOR_CHARGESESSIONS], hass, client),
    ]

    if client.cap_available:
        numbers.append(
            PriceCapNumber(coordinators[COORDINATOR_ACCOUNTINFO], hass, client)
        )

    async_add_entities(numbers, update_before_add=True)


class TargetPercentNumber(OhmeEntity, NumberEntity):
    """Target percentage sensor."""
    _attr_translation_key = "target_percentage"
    _attr_icon = "mdi:battery-heart"
    _attr_device_class = NumberDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 0

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._client.async_set_target(target_percent=int(value))
        await asyncio.sleep(1)
        await self.coordinator.async_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Get value from client state."""
        target = self._client.target_soc
        self._state = target if target and target > 0 else None
        self.async_write_ha_state()

    @property
    def native_value(self):
        return self._state


class PreconditioningNumber(OhmeEntity, NumberEntity):
    """Preconditioning sensor."""
    _attr_translation_key = "preconditioning"
    _attr_icon = "mdi:air-conditioner"
    _attr_device_class = NumberDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_native_min_value = 0
    _attr_native_step = 5
    _attr_native_max_value = 60

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._client.async_set_target(pre_condition_length=int(value))
        await asyncio.sleep(1)
        await self.coordinator.async_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Get value from client state."""
        self._state = self._client.preconditioning
        self.async_write_ha_state()

    @property
    def native_value(self):
        return self._state


class PriceCapNumber(OhmeEntity, NumberEntity):
    _attr_translation_key = "price_cap"
    _attr_icon = "mdi:cash"
    _attr_device_class = NumberDeviceClass.MONETARY
    _attr_mode = NumberMode.BOX
    _attr_native_step = 0.1
    _attr_native_min_value = -100
    _attr_native_max_value = 100

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._client.async_change_price_cap(cap=value)

        await asyncio.sleep(1)
        await self.coordinator.async_refresh()

    @property
    def native_unit_of_measurement(self):
        if self.coordinator.data is None:
            return None

        penny_unit = {
            "GBP": "p",
            "EUR": "c"
        }
        currency = self.coordinator.data["userSettings"].get(
            "currencyCode", "XXX")

        return penny_unit.get(currency, f"{currency}/100")

    @callback
    def _handle_coordinator_update(self) -> None:
        """Get value from data returned from API by coordinator"""
        if self.coordinator.data is not None:
            try:
                self._state = self.coordinator.data["userSettings"]["chargeSettings"][0]["value"]
            except:
                self._state = None
        self.async_write_ha_state()

    @property
    def native_value(self):
        return self._state
