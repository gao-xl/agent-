# EdgePlay 第一版架构

## 数据流

```text
Web 前端
  -> REST / WebSocket
FastAPI 边缘后端
  -> 模块管理器 / 事件总线 / 剧本引擎 / AI Gateway
Safety Core
  -> Device Provider
设备：Mock / DG-LAB Gateway / YokoNex / Buttplug / Generic BLE

## DG-LAB 官方 SDK 网关

官方 `dglab-kit` 是 TypeScript SDK，因此第一版使用独立 Node.js 网关承载
DG-LAB Socket V4。Python 主后端通过本地 WebSocket 调用网关，避免把厂商
协议耦合进剧本、AI 和安全核心。
```

## Provider 约定

设备适配器只负责设备协议，不负责剧情和 AI。所有真实设备动作必须经过 `SafetyCore.validate()`，并实现 `stop_all()`。

## 后续接入

- `DGLabSocketProvider`：调用官方 `dglab-kit` 的 V4 WebSocket API。
- `DGLabBleProvider`：瑞芯微 Linux/BlueZ 直连郊狼。
- `YokoNexProvider`：在确认型号和授权边界后接入 YokoNex ES01。
- `ButtplugProvider`：通过 Intiface WebSocket 接入通用设备。
