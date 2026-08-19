import { createApp, ref } from "vue"
import "./style.css"

const App = {
  setup() {
    const devices = ref<any[]>([])
    const safetyStopped = ref(false)
    const status = ref("正在连接后端…")

    async function loadDevices() {
      const response = await fetch("/api/devices")
      devices.value = await response.json()
      status.value = "后端已连接"
    }

    async function stop() {
      await fetch("/api/safety/stop", { method: "POST" })
      safetyStopped.value = true
    }

    async function resume() {
      await fetch("/api/safety/resume", { method: "POST" })
      safetyStopped.value = false
    }

    loadDevices().catch(() => (status.value = "无法连接后端"))
    return { devices, safetyStopped, status, loadDevices, stop, resume }
  },
  template: `
    <main class="shell">
      <header>
        <div>
          <p class="eyebrow">EDGEPLAY PLATFORM</p>
          <h1>AI 互动设备控制台</h1>
          <p class="subtitle">瑞芯微边缘节点 · 模块化设备 · 本地优先</p>
        </div>
        <span class="status">{{ status }}</span>
      </header>
      <section class="grid">
        <article class="panel">
          <h2>设备</h2>
          <div v-if="devices.length === 0" class="empty">暂无设备</div>
          <div v-for="device in devices" :key="device.id" class="device">
            <div><strong>{{ device.name }}</strong><small>{{ device.provider }} · {{ device.model }}</small></div>
            <span class="tag">{{ device.state }}</span>
          </div>
          <button @click="loadDevices">刷新设备</button>
        </article>
        <article class="panel">
          <h2>模块</h2>
          <div class="module">剧本引擎 <span>准备接入</span></div>
          <div class="module">AI Provider <span>准备接入</span></div>
          <div class="module">音频输出 <span>准备接入</span></div>
          <div class="module">郊狼 / 役次元 <span>Provider 预留</span></div>
        </article>
      </section>
      <section class="safety">
        <div><h2>安全控制</h2><p>所有设备动作都必须经过 Safety Core。</p></div>
        <button v-if="!safetyStopped" class="danger" @click="stop">立即停止</button>
        <button v-else @click="resume">解除停止</button>
      </section>
    </main>
  `
}

import { Dashboard } from "./dashboard"

createApp(Dashboard).mount("#app")
