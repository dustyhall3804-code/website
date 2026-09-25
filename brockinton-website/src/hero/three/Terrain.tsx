import { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { terrainGLSL } from './terrain';
import type { Frame } from './timeline';
import type { GroundTextures } from './assets';

const R = 900;          // half-extent of the ground plane (m)
const CX = 1.0, CY = 4.5;

/** Warped grid: dense around the pit, coarse toward the horizon. */
function makeGeometry(segments: number) {
  const g = new THREE.PlaneGeometry(2, 2, segments, segments);
  g.rotateX(-Math.PI / 2);
  const pos = g.attributes.position as THREE.BufferAttribute;
  const warp = (u: number) => Math.sign(u) * Math.pow(Math.abs(u), 2.6) * R;
  for (let i = 0; i < pos.count; i++) {
    const u = pos.getX(i), v = pos.getZ(i);
    pos.setXYZ(i, CX + warp(u), 0, -(CY + warp(-v)));
  }
  g.computeBoundingSphere();
  g.boundingSphere!.radius = R * 1.5;
  return g;
}

export function Terrain({ tex, segments, frame }: { tex: GroundTextures; segments: number; frame: { current: Frame } }) {
  const geometry = useMemo(() => makeGeometry(segments), [segments]);
  const uniforms = useRef({
    uPit: { value: 0 },
    uSpoil: { value: 0 },
    uWaterLevel: { value: -10 },
    uPasture: { value: tex.pasture },
    uPastureN: { value: tex.pastureN },
    uTopsoil: { value: tex.topsoil },
    uClay: { value: tex.clay },
    uClayN: { value: tex.clayN },
    uGravel: { value: tex.gravel },
    uShale: { value: tex.shale },
    uShaleN: { value: tex.shaleN },
  }).current;

  const material = useMemo(() => {
    const m = new THREE.MeshStandardMaterial({ roughness: 0.9, metalness: 0 });
    m.onBeforeCompile = (shader) => {
      Object.assign(shader.uniforms, uniforms);
      shader.vertexShader = shader.vertexShader
        .replace(
          '#include <common>',
          `#include <common>
          uniform float uPit; uniform float uSpoil;
          varying vec2 vBP; varying float vOrig; varying float vWork; varying float vSpoil; varying float vH; varying vec3 vNW;
          ${terrainGLSL}`,
        )
        .replace(
          '#include <beginnormal_vertex>',
          `vec2 bp = vec2(position.x, -position.z);
          float e = 0.12;
          float hx = terrainHeight(bp + vec2(e, 0.0), uPit, uSpoil) - terrainHeight(bp - vec2(e, 0.0), uPit, uSpoil);
          float hy = terrainHeight(bp + vec2(0.0, e), uPit, uSpoil) - terrainHeight(bp - vec2(0.0, e), uPit, uSpoil);
          vec3 objectNormal = normalize(vec3(-hx / (2.0 * e), 1.0, hy / (2.0 * e)));
          vNW = objectNormal;`,
        )
        .replace(
          '#include <begin_vertex>',
          `float h = terrainHeight(bp, uPit, uSpoil);
          vec3 transformed = vec3(position.x, h, position.z);
          vBP = bp; vOrig = baseHeight(bp); vWork = workMask(bp);
          vSpoil = SP_H * uSpoil * spoilMask(bp); vH = h;`,
        );
      shader.fragmentShader = shader.fragmentShader
        .replace(
          '#include <common>',
          `#include <common>
          uniform float uWaterLevel;
          uniform sampler2D uPasture, uPastureN, uTopsoil, uClay, uClayN, uGravel, uShale, uShaleN;
          varying vec2 vBP; varying float vOrig; varying float vWork; varying float vSpoil; varying float vH; varying vec3 vNW;
          float band(float x, float e, float w) { return smoothstep(e - w, e + w, x); }
          vec3 tri(sampler2D t, vec2 top, vec2 side, float wTop) {
            return mix(texture2D(t, side).rgb, texture2D(t, top).rgb, wTop);
          }
          float gNoise(vec2 p) { return sin(p.x * 1.3 + sin(p.y * 0.7)) * 0.5 + sin(p.y * 1.9 + p.x * 0.4) * 0.3 + sin((p.x + p.y) * 3.7) * 0.2; }`,
        )
        .replace(
          '#include <map_fragment>',
          `vec3 nW = normalize(vNW);
          float wTop = smoothstep(0.55, 0.85, nW.y);
          vec2 topUV = vBP / 2.6;
          vec2 sideUV = (abs(nW.x) > abs(nW.z) ? vec2(vBP.y, vH) : vec2(vBP.x, vH)) / 2.6;
          vec3 pasture = texture2D(uPasture, vBP / 7.0).rgb;
          pasture *= 0.92 + 0.16 * texture2D(uPasture, vBP / 41.0).g;          // break up tiling at distance
          float depth = vOrig - vH + gNoise(vBP * 0.6) * 0.12;
          vec3 col = tri(uTopsoil, topUV, sideUV, wTop);
          col = mix(col, tri(uClay, topUV, sideUV, wTop), band(depth, 0.32, 0.04));
          col = mix(col, tri(uGravel, topUV, sideUV, wTop), band(depth, 1.55, 0.05));
          col = mix(col, tri(uShale, topUV, sideUV, wTop), band(depth, 2.35, 0.05));
          vec3 spoilCol = mix(texture2D(uClay, topUV * 1.3).rgb, texture2D(uTopsoil, topUV).rgb, smoothstep(0.35, 0.8, gNoise(vBP * 2.3) * 0.5 + 0.5));
          col = mix(col, spoilCol, smoothstep(0.02, 0.14, vSpoil));
          col = mix(pasture, col, vWork);
          float wet = clamp((uWaterLevel + 0.18 - vH) * 5.0, 0.0, 1.0);
          col *= mix(vec3(1.0), vec3(0.5, 0.45, 0.42), wet);
          diffuseColor.rgb = col;`,
        )
        .replace(
          '#include <roughnessmap_fragment>',
          `float roughnessFactor = mix(0.93, 0.86, vWork) - 0.6 * wet;`,
        )
        .replace(
          '#include <normal_fragment_maps>',
          `vec3 nm = mix(texture2D(uPastureN, vBP / 7.0).xyz,
                        mix(texture2D(uClayN, mix(sideUV, topUV, wTop)).xyz, texture2D(uShaleN, mix(sideUV, topUV, wTop)).xyz,
                            band(depth, 2.35, 0.05)), vWork) * 2.0 - 1.0;
          vec3 nPert = normalize(nW + vec3(nm.x, 0.0, -nm.y) * 0.9 * wTop + vec3(nm.x, nm.y, 0.0) * 0.6 * (1.0 - wTop));
          normal = normalize((viewMatrix * vec4(nPert, 0.0)).xyz);`,
        );
    };
    m.customProgramCacheKey = () => 'brockinton-terrain';
    return m;
  }, [uniforms]);

  useFrame(() => {
    const f = frame.current;
    uniforms.uPit.value = f.pit;
    uniforms.uSpoil.value = f.spoil;
    uniforms.uWaterLevel.value = f.water > 0.001 ? f.waterLevel : -10;
  });

  return <mesh geometry={geometry} material={material} receiveShadow frustumCulled={false} />;
}
