import { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { PerformanceMonitor, Sky } from '@react-three/drei';
import * as THREE from 'three';
import { heroState, type Quality } from '../state';
import { QUALITY, downgrade } from './quality';
import { loadHeroAssets, type HeroAssets } from './assets';
import { Timeline, type Frame } from './timeline';
import { Terrain } from './Terrain';
import { Grass } from './Grass';
import { Trees } from './Trees';
import { Env } from './Env';
import { Water } from './Water';
import { Excavator } from './Excavator';
import { Particles } from './Particles';
import { CameraRig } from './CameraRig';
import { Effects } from './Effects';

// Late-afternoon sun from the west-southwest (matches the Blender scene).
const SUN_AZ = (208 * Math.PI) / 180, SUN_EL = (17 * Math.PI) / 180;
const SUN_DIR = new THREE.Vector3(
  Math.cos(SUN_AZ) * Math.cos(SUN_EL),
  Math.sin(SUN_EL),
  -Math.sin(SUN_AZ) * Math.cos(SUN_EL),
); // points toward the sun, three.js axes
const FOG = new THREE.Color('#b9c1c4');

export type HeroCallbacks = {
  onLoadProgress: (f: number) => void;
  onReady: () => void;
  onError: (e: unknown) => void;
};

/** Pauses rendering while the hero is off screen or the tab is hidden. */
function Visibility() {
  const setFrameloop = useThree((s) => s.setFrameloop);
  useEffect(() => {
    let cur = 'always';
    const id = setInterval(() => {
      const want = heroState.visible && !document.hidden ? 'always' : 'never';
      if (want !== cur) setFrameloop((cur = want) as 'always' | 'never');
    }, 200);
    return () => clearInterval(id);
  }, [setFrameloop]);
  return null;
}

function SceneSetup({ hdri }: { hdri: THREE.Texture }) {
  const { gl, scene } = useThree();
  useEffect(() => {
    gl.shadowMap.autoUpdate = false;
    gl.shadowMap.needsUpdate = true;
    scene.environment = hdri;
    scene.environmentIntensity = 0.7;
    scene.fog = new THREE.FogExp2(FOG, 0.0009);
    return () => { scene.environment = null; };
  }, [gl, scene, hdri]);
  return null;
}

function Sun({ size }: { size: number }) {
  const light = useRef<THREE.DirectionalLight>(null!);
  const target = useMemo(() => new THREE.Object3D(), []);
  useEffect(() => {
    target.position.set(1.5, 0, -4);
    light.current.target = target;
    light.current.position.copy(SUN_DIR).multiplyScalar(80).add(target.position);
  }, [target]);
  return (
    <>
      <primitive object={target} />
      <directionalLight
        ref={light}
        color="#ffeed8"
        intensity={4.4}
        castShadow
        shadow-mapSize={[size, size]}
        shadow-bias={-0.0004}
        shadow-normalBias={0.03}
        shadow-camera-left={-24}
        shadow-camera-right={24}
        shadow-camera-top={24}
        shadow-camera-bottom={-24}
        shadow-camera-near={10}
        shadow-camera-far={180}
      />
      <hemisphereLight args={['#c8d6e6', '#6b5a3f', 0.55]} />
    </>
  );
}

function ReadySignal({ onReady }: { onReady: () => void }) {
  const frames = useRef(0);
  useFrame(() => {
    if (++frames.current === 3) onReady();
  });
  return null;
}

function Scene({ assets, quality, cb }: { assets: HeroAssets; quality: Quality; cb: HeroCallbacks }) {
  const q = QUALITY[quality];
  const timeline = useMemo(() => new Timeline(assets.timeline), [assets]);
  const fxTimeline = useMemo(() => new Timeline(assets.timeline), [assets]);
  const frame = useRef<Frame>(timeline.sample(0, false));
  const focus = useRef(10);
  // every low camera position on the path (both layouts), so no grass sits in front of the lens
  const clear = useMemo(() => {
    const pts: [number, number][] = [];
    for (const r of assets.timeline.samples)
      for (const o of [0, 7]) if (r[o + 1] < 2.5) pts.push([r[o], -r[o + 2]]);
    return pts.filter((_, i) => i % 3 === 0);
  }, [assets]);
  return (
    <>
      <SceneSetup hdri={assets.hdri} />
      <CameraRig timeline={timeline} frame={frame} focus={focus} />
      <Sky
        distance={4500}
        sunPosition={SUN_DIR.toArray() as [number, number, number]}
        turbidity={7.5}
        rayleigh={2.2}
        mieCoefficient={0.006}
        mieDirectionalG={0.86}
      />
      <Sun size={q.shadowMap} />
      <Terrain tex={assets.ground} segments={q.terrainSegments} frame={frame} />
      <Grass count={q.grass} clear={clear} />
      <Trees list={assets.treeList} atlas={assets.trees} sunDir={SUN_DIR} density={q.treeCount} />
      <Env gltf={assets.env} />
      <Excavator gltf={assets.excavator} />
      <Water normalMap={assets.waterNormal} resolution={q.reflectorRes} frame={frame} />
      <Particles timeline={fxTimeline} sprite={assets.puff} />
      <Effects q={q} focus={focus} />
      <ReadySignal onReady={cb.onReady} />
    </>
  );
}

function Loader({ cb, onLoaded }: { cb: HeroCallbacks; onLoaded: (a: HeroAssets) => void }) {
  const gl = useThree((s) => s.gl);
  useEffect(() => {
    loadHeroAssets(gl, cb.onLoadProgress).then(onLoaded, cb.onError);
  }, [gl]); // eslint-disable-line react-hooks/exhaustive-deps
  return null;
}

export function HeroCanvas(cb: HeroCallbacks) {
  const [assets, setAssets] = useState<HeroAssets | null>(null);
  const [quality, setQuality] = useState<Quality>(heroState.quality);
  const q = QUALITY[quality];
  const [dpr, setDpr] = useState(Math.min(window.devicePixelRatio, q.dpr[1]));

  return (
    <Canvas
      flat
      shadows="soft"
      dpr={dpr}
      gl={{ antialias: false, powerPreference: 'high-performance', stencil: false }}
      camera={{ fov: 35, near: 0.1, far: 5000, position: [-27, 8, 21] }}
      onCreated={({ gl }) => {
        gl.outputColorSpace = THREE.SRGBColorSpace;
        gl.toneMapping = THREE.NoToneMapping;
      }}
    >
      <Visibility />
      {!assets && <Loader cb={cb} onLoaded={setAssets} />}
      {assets && (
        <PerformanceMonitor
          bounds={() => [45, 58]}
          flipflops={2}
          onDecline={() => {
            // first shed resolution, then drop a quality tier
            if (dpr > q.dpr[0] + 0.05) setDpr((d) => Math.max(q.dpr[0], d - 0.25));
            else if (quality !== 'low') {
              const next = downgrade(quality);
              heroState.quality = next;
              setQuality(next);
            }
          }}
        >
          <Suspense fallback={null}>
            <Scene assets={assets} quality={quality} cb={cb} />
          </Suspense>
        </PerformanceMonitor>
      )}
    </Canvas>
  );
}
