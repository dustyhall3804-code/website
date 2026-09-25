// Terrain height field shared by the GPU (GLSL) and CPU (TS). Mirrors
// pipeline/common.py and terrain_np.py. All functions take Blender-plane
// coordinates (bx, by) where three.js (x, z) = (bx, -by).

export const T = {
  pitCenter: [0.35, 7.25],
  pitHalf: [4.9, 3.25],
  pitWall: 1.75,
  pitDepth: 3.0,
  spoilYaw: -100,
  spoilDist: 7.6,
  spoilRadius: [3.4, 2.4],
  spoilHeight: 2.3,
  armX: 0.28,
  strata: [0.32, 1.55, 2.35],
};

const rad = (T.spoilYaw * Math.PI) / 180;
export const spoilCenter: [number, number] = [
  T.armX * Math.cos(rad) - T.spoilDist * Math.sin(rad),
  T.armX * Math.sin(rad) + T.spoilDist * Math.cos(rad),
];

const clamp01 = (x: number) => (x < 0 ? 0 : x > 1 ? 1 : x);
const smooth = (x: number) => {
  x = clamp01(x);
  return x * x * (3 - 2 * x);
};

export function baseHeight(x: number, y: number) {
  let h = 0.35 * Math.sin(x * 0.045 + 1.3) * Math.cos(y * 0.038 - 0.4);
  h += 0.18 * Math.sin(x * 0.11 - y * 0.07 + 2.1);
  h += 0.06 * Math.sin(x * 0.31 + y * 0.27);
  const d = Math.hypot(x - 0.5, y - 3.5);
  return h * smooth((d - 9) / 14);
}

export function pitMask(x: number, y: number) {
  const dx = Math.abs(x - T.pitCenter[0]) - (T.pitHalf[0] - T.pitWall);
  const dy = Math.abs(y - T.pitCenter[1]) - (T.pitHalf[1] - T.pitWall);
  let d = Math.hypot(Math.max(dx, 0), Math.max(dy, 0)) + Math.min(Math.max(dx, dy), 0);
  d += 0.18 * Math.sin(x * 1.7 + y * 0.9) + 0.1 * Math.sin(y * 2.3 - x);
  return smooth(1 - d / T.pitWall);
}

export function spoilMask(x: number, y: number) {
  const [cx, cy] = spoilCenter;
  const lx = (x - cx) * Math.cos(rad) + (y - cy) * Math.sin(rad);
  const ly = -(x - cx) * Math.sin(rad) + (y - cy) * Math.cos(rad);
  const r = Math.hypot(lx / T.spoilRadius[1], ly / T.spoilRadius[0]);
  const lumps = 0.06 * Math.sin(x * 3.1 + y * 1.3) + 0.05 * Math.sin(y * 4.7 - x * 2.2);
  const m = clamp01(1 - r * r);
  return Math.pow(m, 1.15) + lumps * m;
}

export function height(x: number, y: number, pit: number, spoil: number) {
  return baseHeight(x, y) - T.pitDepth * pit * pitMask(x, y) + T.spoilHeight * spoil * spoilMask(x, y);
}

export function workMask(x: number, y: number) {
  const dx = Math.abs(x - T.pitCenter[0]) - (T.pitHalf[0] + 1.2);
  const dy = Math.abs(y - T.pitCenter[1]) - (T.pitHalf[1] + 1.2);
  const dPit = Math.hypot(Math.max(dx, 0), Math.max(dy, 0)) + Math.min(Math.max(dx, dy), 0);
  const [cx, cy] = spoilCenter;
  const dSp = Math.hypot((x - cx) / 1.25, (y - cy) / 1.1) - T.spoilRadius[0];
  const px = Math.abs(x) - 2.4;
  const py = Math.abs(y - 0.2) - 3.4;
  const dPad = Math.hypot(Math.max(px, 0), Math.max(py, 0)) + Math.min(Math.max(px, py), 0);
  let d = Math.min(dPit, dSp, dPad);
  d += 0.55 * Math.sin(x * 0.7 + 1.7 * Math.cos(y * 0.45)) + 0.35 * Math.sin(y * 1.9 + x * 0.4) + 0.2 * Math.sin(x * 3.1 - y * 2.3);
  return smooth(1 - d / 1.6);
}

/** GLSL version of the same functions (inject into shaders). */
export const terrainGLSL = /* glsl */ `
const vec2 PIT_C = vec2(${T.pitCenter[0].toFixed(4)}, ${T.pitCenter[1].toFixed(4)});
const vec2 PIT_H = vec2(${T.pitHalf[0].toFixed(4)}, ${T.pitHalf[1].toFixed(4)});
const float PIT_W = ${T.pitWall.toFixed(4)};
const float PIT_D = ${T.pitDepth.toFixed(4)};
const vec2 SP_C = vec2(${spoilCenter[0].toFixed(4)}, ${spoilCenter[1].toFixed(4)});
const float SP_A = ${rad.toFixed(6)};
const vec2 SP_R = vec2(${T.spoilRadius[0].toFixed(4)}, ${T.spoilRadius[1].toFixed(4)});
const float SP_H = ${T.spoilHeight.toFixed(4)};

float sm01(float x) { x = clamp(x, 0.0, 1.0); return x * x * (3.0 - 2.0 * x); }

float baseHeight(vec2 p) {
  float h = 0.35 * sin(p.x * 0.045 + 1.3) * cos(p.y * 0.038 - 0.4);
  h += 0.18 * sin(p.x * 0.11 - p.y * 0.07 + 2.1);
  h += 0.06 * sin(p.x * 0.31 + p.y * 0.27);
  float d = length(p - vec2(0.5, 3.5));
  return h * sm01((d - 9.0) / 14.0);
}
float pitMask(vec2 p) {
  vec2 q = abs(p - PIT_C) - (PIT_H - PIT_W);
  float d = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0);
  d += 0.18 * sin(p.x * 1.7 + p.y * 0.9) + 0.1 * sin(p.y * 2.3 - p.x);
  return sm01(1.0 - d / PIT_W);
}
float spoilMask(vec2 p) {
  vec2 o = p - SP_C;
  float lx = o.x * cos(SP_A) + o.y * sin(SP_A);
  float ly = -o.x * sin(SP_A) + o.y * cos(SP_A);
  float r = length(vec2(lx / SP_R.y, ly / SP_R.x));
  float lumps = 0.06 * sin(p.x * 3.1 + p.y * 1.3) + 0.05 * sin(p.y * 4.7 - p.x * 2.2);
  float m = clamp(1.0 - r * r, 0.0, 1.0);
  return pow(m, 1.15) + lumps * m;
}
float workMask(vec2 p) {
  vec2 q = abs(p - PIT_C) - (PIT_H + 1.2);
  float dPit = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0);
  float dSp = length((p - SP_C) / vec2(1.25, 1.1)) - SP_R.x;
  vec2 pq = vec2(abs(p.x) - 2.4, abs(p.y - 0.2) - 3.4);
  float dPad = length(max(pq, 0.0)) + min(max(pq.x, pq.y), 0.0);
  float d = min(min(dPit, dSp), dPad);
  d += 0.55 * sin(p.x * 0.7 + 1.7 * cos(p.y * 0.45)) + 0.35 * sin(p.y * 1.9 + p.x * 0.4) + 0.2 * sin(p.x * 3.1 - p.y * 2.3);
  return sm01(1.0 - d / 1.6);
}
float terrainHeight(vec2 p, float pit, float spoil) {
  return baseHeight(p) - PIT_D * pit * pitMask(p) + SP_H * spoil * spoilMask(p);
}
`;
