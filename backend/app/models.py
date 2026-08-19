from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class DeviceState(StrEnum):
    disconnected = "disconnected"
    connected = "connected"
    stopped = "stopped"
    error = "error"


class DeviceCapability(BaseModel):
    name: str
    minimum: float | None = None
    maximum: float | None = None
    unit: str | None = None


class DeviceInfo(BaseModel):
    id: str
    name: str
    provider: str
    model: str
    state: DeviceState
    capabilities: list[DeviceCapability] = Field(default_factory=list)


class DeviceCommand(BaseModel):
    device_id: str
    action: str
    value: float | None = None
    duration_ms: int | None = Field(default=None, ge=0, le=60_000)
    channel: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeviceCommandRequest(DeviceCommand):
    confirmed: bool = False


class ScenarioEvent(BaseModel):
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class SafetySettings(BaseModel):
    max_value: float = Field(default=30, ge=0, le=100)
    max_duration_ms: int = Field(default=5_000, ge=0, le=60_000)
    require_confirmation: bool = True


class Observation(BaseModel):
    source: str
    kind: str
    value: Any
    confidence: float | None = Field(default=None, ge=0, le=1)


class ObservationRecord(Observation):
    id: int
    timestamp: str


class ScenarioImport(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=50_000)


class ScenarioUpdate(ScenarioImport):
    pass


class Scenario(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    source: str
    events: list[ScenarioEvent] = Field(default_factory=list)
    revision: int = 1
    created_at: str
    updated_at: str


class ScenarioOptimization(BaseModel):
    summary: str
    suggestions: list[str] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)
    suggested_settings: dict[str, Any] = Field(default_factory=dict)


class AudioPlayRequest(BaseModel):
    frequency_hz: int = Field(default=440, ge=80, le=2_000)
    duration_ms: int = Field(default=250, ge=20, le=5_000)
    volume: float = Field(default=0.12, ge=0, le=1)


class ModuleInfo(BaseModel):
    id: str
    name: str
    kind: str
    status: str
    description: str


class HealthReport(BaseModel):
    status: str
    service: str
    version: str
    safety_stopped: bool
    provider_count: int


class ProviderInfo(BaseModel):
    id: str
    status: str
    device_count: int = 0
    message: str | None = None


class SensorInfo(BaseModel):
    id: str
    name: str
    kind: str
    status: str
    description: str
    latest: Observation | None = None


class ExecutionState(StrEnum):
    idle = "idle"
    running = "running"
    awaiting_confirmation = "awaiting_confirmation"
    completed = "completed"
    stopped = "stopped"
    error = "error"


class ScenarioExecution(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    scenario_id: str
    state: ExecutionState = ExecutionState.idle
    event_index: int = 0
    pending_event: ScenarioEvent | None = None
    message: str = ""


class AiSettings(BaseModel):
    provider: str = Field(default="local-rules", pattern="^(local-rules|openai-compatible)$")
    base_url: str | None = None
    model: str | None = None
    api_key: str | None = Field(default=None, exclude=True)


class AiSettingsPublic(BaseModel):
    provider: str
    base_url: str | None = None
    model: str | None = None
    has_api_key: bool = False
