import { useMemo } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import type { Timeline } from './timeline';
import { height } from './terrain';
import { heroState } from '../state';

// Port of pipeline/common.py particles(): a pure function of progress, so
// dust, clods and exhaust replay exactly when scrolling backwards.
const hash1 = (n: number) => {
  const x = Math.sin(n * 12.9898 + 78.233) * 43758.5453;
  return x - Math.floor(x);
};

const MAX_PUFFS = 420;
const MAX_CLODS = 80;

type Puff = { x: number; y: number; z: number; size: number; alpha: number; r: number; g: number; b: number; rot: number };

function simulate(p: number, tl: Timeline, out: Puff[], clods: number[][]) {
  out.length = 0;
  clods.length = 0;
  const spu = tl.secondsPerUnit;
  tl.events.forEach((ev, n) => {
    const dt = (p - ev.p) * spu;
    if (dt < 0 || dt > 4.5) return;
    const [sx, sy, sz] = ev.pos; // three.js coords
    const dump = ev.kind === 'dump';
    const count = dump ? 22 : 14;
    for (let j = 0; j < count; j++) {
      const h = n * 97 + j * 13;
      const a = hash1(h) * Math.PI * 2;
      const sp = 0.4 + hash1(h + 1) * 1.1;
      const life = 2.2 + hash1(h + 2) * 2.2;
      if (dt > life) continue;
      const t = dt / life;
      const rise = 0.4 + hash1(h + 3) * 1.2;
      const spread = sp * (1 - Math.exp(-dt * 1.5));
      const x = sx + Math.cos(a) * spread + 0.55 * dt;
      const z = sz - Math.sin(a) * spread - 0.25 * dt;
      const y0 = dump ? ev.ground + 0.4 : ev.ground;
      const y = y0 + 0.25 + rise * (1 - Math.exp(-dt * 0.9));
      const size = (0.7 + hash1(h + 4) * 0.9) * (0.6 + 1.9 * t) * (dump ? 1.4 : 1);
      const alpha = Math.pow(1 - t, 1.5) * Math.min(1, dt * 6) * (dump ? 0.55 : 0.4);
      out.push({ x, y, z, size, alpha, r: 0.52, g: 0.36, b: 0.25, rot: hash1(h + 5) * 6.283 });
    }
    if (dump) {
      for (let j = 0; j < 10; j++) {
        const h = n * 131 + j * 7;
        if (dt > 0.9) continue;
        const vx = (hash1(h) - 0.5) * 1.6, vz = -(hash1(h + 1) - 0.5) * 1.6;
        const x = sx + vx * dt, z = sz + vz * dt;
        const y = sy - 0.3 - 4.9 * dt * dt;
        const g = height(x, -z, 0, 0) + 0.0;
        if (y < g) continue;
        clods.push([x, y, z, 0.12 + hash1(h + 2) * 0.16, h]);
      }
    }
  });
  // diesel exhaust: denser and darker under load
  const rate = 7;
  const tNow = p * spu;
  for (let k = Math.max(0, Math.floor(tNow * rate) - 30); k <= Math.floor(tNow * rate); k++) {
    const ts = k / rate;
    const age = tNow - ts;
    if (age < 0 || age > 4) continue;
    const f = tl.sample(ts / spu, false);
    const load = f.load;
    const t = age / 4;
    const x = f.exhaust.x + 0.9 * age + (hash1(k) - 0.5) * 0.4 * age;
    const z = f.exhaust.z - 0.35 * age - (hash1(k + 1) - 0.5) * 0.4 * age;
    const y = f.exhaust.y + 1.1 * Math.pow(age, 0.7);
    const shade = 0.62 - 0.45 * load;
    out.push({
      x, y, z, size: 0.25 + 1.6 * t,
      alpha: Math.pow(1 - t, 2) * (0.12 + 0.5 * load * load),
      r: shade * 0.9, g: shade * 0.9, b: shade * 0.92, rot: hash1(k + 5) * 6.283,
    });
  }
}

export function Particles({ timeline, sprite }: { timeline: Timeline; sprite: THREE.Texture }) {
  const camera = useThree((s) => s.camera);
  const { puffMesh, clodMesh, puffs, clods, aAlpha, aColor, aRot } = useMemo(() => {
    const geo = new THREE.PlaneGeometry(1, 1);
    const aAlpha = new THREE.InstancedBufferAttribute(new Float32Array(MAX_PUFFS), 1);
    const aColor = new THREE.InstancedBufferAttribute(new Float32Array(MAX_PUFFS * 3), 3);
    const aRot = new THREE.InstancedBufferAttribute(new Float32Array(MAX_PUFFS), 1);
    geo.setAttribute('aAlpha', aAlpha);
    geo.setAttribute('aColor', aColor);
    geo.setAttribute('aRot', aRot);
    const mat = new THREE.MeshBasicMaterial({ map: sprite, transparent: true, depthWrite: false, fog: true });
    mat.onBeforeCompile = (shader) => {
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', '#include <common>\nattribute float aAlpha; attribute vec3 aColor; attribute float aRot; varying float vA; varying vec3 vC;')
        .replace(
          '#include <project_vertex>',
          `vec3 ip = vec3(instanceMatrix[3]);
          float sc = length(instanceMatrix[0].xyz);
          vec4 mvPosition = viewMatrix * vec4(ip, 1.0);
          float c = cos(aRot), s = sin(aRot);
          mvPosition.xy += mat2(c, s, -s, c) * position.xy * sc;
          gl_Position = projectionMatrix * mvPosition;
          vA = aAlpha; vC = aColor;`,
        );
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', '#include <common>\nvarying float vA; varying vec3 vC;')
        .replace('#include <map_fragment>', `vec4 tx = texture2D(map, vMapUv); diffuseColor = vec4(vC * 1.6, tx.a * vA);`);
    };
    const puffMesh = new THREE.InstancedMesh(geo, mat, MAX_PUFFS);
    puffMesh.frustumCulled = false;
    puffMesh.renderOrder = 10;
    const clodMesh = new THREE.InstancedMesh(
      new THREE.IcosahedronGeometry(0.5, 0),
      new THREE.MeshStandardMaterial({ color: '#6d3522', roughness: 0.95 }),
      MAX_CLODS,
    );
    clodMesh.castShadow = true;
    clodMesh.frustumCulled = false;
    return { puffMesh, clodMesh, puffs: [] as Puff[], clods: [] as number[][], aAlpha, aColor, aRot };
  }, [sprite]);

  const m = useMemo(() => new THREE.Matrix4(), []);
  const q = useMemo(() => new THREE.Quaternion(), []);
  const e = useMemo(() => new THREE.Euler(), []);
  const v = useMemo(() => new THREE.Vector3(), []);
  const s = useMemo(() => new THREE.Vector3(), []);

  useFrame(() => {
    simulate(heroState.progress, timeline, puffs, clods);
    // back-to-front so the soft sprites blend correctly
    puffs.sort((a, b) => camera.position.distanceToSquared(v.set(b.x, b.y, b.z)) - camera.position.distanceToSquared(s.set(a.x, a.y, a.z)));
    const n = Math.min(puffs.length, MAX_PUFFS);
    for (let i = 0; i < n; i++) {
      const pf = puffs[i];
      m.makeScale(pf.size, pf.size, pf.size).setPosition(pf.x, pf.y, pf.z);
      puffMesh.setMatrixAt(i, m);
      aAlpha.setX(i, pf.alpha);
      aColor.setXYZ(i, pf.r, pf.g, pf.b);
      aRot.setX(i, pf.rot);
    }
    puffMesh.count = n;
    puffMesh.instanceMatrix.needsUpdate = true;
    aAlpha.needsUpdate = aColor.needsUpdate = aRot.needsUpdate = true;
    const k = Math.min(clods.length, MAX_CLODS);
    for (let i = 0; i < k; i++) {
      const [x, y, z, size, h] = clods[i];
      e.set(h * 1.3, h * 0.7, h * 2.1);
      q.setFromEuler(e);
      m.compose(v.set(x, y, z), q, s.setScalar(size));
      clodMesh.setMatrixAt(i, m);
    }
    clodMesh.count = k;
    clodMesh.instanceMatrix.needsUpdate = true;
  });

  return (
    <>
      <primitive object={puffMesh} />
      <primitive object={clodMesh} />
    </>
  );
}
