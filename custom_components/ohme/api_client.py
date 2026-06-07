import logging
from homeassistant.helpers.device_registry import DeviceInfo
from ohme import OhmeApiClient as _BaseOhmeApiClient, ApiException, AuthException
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

__all__ = ["OhmeApiClient", "ApiException", "AuthException"]


class OhmeApiClient(_BaseOhmeApiClient):
    """Extends ohme package client with HA device info and CT clamp support."""

    def __init__(self, email: str, password: str) -> None:
        super().__init__(email=email, password=password)
        self._account_data: dict = {}
        self._ct_connected: bool = False

    # Compatibility wrapper

    async def async_create_session(self) -> bool:
        """Compatibility wrapper — delegates to async_login."""
        return await self.async_login()

    # Pull methods

    async def async_get_charge_sessions(self) -> dict:
        """Fetch charge sessions and return raw response for coordinators."""
        await self.async_get_charge_session()
        return self._charge_session

    async def async_update_device_info(self, **_kwargs) -> bool:
        """Fetch account/device info, cache raw response, update internal state."""
        resp = await self._make_request("GET", "/v1/users/me/account")
        self._account_data = resp

        self._cars = resp.get("cars") or []
        try:
            self.cap_enabled = resp["userSettings"]["chargeSettings"][0]["enabled"]
        except Exception:
            pass

        device = resp["chargeDevices"][0]
        self._capabilities = device["modelCapabilities"]
        self._configuration = device["optionalSettings"]
        self.serial = device["id"]

        self.device_info = {
            "name": device["modelTypeDisplayName"],
            "model": device["modelTypeDisplayName"].replace("Ohme ", ""),
            "sw_version": device["firmwareVersionLabel"],
        }

        if resp.get("tariff") and resp["tariff"].get("dsrTariff"):
            self.cap_available = False

        solar_modes = device["modelCapabilities"].get("solarModes", [])
        if isinstance(solar_modes, list) and len(solar_modes) == 1:
            self._capabilities["solar"] = True

        return True

    async def async_get_account_info(self) -> dict:
        """Refresh account info and return raw response."""
        await self.async_update_device_info()
        return self._account_data

    async def async_get_advanced_settings(self) -> dict:
        """Fetch advanced settings (CT clamp data)."""
        resp = await self._make_request(
            "GET", f"/v1/chargeDevices/{self.serial}/advancedSettings"
        )
        if resp.get("clampAmps") and resp["clampAmps"] > 0:
            self._ct_connected = True
        return resp

    # Getters

    def ct_connected(self) -> bool:
        """Is a CT clamp connected."""
        return self._ct_connected

    def get_device_info(self) -> DeviceInfo:
        """Return HA DeviceInfo object built from stored device_info dict."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"ohme_charger_{self.serial}")},
            name=self.device_info.get("name"),
            manufacturer="Ohme",
            model=self.device_info.get("model"),
            sw_version=self.device_info.get("sw_version"),
            serial_number=self.serial,
        )
