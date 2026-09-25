import { useEffect, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import type { GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { heroState } from '../state';

// Material tuning by Blender material name (the GLB carries paint and mud as vertex colours).
const TUNE: Record<string, Partial<THREE.MeshStandardMaterialParameters>> = {
  Paint: { color: '#ffffff', roughness: 0.42, metalness: 0.0 },
  Undercarriage: { color: '#ffffff', roughness: 0.82, metalness: 0.15 },
  Load: { color: '#ffffff', roughness: 0.97, metalness: 0 },
  Steel: { color: '#34322f', roughness: 0.45, metalness: 0.7 },
  Chrome: { color: '#dcdcdc', roughness: 0.1, metalness: 1.0 },
  Glass: { color: '#0b0d0f', roughness: 0.04, metalness: 0.35, envMapIntensity: 1.4 },
  Trim: { color: '#141414', roughness: 0.55, metalness: 0 },
  Decal: { color: '#121110', roughness: 0.5, metalness: 0 },
  Lens: { color: '#cfcfc9', roughness: 0.08, metalness: 0 },
};

export function Excavator({ gltf }: { gltf: GLTF }) {
  const { scene, mixer, clip } = useMemo(() => {
    const scene = gltf.scene;
    scene.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      m.castShadow = true;
      m.receiveShadow = true;
      const mats = Array.isArray(m.material) ? m.material : [m.material];
      for (const mat of mats as THREE.MeshStandardMaterial[]) {
        const t = TUNE[mat.name];
        if (t) mat.setValues(t);
        mat.vertexColors = !!m.geometry.attributes.color;
        mat.needsUpdate = true;
      }
    });
    const mixer = new THREE.AnimationMixer(scene);
    const clip = gltf.animations[0];
    const action = mixer.clipAction(clip);
    action.setLoop(THREE.LoopOnce, 1);
    action.clampWhenFinished = true;
    action.play();
    return { scene, mixer, clip };
  }, [gltf]);

  useEffect(() => () => void mixer.stopAllAction(), [mixer]);

  useFrame(() => {
    // the clip spans progress 0..1; setTime is absolute, so scrubbing back is exact
    mixer.setTime(heroState.progress * clip.duration * 0.99999);
  });

  return <primitive object={scene} />;
}
