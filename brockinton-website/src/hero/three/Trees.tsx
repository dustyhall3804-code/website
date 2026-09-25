import { useMemo } from 'react';
import * as THREE from 'three';

// Impostor atlas (pipeline/render_tree_cards.py): 3 x 2 cards, row-major from the top-left.
const CELLS: Record<string, number> = {
  Tree_cedar_6: 0, Tree_oak_1: 1, Tree_oak_2: 2, Tree_oak_3: 3, Tree_pine_4: 4, Tree_pine_5: 5,
};
const CARD_W = 17.32, CARD_H = 26, CARD_BASE = -0.5;

type TreeRec = { kind: string; x: number; y: number; z: number; s: number };

export function Trees({ list, atlas, sunDir, density }: { list: TreeRec[]; atlas: THREE.Texture; sunDir: THREE.Vector3; density: number }) {
  const mesh = useMemo(() => {
    const kept = list.filter((_, i) => ((i * 2654435761) % 1000) / 1000 < density);
    const geo = new THREE.PlaneGeometry(1, 1);
    const cell = new Float32Array(kept.length);
    const mat = new THREE.MeshBasicMaterial({ map: atlas, alphaTest: 0.45, side: THREE.DoubleSide, fog: true });
    mat.onBeforeCompile = (shader) => {
      shader.uniforms.uSun = { value: sunDir.clone().setY(0).normalize() };
      shader.vertexShader = shader.vertexShader
        .replace(
          '#include <common>',
          `#include <common>
          attribute float aCell; uniform vec3 uSun; varying vec2 vCellUv; varying float vShade;`,
        )
        .replace(
          '#include <project_vertex>',
          `vec3 ip = vec3(instanceMatrix[3]);
          float sc = length(instanceMatrix[0].xyz);
          vec3 toCam = cameraPosition - ip; toCam.y = 0.0; toCam = normalize(toCam);
          vec3 right = vec3(toCam.z, 0.0, -toCam.x);
          vec3 world = ip + right * position.x * ${CARD_W.toFixed(2)} * sc
                     + vec3(0.0, (position.y + 0.5) * ${CARD_H.toFixed(2)} * sc + ${CARD_BASE.toFixed(2)} * sc, 0.0);
          vec4 mvPosition = viewMatrix * vec4(world, 1.0);
          gl_Position = projectionMatrix * mvPosition;
          float col = mod(aCell, 3.0), row = floor(aCell / 3.0);
          vCellUv = vec2((col * 683.0 + uv.x * 682.0) / 2048.0, row * 0.5 + (1.0 - uv.y) * 0.5);
          // cards were lit from the sun side; the far side of a tree reads darker
          vShade = mix(0.62, 1.0, dot(toCam, uSun) * 0.5 + 0.5);`,
        );
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', '#include <common>\nvarying vec2 vCellUv; varying float vShade;')
        .replace(
          '#include <map_fragment>',
          `vec4 sampledDiffuseColor = texture2D(map, vCellUv);
          diffuseColor *= sampledDiffuseColor;
          diffuseColor.rgb *= vShade;`,
        );
    };
    mat.customProgramCacheKey = () => 'brockinton-trees';
    const m = new THREE.InstancedMesh(geo, mat, kept.length);
    const mtx = new THREE.Matrix4();
    kept.forEach((t, i) => {
      mtx.makeScale(t.s, t.s, t.s).setPosition(t.x, t.z, -t.y);
      m.setMatrixAt(i, mtx);
      cell[i] = CELLS[t.kind] ?? 1;
    });
    geo.setAttribute('aCell', new THREE.InstancedBufferAttribute(cell, 1));
    m.frustumCulled = false;
    return m;
  }, [list, atlas, sunDir, density]);
  return <primitive object={mesh} />;
}
