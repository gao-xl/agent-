from ..models import DeviceCapability, DeviceCommand, DeviceInfo, DeviceState
from .base import DeviceProvider


class MockProvider(DeviceProvider):
    id = "mock"

    def __init__(self) -> None:
        self.last_command: DeviceCommand | None = None

    async def list_devices(self) -> list[DeviceInfo]:
        return [
            DeviceInfo(
                id="mock-001",
                name="模拟反馈设备",
                provider=self.id,
                model="MockDevice",
                state=DeviceState.connected,
                capabilities=[
                    DeviceCapability(name="set_value", minimum=0, maximum=100),
                    DeviceCapability(name="pulse", minimum=0, maximum=100, unit="level"),
                    DeviceCapability(name="stop"),
                ],
            )
        ]

    async def execute(self, command: DeviceCommand) -> None:
        self.last_command = command

    async def stop_all(self) -> None:
        self.last_command = DeviceCommand(device_id="*", action="stop")
