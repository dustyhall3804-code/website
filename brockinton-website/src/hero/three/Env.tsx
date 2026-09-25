import { useMemo } from 'react';
import * as THREE from 'three';
import type { GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js';

/** Fence, round bales and the Ouachita-style ridges from env.glb. */
export function Env({ gltf }: { gltf: GLTF }) {
  const scene = useMemo(() => {
    const s = gltf.scene;
    s.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      const mat = m.material as THREE.MeshStandardMaterial;
      if (o.name.startsWith('Ridges')) {
        mat.setValues({ color: '#ffffff', roughness: 1, metalness: 0, vertexColors: true });
        m.receiveShadow = false;
      } else if (o.name.startsWith('HayBale')) {
        mat.setValues({ color: '#b39a60', roughness: 0.95, metalness: 0 });
        m.castShadow = m.receiveShadow = true;
      } else if (o.name.startsWith('FencePosts')) {
        mat.setValues({ color: '#6b5a48', roughness: 0.9, metalness: 0 });
        m.castShadow = true;
      } else if (o.name.startsWith('FenceWire')) {
        mat.setValues({ color: '#8a8580', roughness: 0.4, metalness: 0.85 });
      }
      mat.needsUpdate = true;
    });
    return s;
  }, [gltf]);
  return <primitive object={scene} />;
}
