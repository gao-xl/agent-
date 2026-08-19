from .models import ModuleInfo


def default_modules() -> list[ModuleInfo]:
    return [
        ModuleInfo(id="scenario", name="剧本引擎", kind="core", status="ready", description="导入、版本化并分析剧本事件。"),
        ModuleInfo(id="ai-rules", name="本地规则 AI", kind="ai", status="ready", description="生成受限的剧本优化建议；不直接控制硬件。"),
        ModuleInfo(id="audio-web", name="Web 音频输出", kind="output", status="ready", description="通过浏览器 Web Audio API 播放提示音。"),
        ModuleInfo(id="dglab-gateway", name="DG-LAB 网关", kind="provider", status="optional", description="需要独立启动官方 SDK 网关并用真实设备验证。"),
        ModuleInfo(id="yokonex", name="YokoNex 适配器", kind="provider", status="planned", description="保留接口，等待公开协议或经授权实现。"),
        ModuleInfo(id="buttplug", name="Buttplug / Intiface", kind="provider", status="planned", description="作为广泛第三方设备兼容层。"),
    ]
