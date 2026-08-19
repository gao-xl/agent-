"""AI optimizer boundary. AI output is advice, never a device-control path."""

from __future__ import annotations

import asyncio
import json
from urllib.request import Request, urlopen

from .models import AiSettings, AiSettingsPublic, Scenario, ScenarioOptimization
from .scenarios import optimize_scenario


class AiService:
    def __init__(self) -> None:
        self.settings = AiSettings()

    def public_settings(self) -> AiSettingsPublic:
        return AiSettingsPublic(
            provider=self.settings.provider,
            base_url=self.settings.base_url,
            model=self.settings.model,
            has_api_key=bool(self.settings.api_key),
        )

    def update_settings(self, settings: AiSettings) -> AiSettingsPublic:
        if settings.api_key is None:
            settings.api_key = self.settings.api_key
        if settings.provider == "openai-compatible" and (not settings.base_url or not settings.model or not settings.api_key):
            raise ValueError("OpenAI 兼容 Provider 需要 base_url、model 和 api_key")
        self.settings = settings
        return self.public_settings()

    async def optimize(self, scenario: Scenario) -> ScenarioOptimization:
        if self.settings.provider == "local-rules":
            return optimize_scenario(scenario)
        return await asyncio.to_thread(self._openai_compatible, scenario)

    def _openai_compatible(self, scenario: Scenario) -> ScenarioOptimization:
        assert self.settings.base_url and self.settings.model and self.settings.api_key
        prompt = (
            "你是 EdgePlay 的剧本编辑助手。只返回 JSON 对象，字段为 summary、suggestions、safety_notes、suggested_settings。"
            "不要输出设备命令、强度、波形或自动化规则。观察数据不能作为自动设备控制依据。\n\n"
            f"剧本名称：{scenario.name}\n剧本内容：{scenario.source}"
        )
        request = Request(
            self.settings.base_url.rstrip("/") + "/chat/completions",
            data=json.dumps({"model": self.settings.model, "messages": [{"role": "user", "content": prompt}], "response_format": {"type": "json_object"}}).encode(),
            headers={"Authorization": f"Bearer {self.settings.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=30) as response:  # noqa: S310 - URL is explicit user configuration.
            payload = json.loads(response.read())
        content = payload["choices"][0]["message"]["content"]
        result = ScenarioOptimization.model_validate_json(content)
        # The system owns this safety contract even when the text came from a model.
        result.suggested_settings = {"require_confirmation": True, "max_duration_ms": 5_000}
        result.safety_notes = list(dict.fromkeys([*result.safety_notes, "AI 建议不直接控制硬件；需人工确认并经 Safety Core 校验。 "]))
        return result
