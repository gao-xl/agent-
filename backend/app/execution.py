"""A deliberately small, human-supervised scenario runner."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from .models import AudioPlayRequest, DeviceCommand, ExecutionState, Scenario, ScenarioEvent, ScenarioExecution
from .safety import SafetyCore

Publish = Callable[[dict], Awaitable[None]]
ExecuteDevice = Callable[[DeviceCommand], Awaitable[None]]


class ScenarioRunner:
    def __init__(self, safety: SafetyCore, execute_device: ExecuteDevice, publish: Publish) -> None:
        self.safety = safety
        self.execute_device = execute_device
        self.publish = publish
        self.execution: ScenarioExecution | None = None
        self.scenario: Scenario | None = None

    async def start(self, scenario: Scenario) -> ScenarioExecution:
        if self.execution and self.execution.state in {ExecutionState.running, ExecutionState.awaiting_confirmation}:
            raise ValueError("已有剧本正在执行")
        self.scenario = scenario
        self.execution = ScenarioExecution(scenario_id=scenario.id, state=ExecutionState.running, message="剧本已启动")
        await self.publish({"type": "scenario.started", "payload": self.execution.model_dump(mode="json")})
        return await self.advance()

    async def advance(self) -> ScenarioExecution:
        if not self.execution or not self.scenario:
            raise ValueError("没有正在执行的剧本")
        if self.execution.state == ExecutionState.awaiting_confirmation:
            return self.execution
        while self.execution.event_index < len(self.scenario.events):
            event = self.scenario.events[self.execution.event_index]
            if event.type == "device_command":
                self.execution.state = ExecutionState.awaiting_confirmation
                self.execution.pending_event = event
                self.execution.message = "设备事件等待人工确认"
                await self.publish({"type": "scenario.confirmation_required", "payload": self.execution.model_dump(mode="json")})
                return self.execution
            await self._publish_event(event)
            self.execution.event_index += 1
        self.execution.state = ExecutionState.completed
        self.execution.pending_event = None
        self.execution.message = "剧本执行完成"
        await self.publish({"type": "scenario.completed", "payload": self.execution.model_dump(mode="json")})
        return self.execution

    async def confirm(self) -> ScenarioExecution:
        if not self.execution or self.execution.state != ExecutionState.awaiting_confirmation or not self.execution.pending_event:
            raise ValueError("当前没有等待确认的设备事件")
        command = DeviceCommand.model_validate(self.execution.pending_event.payload.get("command", {}))
        command.metadata["confirmed"] = True
        checked = self.safety.validate(command)
        await self.execute_device(checked)
        await self.publish({"type": "scenario.device_command", "payload": checked.model_dump(mode="json")})
        self.execution.event_index += 1
        self.execution.pending_event = None
        self.execution.state = ExecutionState.running
        self.execution.message = "设备事件已确认"
        return await self.advance()

    async def stop(self, reason: str = "操作者停止") -> ScenarioExecution | None:
        if not self.execution:
            return None
        self.execution.state = ExecutionState.stopped
        self.execution.pending_event = None
        self.execution.message = reason
        await self.publish({"type": "scenario.stopped", "payload": self.execution.model_dump(mode="json")})
        return self.execution

    async def _publish_event(self, event: ScenarioEvent) -> None:
        if event.type == "audio":
            payload = AudioPlayRequest.model_validate(event.payload).model_dump(mode="json")
            await self.publish({"type": "audio.play", "payload": payload})
            return
        await self.publish({"type": "scenario.event", "payload": event.model_dump(mode="json")})
