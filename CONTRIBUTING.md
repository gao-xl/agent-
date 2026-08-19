# Contributing

感谢贡献。请先阅读 `SECURITY.md` 与项目的安全边界：任何新 Provider 都必须默认停止、支持显式停止，并且不得根据观察数据自动触发设备动作。

## 本地开发

1. 启动后端：`cd backend` 后创建虚拟环境并执行 `pip install -r requirements.txt`。
2. 启动前端：`cd frontend && npm install && npm run dev`。
3. 运行检查：根目录执行 `npm run build`；后端执行 `python -m unittest discover -s tests`。

## 提交要求

- 每项变更应有清晰、聚焦的提交说明。
- 为行为变更添加或更新测试。
- 不提交 API 密钥、真实个人数据、音视频、设备标识符或构建产物。
- 新设备协议必须注明来源、许可证、测试范围和失联/异常时的停止行为。

## Pull Request

说明问题、实现方式、风险、测试命令和结果。涉及设备控制、安全或隐私的改动需要维护者人工审核。
