// Compress the Blender exports for the web.
//   GLB  -> weld, dedup, quantize, Meshopt (EXT_meshopt_compression)
//   PNG  -> KTX2 / Basis Universal (ETC1S for colour, UASTC for normal maps)
// Run after the pipeline: `npm run assets`
import { readFile, writeFile, mkdir, stat, copyFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import sharp from 'sharp';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { dedup, weld, quantize, meshopt, prune, resample } from '@gltf-transform/functions';
import { MeshoptEncoder, MeshoptDecoder } from 'meshoptimizer';
import { encodeToKTX2 } from 'ktx2-encoder';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const build = path.join(root, 'pipeline', 'build');
const out = path.join(root, 'public', 'hero');
await mkdir(path.join(out, 'tex'), { recursive: true });

const kb = async (f) => ((await stat(f)).size / 1024).toFixed(0) + ' KB';

// ------------------------------------------------------------------ models
await MeshoptEncoder.ready;
const io = new NodeIO()
  .registerExtensions(ALL_EXTENSIONS)
  .registerDependencies({ 'meshopt.encoder': MeshoptEncoder, 'meshopt.decoder': MeshoptDecoder });

for (const [src, dst] of [['excavator_raw.glb', 'excavator.glb'], ['env_raw.glb', 'env.glb']]) {
  const doc = await io.read(path.join(build, src));
  // environment props get their materials in code; drop any embedded images
  if (dst === 'env.glb') for (const t of doc.getRoot().listTextures()) t.dispose();
  await doc.transform(
    dedup(),
    weld(),
    resample(),                                   // drop redundant linear keys
    prune(),
    quantize({ quantizePosition: 14, quantizeNormal: 10 }),
    meshopt({ encoder: MeshoptEncoder, level: 'high' }),
  );
  const dstPath = path.join(out, dst);
  await io.write(dstPath, doc);
  console.log(`${dst}: ${await kb(path.join(build, src))} -> ${await kb(dstPath)}`);
}

// ---------------------------------------------------------------- textures
// Only what the real-time hero samples. Normal maps use ETC1S at 512 px: at
// the grazing angles of a landscape they hold up, and UASTC would cost ~1.3 MB each.
const TEX = [
  ...['pasture', 'topsoil', 'clay', 'gravel', 'shale'].map((n) => [`${n}_albedo`, 1024, 'color']),
  ...['pasture', 'clay', 'shale'].map((n) => [`${n}_normal`, 512, 'normal']),
  ['water_normal', 512, 'normal'],
  ['puff', 256, 'color'],
  ['trees', 1024, 'color'],
];

for (const [name, size, kind] of TEX) {
  const src = path.join(build, 'tex', `${name}.png`);
  try { await stat(src); } catch { console.warn('skip (missing)', name); continue; }
  const png = await sharp(src).resize(size, size, { fit: 'fill' })
    .png().toBuffer();
  const ktx = await encodeToKTX2(new Uint8Array(png), {
    isUASTC: false,
    isNormalMap: kind === 'normal',
    isPerceptual: kind === 'color',
    isSetKTX2SRGBTransferFunc: kind === 'color',
    generateMipmap: true,
    qualityLevel: kind === 'color' ? 170 : 200,
    compressionLevel: 2,
    needSupercompression: true,
    imageDecoder: async (buf) => {
      const { data, info } = await sharp(buf).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
      return { data: new Uint8Array(data), width: info.width, height: info.height };
    },
  });
  const dst = path.join(out, 'tex', `${name}.ktx2`);
  await writeFile(dst, ktx);
  console.log(`${name}.ktx2: ${await kb(dst)}`);
}

// keep a copy of trees.json for instancing
try {
  await copyFile(path.join(build, 'trees.json'), path.join(out, 'trees.json'));
} catch { /* optional */ }
