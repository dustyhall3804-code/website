// Encode the Blender frame sequence (pipeline/build/frames/<orient>/f_XXXX.png)
// to AVIF + WebP for the scroll-scrubbed fallback, plus poster and OG images.
//   npm run frames
import { readdir, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import sharp from 'sharp';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const src = path.join(root, 'pipeline', 'build', 'frames');
const out = path.join(root, 'public', 'hero');

for (const orient of ['landscape', 'portrait']) {
  const dir = path.join(src, orient);
  let files = [];
  try { files = (await readdir(dir)).filter((f) => /^f_\d{4}\.png$/.test(f)).sort(); } catch { continue; }
  const dst = path.join(out, 'frames', orient);
  await mkdir(dst, { recursive: true });
  let bytes = 0;
  for (const f of files) {
    const img = sharp(path.join(dir, f));
    const base = path.join(dst, f.replace('.png', ''));
    const a = await img.clone().avif({ quality: 52, effort: 5, chromaSubsampling: '4:2:0' }).toFile(base + '.avif');
    const w = await img.clone().webp({ quality: 70, effort: 5 }).toFile(base + '.webp');
    bytes += a.size;
    if (f === 'f_0000.png') {
      // poster = first frame of the sequence (the LCP image before any JS runs)
      await img.clone().avif({ quality: 55, effort: 6 }).toFile(path.join(out, `poster-${orient}.avif`));
      await img.clone().webp({ quality: 74 }).toFile(path.join(out, `poster-${orient}.webp`));
    }
    void w;
  }
  console.log(`${orient}: ${files.length} frames, AVIF total ${(bytes / 1048576).toFixed(1)} MB`);
}
