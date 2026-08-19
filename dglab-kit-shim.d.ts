// dglab-kit 1.0.3 exposes these runtime symbols but its bundled root .d.ts
// currently omits their re-exports. Keep this small compatibility shim until
// the upstream declaration package is corrected.
declare module "dglab-kit" {
  export const DGLAB_SOCKET_VERSION: { V4: "v4" }
  export const V4Channel: { A: number; B: number }
  export const DglabSocket: new (options: { url?: string; version?: string }) => any
}
