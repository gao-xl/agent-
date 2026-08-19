from abc import ABC, abstractmethod

from ..models import DeviceCommand, DeviceInfo


class DeviceProvider(ABC):
    id: str

    @abstractmethod
    async def list_devices(self) -> list[DeviceInfo]:
        raise NotImplementedError

    @abstractmethod
    async def execute(self, command: DeviceCommand) -> None:
        raise NotImplementedError

    @abstractmethod
    async def stop_all(self) -> None:
        raise NotImplementedError
