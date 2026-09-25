import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { MeshReflectorMaterial } from '@react-three/drei';
import * as THREE from 'three';
import type { Frame } from './timeline';
import { T } from './terrain';

/** Pond surface: planar reflection, rippled normal map, muddy new-pond colour. */
export function Water({ normalMap, resolution, frame }: { normalMap: THREE.Texture; resolution: number; frame: { current: Frame } }) {
  const mesh = useRef<THREE.Mesh>(null!);
  const mat = useRef<THREE.MeshStandardMaterial>(null!);
  normalMap.repeat.set(3, 3);
  useFrame((_, dt) => {
    const f = frame.current;
    const m = mesh.current;
    m.visible = f.water > 0.001;
    m.position.y = f.waterLevel;
    normalMap.offset.x += dt * 0.006;
    normalMap.offset.y += dt * 0.004;
  });
  const w = (T.pitHalf[0] + 1.5) * 2, h = (T.pitHalf[1] + 1.5) * 2;
  return (
    <mesh ref={mesh} rotation-x={-Math.PI / 2} position={[T.pitCenter[0], -3, -T.pitCenter[1]]} visible={false}>
      <planeGeometry args={[w, h]} />
      <MeshReflectorMaterial
        ref={mat as never}
        resolution={resolution}
        mirror={0.75}
        mixBlur={0.8}
        mixStrength={0.95}
        blur={[180, 60]}
        depthScale={0}
        minDepthThreshold={0.9}
        maxDepthThreshold={1}
        color="#2e2014"
        metalness={0.2}
        roughness={0.12}
        normalMap={normalMap}
        normalScale={new THREE.Vector2(0.18, 0.18)}
        distortion={0.12}
        distortionMap={normalMap}
      />
    </mesh>
  );
}
