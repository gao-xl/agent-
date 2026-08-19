from dataclasses import dataclass

from .models import DeviceCommand, SafetySettings


class SafetyError(ValueError):
    pass


@dataclass
class SafetyCore:
    settings: SafetySettings
    stopped: bool = False

    def validate(self, command: DeviceCommand) -> DeviceCommand:
        if self.stopped and command.action != "stop":
            raise SafetyError("safety stop is active")
        if self.settings.require_confirmation and command.action != "stop" and not command.metadata.get("confirmed"):
            raise SafetyError("manual confirmation is required")
        if command.action in {"set_value", "pulse"}:
            if command.value is None:
                raise SafetyError("value is required")
            if command.value < 0 or command.value > self.settings.max_value:
                raise SafetyError("value exceeds the configured safety limit")
            if command.duration_ms is not None and command.duration_ms > self.settings.max_duration_ms:
                raise SafetyError("duration exceeds the configured safety limit")
        return command

    def stop(self) -> None:
        self.stopped = True

    def resume(self) -> None:
        self.stopped = False
