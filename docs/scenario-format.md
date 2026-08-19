# 剧本格式

剧本可直接导入纯文本，也可导入 JSON。纯文本会被保存为一个 `narrative` 事件，适合先编辑再逐步结构化。

```json
{
  "events": [
    {"type": "narrative", "payload": {"text": "显示给操作者的提示"}},
    {"type": "audio", "payload": {"cue": "提示音"}}
  ]
}
```

当前本地优化器只给出编辑建议和安全说明。它不产生 `DeviceCommand`，也不会根据摄像头、麦克风或生理观察数据触发设备。

未来的 AI Provider 应只输出经过 JSON Schema 校验的建议；由操作者确认后，独立的剧本执行器才可以请求设备动作，并仍由 Safety Core 拦截。
