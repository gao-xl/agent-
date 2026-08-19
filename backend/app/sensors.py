"""Sensor plugin boundary with deterministic, opt-in mock sources."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from .models import Observation, ObservationRecord, SensorInfo

Publish = Callable[[dict], Awaitable[None]]
RecordObservation = Callable[[Observation], Awaitable[ObservationRecord]]


class SensorManager:
    def __init__(self, publish: Publish, record_observation: RecordObservation) -> None:
        self.publish = publish
        self.record_observation = record_observation
        self.sensors = {
            "mock-heart-rate": SensorInfo(id="mock-heart-rate", name="模拟心率", kind="heart_rate", status="stopped", description="用于验证蓝牙/可穿戴输入链路的模拟源。"),
            "mock-microphone": SensorInfo(id="mock-microphone", name="模拟声音电平", kind="audio_level", status="stopped", description="只产生归一化音量，不保存原始音频。"),
            "mock-camera": SensorInfo(id="mock-camera", name="模拟画面状态", kind="visual_signal", status="stopped", description="只产生演示信号，不采集或保存图像。"),
        }
        self.tasks: dict[str, asyncio.Task] = {}

    def list(self) -> list[SensorInfo]:
        return list(self.sensors.values())

    async def start(self, sensor_id: str) -> SensorInfo:
        sensor = self._get(sensor_id)
        if sensor_id not in self.tasks or self.tasks[sensor_id].done():
            self.tasks[sensor_id] = asyncio.create_task(self._run(sensor_id))
        sensor.status = "running"
        await self.publish({"type": "sensor.started", "payload": sensor.model_dump(mode="json")})
        return sensor

    async def stop(self, sensor_id: str) -> SensorInfo:
        sensor = self._get(sensor_id)
        task = self.tasks.pop(sensor_id, None)
        if task:
            task.cancel()
        sensor.status = "stopped"
        await self.publish({"type": "sensor.stopped", "payload": sensor.model_dump(mode="json")})
        return sensor

    async def shutdown(self) -> None:
        for sensor_id in list(self.tasks):
            await self.stop(sensor_id)

    def _get(self, sensor_id: str) -> SensorInfo:
        if sensor_id not in self.sensors:
            raise ValueError("sensor not found")
        return self.sensors[sensor_id]

    async def _run(self, sensor_id: str) -> None:
        tick = 0
        try:
            while True:
                await asyncio.sleep(2)
                tick += 1
                sensor = self._get(sensor_id)
                if sensor.kind == "heart_rate": value: int | float = 66 + (tick % 5)
                elif sensor.kind == "audio_level": value = round((tick % 10) / 10, 2)
                else: value = "signal-present" if tick % 2 else "signal-idle"
                observation = Observation(source=sensor_id, kind=sensor.kind, value=value, confidence=1.0)
                sensor.latest = observation
                record = await self.record_observation(observation)
                await self.publish({"type": "sensor.observation", "payload": record.model_dump(mode="json")})
        except asyncio.CancelledError:
            raise
