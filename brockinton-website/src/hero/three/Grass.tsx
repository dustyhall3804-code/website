import { useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { baseHeight, workMask } from './terrain';

/** One clump of late-summer pasture grass: several curved, tapering blades. */
function clumpGeometry() {
  const blades = 7, segs = 4;
  const pos: number[] = [], col: number[] = [], idx: number[] = [];
  const rnd = mulberry(7);
  const base = new THREE.Color(), tip = new THREE.Color(), c = new THREE.Color();
  const greens = ['#6d7a35', '#84893d', '#96914a'];
  const straws = ['#b3a45c', '#c4b06a', '#d2bf7e', '#c9b476'];
  for (let b = 0; b < blades; b++) {
    const ang = rnd() * Math.PI * 2;
    const r = rnd() * 0.08;
    const bx = Math.cos(ang) * r, bz = Math.sin(ang) * r;
    const h = 0.32 + rnd() * 0.42;
    const lean = 0.15 + rnd() * 0.45;
    const face = rnd() * Math.PI * 2;
    const w = 0.012 + rnd() * 0.01;
    base.set(greens[Math.floor(rnd() * 3)]).convertSRGBToLinear();
    tip.set(straws[Math.floor(rnd() * 4)]).convertSRGBToLinear();
    const start = pos.length / 3;
    for (let s = 0; s <= segs; s++) {
      const t = s / segs;
      const px = bx + Math.cos(ang) * lean * h * t * t;
      const pz = bz + Math.sin(ang) * lean * h * t * t;
      const py = h * t * (1 - 0.25 * lean * t);
      const ww = w * (1 - t * 0.85);
      const ox = Math.cos(face) * ww, oz = Math.sin(face) * ww;
      pos.push(px - ox, py, pz - oz, px + ox, py, pz + oz);
      c.copy(base).lerp(tip, t).multiplyScalar(0.75 + 0.35 * t);
      col.push(c.r, c.g, c.b, c.r, c.g, c.b);
      if (s > 0) {
        const a = start + (s - 1) * 2;
        idx.push(a, a + 1, a + 3, a, a + 3, a + 2);
      }
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
  g.setIndex(idx);
  // blade normals face sideways with a little lift, so blades catch a low sun
  // the way real grass does instead of shading like flat ground
  const n = new Float32Array(pos.length);
  for (let i = 0; i < n.length; i += 6) {
    const dx = pos[i + 3] - pos[i], dz = pos[i + 5] - pos[i + 2];
    const len = Math.hypot(dx, dz) || 1;
    const nx = -dz / len, nz = dx / len;
    for (const o of [0, 3]) { n[i + o] = nx * 0.8; n[i + o + 1] = 0.6; n[i + o + 2] = nz * 0.8; }
  }
  g.setAttribute('normal', new THREE.BufferAttribute(n, 3));
  return g;
}

function mulberry(a: number) {
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** clear: low camera positions (Blender x, y) that must not look through a clump */
export function Grass({ count, clear }: { count: number; clear: [number, number][] }) {
  const { mesh, material } = useMemo(() => {
    const geo = clumpGeometry();
    const material = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.75, side: THREE.DoubleSide });
    const uTime = { value: 0 };
    material.userData.uTime = uTime;
    material.onBeforeCompile = (shader) => {
      shader.uniforms.uTime = uTime;
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', '#include <common>\nuniform float uTime;')
        .replace(
          '#include <begin_vertex>',
          `#include <begin_vertex>
          // wind: gusts roll across the pasture, tips move most
          vec3 ip = vec3(instanceMatrix[3][0], 0.0, instanceMatrix[3][2]);
          float k = position.y * position.y * 2.2;
          float gust = sin(ip.x * 0.08 + ip.z * 0.05 + uTime * 1.3) * 0.5 + 0.5;
          float flutter = sin(uTime * 3.1 + ip.x * 1.7 + ip.z * 1.3);
          transformed.x += k * (0.1 * gust + 0.03 * flutter);
          transformed.z += k * (0.05 * gust + 0.02 * flutter);`,
        );
    };
    const mesh = new THREE.InstancedMesh(geo, material, count);
    const rnd = mulberry(42);
    const m = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3();
    const up = new THREE.Vector3(0, 1, 0);
    const tint = new THREE.Color();
    let n = 0, tries = 0;
    while (n < count && tries < count * 6) {
      tries++;
      // denser near the dig, thinning out toward the treeline
      const r = 3 + 72 * Math.pow(rnd(), 1.7);
      const a = rnd() * Math.PI * 2;
      const bx = 1 + Math.cos(a) * r, by = 4.5 + Math.sin(a) * r;
      if (workMask(bx, by) > 0.25) continue;
      if (clear.some(([cx, cy]) => Math.hypot(bx - cx, by - cy) < 2.8)) continue;
      const sc = (0.75 + rnd() * 0.6) * (1 + r / 45);
      p.set(bx, baseHeight(bx, by) - 0.02, -by);
      q.setFromAxisAngle(up, rnd() * Math.PI * 2);
      s.set(sc, sc * (0.8 + rnd() * 0.5), sc);
      mesh.setMatrixAt(n, m.compose(p, q, s));
      const dry = rnd();
      tint.setRGB(0.92 + dry * 0.16, 0.92 + dry * 0.08, 0.85 + dry * 0.05);
      mesh.setColorAt(n, tint);
      n++;
    }
    mesh.count = n;
    mesh.receiveShadow = true;
    mesh.frustumCulled = false;
    mesh.instanceMatrix.needsUpdate = true;
    return { mesh, material };
  }, [count, clear]);

  useFrame((_, dt) => {
    (material.userData.uTime as { value: number }).value += Math.min(dt, 0.05);
  });

  return <primitive object={mesh} />;
}
