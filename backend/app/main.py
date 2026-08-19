from contextlib import asynccontextmanager
import os
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .ai import AiService
from .events import EventBus
from .execution import ScenarioRunner
from .models import AiSettings, AudioPlayRequest, DeviceCommand, DeviceCommandRequest, Observation, SafetySettings, ScenarioImport
from .modules import default_modules
from .providers.registry import ProviderRegistry
from .scenarios import ScenarioStore
from .safety import SafetyCore, SafetyError
from .sensors import SensorManager


bus = EventBus()
registry = ProviderRegistry()
safety = SafetyCore(SafetySettings())
scenarios = ScenarioStore(os.getenv("EDGEPLAY_DB_PATH", "edgeplay.db"))
ai_service = AiService()
runner = ScenarioRunner(safety, registry.execute, bus.publish)
sensors = SensorManager(bus.publish)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    safety.stop()
    await runner.stop("服务关闭")
    await sensors.shutdown()
    await registry.stop_all()


app = FastAPI(title="EdgePlay Platform", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "edgeplay-backend"}


@app.get("/api/devices")
async def devices():
    return await registry.list_devices()


@app.get("/api/providers")
async def providers():
    return await registry.status()


@app.get("/api/modules")
async def modules():
    return default_modules()


@app.get("/api/ai/settings")
async def get_ai_settings():
    return ai_service.public_settings()


@app.put("/api/ai/settings")
async def update_ai_settings(settings: AiSettings):
    try:
        result = ai_service.update_settings(settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await bus.publish({"type": "ai.settings", "payload": result.model_dump(mode="json")})
    return result


@app.get("/api/safety")
async def get_safety() -> SafetySettings:
    return safety.settings


@app.post("/api/safety/stop")
async def safety_stop() -> dict[str, str]:
    safety.stop()
    await runner.stop("安全停止")
    await registry.stop_all()
    await bus.publish({"type": "safety.stopped"})
    return {"status": "stopped"}


@app.post("/api/safety/resume")
async def safety_resume() -> dict[str, str]:
    safety.resume()
    await bus.publish({"type": "safety.resumed"})
    return {"status": "resumed"}


@app.put("/api/safety")
async def update_safety(settings: SafetySettings) -> SafetySettings:
    safety.settings = settings
    await bus.publish({"type": "safety.settings", "payload": settings.model_dump(mode="json")})
    return settings


@app.post("/api/devices/command")
async def command(payload: DeviceCommandRequest) -> dict[str, Any]:
    command_data = payload.model_dump(exclude={"confirmed"})
    checked_command = DeviceCommand.model_validate(command_data)
    if payload.confirmed:
        checked_command.metadata["confirmed"] = True
    try:
        checked = safety.validate(checked_command)
        await registry.execute(checked)
    except (SafetyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    event = {"type": "device.command", "payload": checked.model_dump(mode="json")}
    await bus.publish(event)
    return {"ok": True, "command": checked}


@app.get("/api/scenarios")
async def list_scenarios():
    return scenarios.list()


@app.post("/api/scenarios", status_code=201)
async def import_scenario(payload: ScenarioImport):
    try:
        scenario = scenarios.import_scenario(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await bus.publish({"type": "scenario.imported", "payload": scenario.model_dump(mode="json")})
    return scenario


@app.post("/api/scenarios/{scenario_id}/optimize")
async def optimize(scenario_id: str):
    scenario = scenarios.get(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="剧本不存在")
    try:
        result = await ai_service.optimize(scenario)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI 优化失败：{exc}") from exc
    await bus.publish({"type": "scenario.optimized", "payload": {"scenario_id": scenario_id, **result.model_dump()}})
    return result


@app.get("/api/execution")
async def execution_status():
    return runner.execution


@app.post("/api/scenarios/{scenario_id}/start")
async def start_scenario(scenario_id: str):
    scenario = scenarios.get(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="剧本不存在")
    try:
        return await runner.start(scenario)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/execution/confirm")
async def confirm_execution():
    try:
        return await runner.confirm()
    except (ValueError, SafetyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/execution/advance")
async def advance_execution():
    try:
        return await runner.advance()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/execution/stop")
async def stop_execution():
    return await runner.stop()


@app.post("/api/audio/play")
async def play_audio(payload: AudioPlayRequest):
    await bus.publish({"type": "audio.play", "payload": payload.model_dump(mode="json")})
    return {"ok": True}


@app.post("/api/observations")
async def receive_observation(payload: Observation):
    # Observations are informational only; they never dispatch device commands.
    await bus.publish({"type": "observation.received", "payload": payload.model_dump(mode="json")})
    return {"ok": True, "automation": "disabled"}


@app.get("/api/sensors")
async def list_sensors():
    return sensors.list()


@app.post("/api/sensors/{sensor_id}/start")
async def start_sensor(sensor_id: str):
    try:
        return await sensors.start(sensor_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/sensors/{sensor_id}/stop")
async def stop_sensor(sensor_id: str):
    try:
        return await sensors.stop(sensor_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.websocket("/ws/events")
async def events(websocket: WebSocket):
    await websocket.accept()
    queue = bus.subscribe()
    try:
        await websocket.send_json({"type": "connected"})
        async for event in bus.stream(queue):
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        bus.unsubscribe(queue)
