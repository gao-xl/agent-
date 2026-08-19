import http from "node:http"
import { WebSocketServer, WebSocket } from "ws"
import {
  DglabSocket,
  DGLAB_SOCKET_VERSION,
  V4Channel,
} from "dglab-kit"

type RawDevice = Record<string, unknown>

type GatewayCommand = {
  type: "connect" | "devices" | "pulse" | "clear" | "stop"
  clientId?: string
  slotId?: string
  channel?: "A" | "B"
  durationMs?: number
  frames?: string[]
}

const port = Number(process.env.GATEWAY_PORT ?? 8765)
const socketUrl = process.env.DGLAB_SOCKET_URL ?? "wss://trex.dungeon-lab.cn/v4"
const socket = new DglabSocket({ url: socketUrl, version: DGLAB_SOCKET_VERSION.V4 })
const peers = new Set<WebSocket>()
let targetId: string | null = null
const clients = new Map<string, RawDevice[]>()

function publish(payload: unknown) {
  const message = JSON.stringify(payload)
  for (const peer of peers) {
    if (peer.readyState === WebSocket.OPEN) peer.send(message)
  }
}

socket.on("state", (state, previous) => publish({ type: "socket.state", state, previous }))
socket.on("client-attached", async (clientId) => {
  publish({ type: "client.attached", clientId })
  const result = await socket.requestDevices(clientId)
  clients.set(clientId, result.devices)
  publish({ type: "devices", clientId, devices: result.devices })
})
socket.on("client-disconnected", (clientId) => {
  clients.delete(clientId)
  publish({ type: "client.disconnected", clientId })
})
socket.on("devices", (devices, clientId) => {
  clients.set(clientId, devices)
  publish({ type: "devices", clientId, devices })
})
socket.on("device", (device, clientId) => publish({ type: "device", clientId, device }))
socket.on("action", (action) => publish({ type: "device.action", action }))
socket.on("error", (error) => publish({ type: "socket.error", error: String(error) }))

async function handle(command: GatewayCommand) {
  if (command.type === "connect") {
    if (!targetId) ({ targetId } = await socket.connect())
    return { targetId, pairUrl: `https://dungeon-lab.cn/s/?v=1&action=socket&url=${encodeURIComponent(`${socketUrl}?tid=${targetId}`)}` }
  }
  if (command.type === "devices") return { clients: [...clients.entries()] }
  if (!command.clientId || !command.slotId) throw new Error("clientId and slotId are required")
  if (command.type === "pulse") {
    if (!command.channel || !command.durationMs || !command.frames) throw new Error("pulse fields are required")
    await socket.sendPulse(command.clientId, command.slotId, command.channel === "A" ? V4Channel.A : V4Channel.B, command.durationMs, command.frames)
  } else if (command.type === "clear" || command.type === "stop") {
    await socket.clearOperate(command.clientId, { slotId: command.slotId })
  }
  return { ok: true }
}

const server = http.createServer((request, response) => {
  if (request.url === "/health") {
    response.writeHead(200, { "content-type": "application/json" })
    response.end(JSON.stringify({ status: "ok", provider: "dglab-socket", targetId }))
    return
  }
  response.writeHead(404)
  response.end()
})

const wss = new WebSocketServer({ server, path: "/ws" })
wss.on("connection", (peer) => {
  peers.add(peer)
  peer.send(JSON.stringify({ type: "gateway.connected", provider: "dglab-socket" }))
  peer.on("message", async (raw) => {
    try {
      const result = await handle(JSON.parse(raw.toString()) as GatewayCommand)
      peer.send(JSON.stringify({ type: "command.result", result }))
    } catch (error) {
      peer.send(JSON.stringify({ type: "command.error", error: String(error) }))
    }
  })
  peer.on("close", () => peers.delete(peer))
})

server.listen(port, "127.0.0.1", () => {
  console.log(`EdgePlay device gateway listening on ws://127.0.0.1:${port}/ws`)
})
