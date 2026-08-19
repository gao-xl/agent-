# EdgePlay Platform

一个本地优先、模块化的 AI 互动设备平台。

第一版目标：

- 瑞芯微 Linux 边缘后端
- Web 控制台
- 模块化设备 Provider
- 模拟设备与安全策略
- 剧本导入、SQLite 持久化、本地规则优化和音频事件链路
- 为 DG-LAB 郊狼、YokoNex 役次元及 Buttplug/Intiface 预留适配层

## 开发结构

```text
backend/    Python 边缘后端
frontend/   Vue Web 控制台
docs/       架构和协议文档
```

第一版默认启用 `MockProvider`，不会连接真实硬件。`DG-LAB` 网关为可选组件；YokoNex 和 Buttplug 目前是明确标记的预留接口，并未宣称兼容真实产品。

人体、摄像头、麦克风或可穿戴设备的观察数据只会发布为事件供界面提示和人工复核，**绝不会自动生成或升级硬件控制指令**。真实设备适配器必须经过 `SafetyCore` 的上限、时长和紧急停止检查。

根目录的 `dglab-gateway.ts` 是独立的 DG-LAB 官方 SDK 网关。根目录 `package.json` 管理其依赖。

## 启动后端

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 启动 Web 控制台

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 Vite 输出的地址。开发服务器会把 `/api` 和 `/ws` 转发至后端 `127.0.0.1:8000`。

## 容器运行

镜像只提供后端服务。设备控制 API 未配置网络鉴权，因此仅应在受控的本地网络中使用；示例 compose 配置绑定到 `127.0.0.1`。

```bash
docker compose up --build
```

## 可选：启动 DG-LAB Socket 网关

该网关只绑定本机回环地址，独立于 Python 后端运行。它使用官方 `dglab-kit` 的 V4 Socket 模型；首次与 App 配对及任何真实硬件测试都应在明确同意、手动监督和可立即停止的前提下进行。

```bash
npm install
npm run gateway
```

后端会在网关可用时读取其设备列表；网关不可用不会影响 MockProvider、剧本或音频功能。

## 当前完成度

- 已可运行：Mock 设备、安全停止、事件 WebSocket、剧本导入/持久化、受限本地优化、浏览器提示音、模块状态页；也可在控制台 API 配置 OpenAI 兼容模型进行剧本编辑建议（密钥只保存在当前后端进程内）。
- 需要真实设备验收后启用：DG-LAB 网关脉冲指令映射。
- 设计预留但尚未实现：YokoNex、Buttplug/Intiface、摄像头/麦克风/心率采集器，以及外部或本地大模型 Provider。

## 开源协作

- [贡献指南](CONTRIBUTING.md)
- [安全政策](SECURITY.md)
- [社区行为准则](CODE_OF_CONDUCT.md)
- [路线图](ROADMAP.md)
- [变更日志](CHANGELOG.md)

项目核心代码使用 [MIT License](LICENSE)。不同的第三方设备 SDK 与协议可能具有额外授权条件。

## 许可证

核心项目使用 MIT License。第三方设备协议、SDK 和适配器必须遵守各自许可证与厂商授权条款。
