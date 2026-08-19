from .base import DeviceProvider
from .gateway import GatewayProvider
from .mock import MockProvider


class ProviderRegistry:
    def __init__(self) -> None:
        self.providers: dict[str, DeviceProvider] = {"mock": MockProvider()}
        self.providers["dglab-gateway"] = GatewayProvider()

    def add(self, provider: DeviceProvider) -> None:
        self.providers[provider.id] = provider

    async def list_devices(self):
        devices = []
        for provider in self.providers.values():
            devices.extend(await provider.list_devices())
        return devices

    async def execute(self, command):
        devices = await self.list_devices()
        device = next((item for item in devices if item.id == command.device_id), None)
        if device is None:
            raise ValueError("device not found")
        await self.providers[device.provider].execute(command)

    async def stop_all(self) -> None:
        for provider in self.providers.values():
            await provider.stop_all()

    async def status(self):
        from ..models import ProviderInfo
        result = []
        for provider_id, provider in self.providers.items():
            try:
                devices = await provider.list_devices()
                result.append(ProviderInfo(id=provider_id, status="ready" if devices else "idle", device_count=len(devices)))
            except Exception as exc:
                result.append(ProviderInfo(id=provider_id, status="error", message=str(exc)))
        return result
