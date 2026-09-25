import * as THREE from 'three';
import { GLTFLoader, type GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { KTX2Loader } from 'three/examples/jsm/loaders/KTX2Loader.js';
import { EXRLoader } from 'three/examples/jsm/loaders/EXRLoader.js';
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js';
import type { TimelineData } from './timeline';

export type GroundTextures = Record<
  'pasture' | 'pastureN' | 'topsoil' | 'clay' | 'clayN' | 'gravel' | 'shale' | 'shaleN',
  THREE.Texture
>;

export type HeroAssets = {
  timeline: TimelineData;
  excavator: GLTF;
  env: GLTF;
  ground: GroundTextures;
  waterNormal: THREE.Texture;
  puff: THREE.Texture;
  trees: THREE.Texture;
  treeList: { kind: string; x: number; y: number; z: number; s: number; r: number }[];
  hdri: THREE.DataTexture;
};

const BASE = '/hero/';

/** Load every hero asset in parallel, reporting 0..1 progress. */
export async function loadHeroAssets(renderer: THREE.WebGLRenderer, onProgress: (f: number) => void): Promise<HeroAssets> {
  const manager = new THREE.LoadingManager();
  let done = 0;
  const total = 16;
  const tick = <T,>(p: Promise<T>) =>
    p.then((v) => {
      done++;
      onProgress(done / total);
      return v;
    });

  const ktx2 = new KTX2Loader(manager).setTranscoderPath('/basis/').detectSupport(renderer);
  const gltf = new GLTFLoader(manager).setMeshoptDecoder(MeshoptDecoder).setKTX2Loader(ktx2);
  const tex = (name: string, color: boolean) =>
    tick(
      ktx2.loadAsync(`${BASE}tex/${name}.ktx2`).then((t) => {
        t.wrapS = t.wrapT = THREE.RepeatWrapping;
        t.colorSpace = color ? THREE.SRGBColorSpace : THREE.NoColorSpace;
        t.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
        return t;
      }),
    );

  const [timeline, excavator, env, pasture, pastureN, topsoil, clay, clayN, gravel, shale, shaleN, waterNormal, puff, trees, treeList, hdri] =
    await Promise.all([
      tick(fetch(`${BASE}timeline.json`).then((r) => r.json() as Promise<TimelineData>)),
      tick(gltf.loadAsync(`${BASE}excavator.glb`)),
      tick(gltf.loadAsync(`${BASE}env.glb`)),
      tex('pasture_albedo', true),
      tex('pasture_normal', false),
      tex('topsoil_albedo', true),
      tex('clay_albedo', true),
      tex('clay_normal', false),
      tex('gravel_albedo', true),
      tex('shale_albedo', true),
      tex('shale_normal', false),
      tex('water_normal', false),
      tex('puff', true),
      tex('trees', true),
      tick(fetch(`${BASE}trees.json`).then((r) => r.json())),
      // Poly Haven "Rooitou Park" (CC0), 512 px EXR via @pmndrs/assets
      tick(
        import('@pmndrs/assets/hdri/park.exr').then(
          (m: { default: string }) => new EXRLoader(manager).loadAsync(m.default) as Promise<THREE.DataTexture>,
        ),
      ),
    ]);
  ktx2.dispose();
  hdri.mapping = THREE.EquirectangularReflectionMapping;
  trees.wrapS = trees.wrapT = THREE.ClampToEdgeWrapping;
  return {
    timeline, excavator, env, waterNormal, puff, trees, treeList, hdri,
    ground: { pasture, pastureN, topsoil, clay, clayN, gravel, shale, shaleN },
  };
}
