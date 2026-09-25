// Encode the Blender frame sequence (pipeline/build/frames/<orient>/f_XXXX.png)
// to AVIF + WebP for the scroll-scrubbed fallback, plus poster and OG images.
//   npm run frames              every rendered frame
//   npm run frames -- --step 2  every other frame (half-rate preview)
// Output frames are numbered 0..N-1 and counts go to frames/manifest.json,
// which the hero reads, so switching between 80 and 160 needs no code change.
import { readdir, mkdir, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import sharp from 'sharp';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const src = path.join(root, 'pipeline', 'build', 'frames');
const out = path.join(root, 'public', 'hero');
const stepArg = process.argv.indexOf('--step');
const step = stepArg > 0 ? parseInt(process.argv[stepArg + 1], 10) : 1;
const manifest = {};

for (const orient of ['landscape', 'portrait']) {
  const dir = path.join(src, orient);
  let files = [];
  try { files = (await readdir(dir)).filter((f) => /^f_\d{4}\.png$/.test(f)).sort(); } catch { continue; }
  files = files.filter((f) => parseInt(f.slice(2, 6), 10) % step === 0);
  // require a gap-free sequence so scrubbing is even
  files.forEach((f, i) => {
    if (parseInt(f.slice(2, 6), 10) !== i * step) throw new Error(`${orient}: missing frame before ${f}`);
  });
  const dst = path.join(out, 'frames', orient);
  await rm(dst, { recursive: true, force: true });
  await mkdir(dst, { recursive: true });
  let bytes = 0;
  for (const [n, f] of files.entries()) {
    const img = sharp(path.join(dir, f));
    const base = path.join(dst, `f_${String(n).padStart(4, '0')}`);
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
  manifest[orient] = files.length;
  console.log(`${orient}: ${files.length} frames, AVIF total ${(bytes / 1048576).toFixed(1)} MB`);
}
await mkdir(path.join(out, 'frames'), { recursive: true });
await writeFile(path.join(out, 'frames', 'manifest.json'), JSON.stringify(manifest));
