import { computed, onBeforeUnmount, onMounted, ref } from "vue"

type Scenario = { id: string; name: string; source: string; events: unknown[]; revision: number }
type Module = { id: string; name: string; status: string; description: string }
type Sensor = { id: string; name: string; kind: string; status: string; description: string; latest?: { value: unknown } }
type Provider = { id: string; status: string; device_count: number; message?: string }

export const Dashboard = {
  setup() {
    const devices = ref<any[]>([])
    const modules = ref<Module[]>([])
    const providers = ref<Provider[]>([])
    const sensors = ref<Sensor[]>([])
    const observations = ref<any[]>([])
    const scenarios = ref<Scenario[]>([])
    const selectedScenario = ref<Scenario | null>(null)
    const scenarioName = ref("示例剧本")
    const scenarioContent = ref('{"events":[{"type":"narrative","payload":{"text":"开始前请确认安全限制。"}},{"type":"audio","payload":{"cue":"提示音"}}]}')
    const optimization = ref<any>(null)
    const aiSettings = ref({ provider: "local-rules", base_url: "", model: "", api_key: "", has_api_key: false })
    const execution = ref<any>(null)
    const commandValue = ref(10)
    const commandDuration = ref(500)
    const safetyStopped = ref(false)
    const status = ref("正在连接后端…")
    const log = ref<string[]>([])
    const audioEnabled = ref(false)
    let socket: WebSocket | undefined
    const selectedLabel = computed(() => selectedScenario.value ? `${selectedScenario.value.name} · ${selectedScenario.value.events.length} 个事件` : "尚未选择剧本")
    const addLog = (message: string) => log.value.unshift(`${new Date().toLocaleTimeString()} ${message}`)

    async function request(path: string, init?: RequestInit) {
      const response = await fetch(path, init)
      if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || "请求失败")
      return response.json()
    }
    async function loadAll() {
      const [nextDevices, nextModules, nextScenarios, safety, nextAiSettings, nextProviders, nextSensors, nextExecution, nextObservations] = await Promise.all([request("/api/devices"), request("/api/modules"), request("/api/scenarios"), request("/api/safety"), request("/api/ai/settings"), request("/api/providers"), request("/api/sensors"), request("/api/execution"), request("/api/observations?limit=20")])
      devices.value = nextDevices; modules.value = nextModules; scenarios.value = nextScenarios; providers.value = nextProviders; sensors.value = nextSensors; execution.value = nextExecution; observations.value = nextObservations; safetyStopped.value = false
      aiSettings.value = { ...nextAiSettings, api_key: "" }
      status.value = `后端已连接 · 上限 ${safety.max_value}`
    }
    async function stop() { await request("/api/safety/stop", { method: "POST" }); safetyStopped.value = true }
    async function resume() { await request("/api/safety/resume", { method: "POST" }); safetyStopped.value = false }
    async function importScenario() {
      const created = await request("/api/scenarios", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: scenarioName.value, content: scenarioContent.value }) })
      scenarios.value.unshift(created); selectedScenario.value = created; addLog(`已导入剧本：${created.name}`)
    }
    function selectScenario(scenario: Scenario) { selectedScenario.value = scenario; scenarioName.value = scenario.name; scenarioContent.value = scenario.source }
    async function saveScenario() {
      if (!selectedScenario.value) return importScenario()
      const updated = await request(`/api/scenarios/${selectedScenario.value.id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: scenarioName.value, content: scenarioContent.value }) })
      scenarios.value = scenarios.value.map(item => item.id === updated.id ? updated : item); selectedScenario.value = updated; addLog("剧本已保存")
    }
    async function deleteScenario() {
      if (!selectedScenario.value || !confirm(`删除《${selectedScenario.value.name}》？`)) return
      await request(`/api/scenarios/${selectedScenario.value.id}`, { method: "DELETE" }); scenarios.value = scenarios.value.filter(item => item.id !== selectedScenario.value?.id); selectedScenario.value = null; addLog("剧本已删除")
    }
    async function exportScenario() {
      if (!selectedScenario.value) return
      const data = await request(`/api/scenarios/${selectedScenario.value.id}/export`); const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })); const link = document.createElement("a"); link.href = url; link.download = `${data.name}.json`; link.click(); URL.revokeObjectURL(url)
    }
    async function optimizeScenario() {
      if (!selectedScenario.value) return
      optimization.value = await request(`/api/scenarios/${selectedScenario.value.id}/optimize`, { method: "POST" }); addLog("已生成本地优化建议")
    }
    async function startScenario() {
      if (!selectedScenario.value) return
      execution.value = await request(`/api/scenarios/${selectedScenario.value.id}/start`, { method: "POST" }); addLog("剧本已启动")
    }
    async function confirmExecution() { execution.value = await request("/api/execution/confirm", { method: "POST" }); addLog("已确认待执行事件") }
    async function stopExecution() { execution.value = await request("/api/execution/stop", { method: "POST" }); addLog("剧本已停止") }
    async function commandDevice(deviceId: string) {
      await request("/api/devices/command", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ device_id: deviceId, action: "set_value", value: commandValue.value, duration_ms: commandDuration.value, confirmed: true }) })
      addLog("已发送已确认的设备指令")
    }
    async function toggleSensor(sensor: Sensor) {
      await request(`/api/sensors/${sensor.id}/${sensor.status === "running" ? "stop" : "start"}`, { method: "POST" }); await loadAll()
    }
    async function saveAiSettings() {
      const payload: any = { ...aiSettings.value }
      if (!payload.api_key) delete payload.api_key
      const result = await request("/api/ai/settings", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) })
      aiSettings.value = { ...result, api_key: "" }; addLog("AI Provider 设置已保存")
    }
    function playTone(payload: { frequency_hz: number; duration_ms: number; volume: number }) {
      if (!audioEnabled.value) return
      const context = new AudioContext(); const oscillator = context.createOscillator(); const gain = context.createGain()
      oscillator.frequency.value = payload.frequency_hz; gain.gain.value = payload.volume; oscillator.connect(gain).connect(context.destination)
      oscillator.start(); oscillator.stop(context.currentTime + payload.duration_ms / 1000); oscillator.onended = () => context.close()
    }
    function enableAudio() { audioEnabled.value = true; playTone({ frequency_hz: 440, duration_ms: 80, volume: 0.06 }) }
    async function testAudio() { await request("/api/audio/play", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }) }
    function connectEvents() {
      const scheme = location.protocol === "https:" ? "wss" : "ws"; socket = new WebSocket(`${scheme}://${location.host}/ws/events`)
      socket.onmessage = ({ data }) => { const event = JSON.parse(data); addLog(event.type); if (event.type === "audio.play") playTone(event.payload); if (event.type === "safety.stopped") safetyStopped.value = true; if (event.type === "safety.resumed") safetyStopped.value = false }
    }
    onMounted(() => { loadAll().catch(() => status.value = "无法连接后端"); connectEvents() }); onBeforeUnmount(() => socket?.close())
    return { devices, modules, providers, sensors, observations, scenarios, selectedScenario, scenarioName, scenarioContent, optimization, aiSettings, execution, commandValue, commandDuration, safetyStopped, status, log, audioEnabled, selectedLabel, loadAll, stop, resume, importScenario, selectScenario, saveScenario, deleteScenario, exportScenario, optimizeScenario, startScenario, confirmExecution, stopExecution, commandDevice, toggleSensor, saveAiSettings, enableAudio, testAudio }
  },
  template: `
    <main class="shell"><header><div><p class="eyebrow">EDGEPLAY PLATFORM · LOCAL FIRST</p><h1>AI 互动设备控制台</h1><p class="subtitle">剧本、音频、设备与安全策略处在同一条本地事件链路。</p></div><span class="status">{{ status }}</span></header>
    <section class="grid"><article class="panel"><h2>设备</h2><div v-if="!devices.length" class="empty">未发现设备；MockProvider 可用于验证链路。</div><div v-for="device in devices" :key="device.id" class="device"><div><strong>{{ device.name }}</strong><small>{{ device.provider }} · {{ device.model }}</small></div><span class="tag">{{ device.state }}</span><button @click="commandDevice(device.id)">确认后测试</button></div><label>数值 <input v-model.number="commandValue" type="number" min="0" max="100" /></label><label>时长 ms <input v-model.number="commandDuration" type="number" min="0" max="5000" /></label><button @click="loadAll">刷新</button></article><article class="panel"><h2>模块 / Provider</h2><div v-for="module in modules" :key="module.id" class="module"><div><strong>{{ module.name }}</strong><small>{{ module.description }}</small></div><span class="tag">{{ module.status }}</span></div><div v-for="provider in providers" :key="provider.id" class="module"><div><strong>{{ provider.id }}</strong><small>{{ provider.message || provider.device_count + ' 个设备' }}</small></div><span class="tag">{{ provider.status }}</span></div></article></section>
    <section class="grid"><article class="panel scenario"><h2>剧本编辑</h2><input v-model="scenarioName" aria-label="剧本名称" placeholder="剧本名称" /><textarea v-model="scenarioContent" aria-label="剧本内容" rows="8"></textarea><button @click="saveScenario">{{ selectedScenario ? '保存修订' : '导入并解析' }}</button><button v-if="selectedScenario" @click="exportScenario">导出 JSON</button><button v-if="selectedScenario" class="danger" @click="deleteScenario">删除剧本</button></article><article class="panel"><h2>剧本执行</h2><p class="selected">{{ selectedLabel }}</p><div class="scenario-list"><button v-for="scenario in scenarios" :key="scenario.id" class="list-button" @click="selectScenario(scenario)">{{ scenario.name }} <small>r{{ scenario.revision }} · {{ scenario.events.length }} 事件</small></button></div><button :disabled="!selectedScenario" @click="optimizeScenario">生成受限建议</button><button :disabled="!selectedScenario" @click="startScenario">启动剧本</button><div v-if="execution" class="result"><strong>{{ execution.state }} · {{ execution.message }}</strong><button v-if="execution.state === 'awaiting_confirmation'" @click="confirmExecution">确认待执行设备事件</button><button v-if="execution.state === 'running' || execution.state === 'awaiting_confirmation'" class="danger" @click="stopExecution">停止剧本</button></div><div v-if="optimization" class="result"><strong>{{ optimization.summary }}</strong><ul><li v-for="item in optimization.suggestions">{{ item }}</li></ul><small v-for="note in optimization.safety_notes" class="note">{{ note }}</small></div></article></section>
    <section class="grid"><article class="panel"><h2>传感器插件</h2><div v-for="sensor in sensors" :key="sensor.id" class="module"><div><strong>{{ sensor.name }}</strong><small>{{ sensor.description }} {{ sensor.latest ? '最新：' + sensor.latest.value : '' }}</small></div><button @click="toggleSensor(sensor)">{{ sensor.status === 'running' ? '停止' : '启动' }}</button></div></article><article class="panel"><h2>观察历史</h2><div class="log"><div v-for="item in observations" :key="item.id">{{ item.timestamp }} · {{ item.source }} · {{ item.value }}</div><div v-if="!observations.length" class="empty">暂无观察数据</div></div><p>观察数据仅用于提示和人工复核，不会自动控制设备。</p></article></section>
    <section class="grid"><article class="panel"><h2>AI Provider</h2><select v-model="aiSettings.provider" aria-label="AI Provider"><option value="local-rules">本地规则（默认）</option><option value="openai-compatible">OpenAI 兼容接口</option></select><template v-if="aiSettings.provider === 'openai-compatible'"><input v-model="aiSettings.base_url" placeholder="https://host/v1" /><input v-model="aiSettings.model" placeholder="模型名称" /><input v-model="aiSettings.api_key" type="password" :placeholder="aiSettings.has_api_key ? '已保存密钥；留空保持不变' : 'API 密钥'" /></template><button @click="saveAiSettings">保存 AI 设置</button></article><article class="panel"><h2>AI 边界</h2><p>AI 只优化剧本表达与参数建议，不拥有设备控制权限。即使使用外部模型，输出也会被限定为建议并由 Safety Core 保底。</p></article></section>
    <section class="grid"><article class="panel"><h2>音频输出</h2><p>音频由当前浏览器播放；首次使用需启用权限。</p><button v-if="!audioEnabled" @click="enableAudio">启用音频</button><button v-else @click="testAudio">播放测试音</button></article><article class="panel"><h2>事件日志</h2><div class="log"><div v-for="entry in log" :key="entry">{{ entry }}</div><div v-if="!log.length" class="empty">等待事件…</div></div></article></section>
    <section class="safety"><div><h2>安全控制</h2><p>观察数据只作提示；不能自动升级设备动作。所有动作均经过 Safety Core。</p></div><button v-if="!safetyStopped" class="danger" @click="stop">立即停止</button><button v-else @click="resume">解除停止</button></section></main>`,
}
