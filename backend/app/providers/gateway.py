import json

from ..models import DeviceCapability, DeviceCommand, DeviceInfo, DeviceState
from .base import DeviceProvider


class GatewayProvider(DeviceProvider):
    """Boundary for the optional Node/DG-LAB gateway."""

    id = "dglab-gateway"

    def __init__(self, url: str = "ws://127.0.0.1:8765/ws") -> None:
        self.url = url
        self._devices: list[DeviceInfo] = []

    async def _request(self, payload: dict) -> dict:
        try:
            from websockets.asyncio.client import connect
        except ImportError as exc:
            raise RuntimeError("未安装可选网关依赖 websockets") from exc
        async with connect(self.url, open_timeout=2) as socket:
            await socket.recv()
            await socket.send(json.dumps(payload))
            while True:
                event = json.loads(await socket.recv())
                if event.get("type") in {"command.result", "command.error"}:
                    if event["type"] == "command.error":
                        raise RuntimeError(event.get("error", "gateway command failed"))
                    return event.get("result", {})

    async def list_devices(self) -> list[DeviceInfo]:
        try:
            await self._request({"type": "connect"})
            result = await self._request({"type": "devices"})
        except Exception:
            return self._devices
        devices: list[DeviceInfo] = []
        for client_id, raw_devices in result.get("clients", []):
            for raw in raw_devices:
                slot_id = str(raw.get("slotId", raw.get("id", "unknown")))
                devices.append(
                    DeviceInfo(
                        id=f"dglab:{client_id}:{slot_id}",
                        name=str(raw.get("name", "DG-LAB device")),
                        provider=self.id,
                        model=str(raw.get("type", "unknown")),
                        state=DeviceState.connected,
                        capabilities=[
                            DeviceCapability(name="pulse"),
                            DeviceCapability(name="stop"),
                        ],
                    )
                )
        self._devices = devices
        return self._devices

    async def execute(self, command: DeviceCommand) -> None:
        item = next((device for device in self._devices if device.id == command.device_id), None)
        if item is None:
            await self.list_devices()
            item = next((device for device in self._devices if device.id == command.device_id), None)
        if item is None:
            raise RuntimeError("gateway device not found")
        _, client_id, slot_id = item.id.split(":", 2)
        if command.action == "stop":
            await self._request({"type": "stop", "clientId": client_id, "slotId": slot_id})
            return
        raise RuntimeError("gateway pulse command requires waveform frames")

    async def stop_all(self) -> None:
        for device in self._devices:
            try:
                await self.execute(DeviceCommand(device_id=device.id, action="stop"))
            except RuntimeError:
                continue
