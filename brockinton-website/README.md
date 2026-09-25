# Brockinton Land Management website

Marketing site for **Brockinton Land Management LLC** (Sherwood, AR; serving Central Arkansas).
It is a static Astro site with a scroll-driven 3D hero: a tracked excavator digs a farm pond in
an Arkansas pasture while the service cards appear one at a time.

- **Stack:** Astro 5 (static output), React Three Fiber, drei and postprocessing for the hero,
  GSAP ScrollTrigger and Lenis for scrolling. The rest of the page ships almost no JS.
- **Asset pipeline:** Blender 5 (the `bpy` module) builds, rigs and animates every 3D asset
  and renders the fallback frame sequence. `gltf-transform` with Meshopt compresses the models,
  and Basis Universal (KTX2) compresses the textures.

## Run, build, deploy

```bash
npm install
npm run dev        # http://localhost:4321
npm run build      # static site in dist/
npm run preview    # serve dist/ locally
```

Deploy `dist/` to any static host.

| Host | Build command | Output | Environment variables |
|---|---|---|---|
| Vercel | `npm run build` | `dist` | `PUBLIC_FORMSPREE_ID`, `SITE_URL` |
| Netlify | `npm run build` | `dist` | same |

`SITE_URL` is the live domain (for example `https://brockintonlandmanagement.com`). It is used
for canonical URLs, Open Graph tags and the sitemap. Also update the domain in `public/robots.txt`.

Built 3D assets (`public/hero/**`) are committed, so hosting never needs Blender.

## Estimate form (Formspree)

The form posts to [Formspree](https://formspree.io). To switch it on:

1. Create a free Formspree account with the email address Cody wants leads sent to, and verify it.
2. Create a new form. Its endpoint looks like `https://formspree.io/f/abcdwxyz`. The ID is `abcdwxyz`.
3. Set `PUBLIC_FORMSPREE_ID=abcdwxyz` in the host's environment variables and redeploy.
4. Optional: in Formspree, add the site's domain under *Restrict to domain* and turn on reCAPTCHA.
   The free plan covers 50 submissions a month.

Until the ID is set, the form validates input and then asks visitors to call instead.
The form includes a honeypot field (`_gotcha`) for basic spam protection.

## How the hero works

Everything that moves is defined once in `pipeline/common.py`: the terrain, pit and spoil
shapes, the excavator's pin geometry, the dig cycle, particles and the camera path. That single
source feeds both versions:

- **Real-time (WebGL):** `build_excavator.py` bakes the full rig into `excavator.glb`: boom,
  stick, bucket, swing, the bucket four-bar linkage, and each hydraulic barrel and rod aimed
  pin-to-pin every frame. Cylinder lengths are sized automatically from the pin distances, so
  a rod can never leave its barrel. The page scrubs that animation clip directly from scroll
  progress (`mixer.setTime`), so scrolling back is exact. The camera path and scene controls
  (pit depth, spoil height, water level, engine load) come from `public/hero/timeline.json`.
  The terrain height function is mirrored in GLSL (`src/hero/three/terrain.ts`).
- **Pre-rendered ("Apple method"):** `render_frames.py` renders the same timeline in Cycles.
  The frames are scrubbed on a `<canvas>` for WebGL-less or low-end devices.

Mode selection (`src/hero/boot.ts`):

| Condition | Mode |
|---|---|
| `prefers-reduced-motion` | Static: poster image, cards as a normal list |
| No WebGL2, Save-Data on, 2 GB of memory or less, `detect-gpu` tier 0, or a tier-1 phone | Frame sequence |
| Everything else | WebGL at tier `high`, `mid` or `low` |

For testing, append `?hero=webgl|frames|static` and `?q=high|mid|low` to the URL.

### Performance

- **Adaptive quality:** each tier sets resolution, shadow map size, grass count, terrain density,
  AO, depth of field, bloom, reflection resolution and tree density. drei's
  `PerformanceMonitor` drops resolution first, then drops a quality tier if frame rate stays
  below 45 fps.
- **Only renders when needed:** the render loop stops when the hero is off screen or the tab is
  hidden. Shadows redraw only when scroll progress changes.
- **Loading:** the WebGL chunk and assets load only after the poster (the LCP image) is
  painted. A branded loader shows progress. The Basis transcoder, GPU benchmark data and HDRI
  are self-hosted, with no third-party CDNs.

Measured hero payload, gzipped where it applies:

| Item | Size |
|---|---|
| WebGL JS chunk (three, R3F, drei, postprocessing) | 441 KB |
| Excavator GLB (Meshopt) | 491 KB |
| Environment GLB (fence, bales, ridges) | 94 KB |
| Ground textures, 5 × KTX2 ETC1S at 1024 | ~960 KB |
| Normal maps, 4 × KTX2 at 512 | ~290 KB |
| Tree impostor atlas and dust sprite | ~106 KB |
| HDRI (Poly Haven Rooitou Park, 512 px EXR) | 154 KB |
| Timeline JSON | ~20 KB |
| **Total, with transcoder and poster** | **about 3 MB** |

Lighthouse (mobile, production build): Performance 95, Accessibility 96, Best Practices 96, SEO 100.

## Rebuilding the 3D assets

Requirements: Python 3.11 and `pip install bpy numpy pillow` (Blender 5.0 as a Python module).
Blender's own `blender -b -P script.py` also works.

```bash
cd pipeline
python textures.py              # tileable PBR ground textures, leaves, straw, water normals, dust sprite
python build_excavator.py       # model + rig + bake the dig cycle -> build/excavator_raw.glb
python build_scene.py           # environment (terrain, grass, trees, ridges, fence, bales, water) -> build/scene.blend, env_raw.glb
python render_tree_cards.py     # tree impostor atlas for the real-time treeline
python export_timeline.py       # camera path + scene controls -> public/hero/timeline.json
cd .. && npm run assets         # Meshopt GLBs + KTX2 textures -> public/hero/

# Pre-rendered sequence, slow on CPU: about 2-3 minutes per frame on 4 cores
cd pipeline
python render_frames.py --orient landscape --frames 160 --res 1280 --samples 14
python render_frames.py --orient portrait  --frames 120 --res 1024 --samples 14
cd .. && npm run frames         # AVIF + WebP frames, posters -> public/hero/frames/
```

`render_frames.py --only 0.1,0.5` renders single look-dev frames. `build_scene.py --fast` builds
a light scene for quick iteration.

### Swapping in Poly Haven or Sketchfab assets

This build environment could not reach Poly Haven or Sketchfab: their hosts were blocked by the
network policy. So every model and texture was built in Blender for this project. To upgrade:

- **Ground textures:** download 1K Poly Haven sets (for example a grass/forest-floor set, a red
  laterite or clay soil, gravel, rock) and save them as `pipeline/build/tex/<name>_albedo.png`
  and `<name>_normal.png` using the names `pasture`, `topsoil`, `clay`, `gravel`, `shale`.
  Then run `npm run assets`. Both the real-time and Blender versions pick them up.
- **HDRI:** replace the `park.exr` import in `src/hero/three/assets.ts` with a 1K late-afternoon
  Poly Haven HDRI.
- **Excavator:** a CC-BY or CC0 Sketchfab model needs its boom, stick, bucket and cylinders as
  separate nodes. Import it in `build_excavator.py` in place of the procedural parts, parent the
  parts to the existing `Boom`, `Stick` and `Bucket` pivots, and keep the pin constants in
  `common.py` aligned with the model's pins. Add its credit line below.

## Accessibility and SEO

- Semantic landmarks and heading order, a skip link, visible focus styles, and tap-to-call
  links everywhere.
- The hero cards are real list items in the HTML. A screen-reader-only text version of the
  scroll story sits alongside the canvas, which is `aria-hidden`.
- Reduced-motion users get a static hero and no smooth scrolling. Without JavaScript, the hero
  becomes a normal section.
- Title, meta description, canonical URL, Open Graph and Twitter image (`public/og-image.jpg`),
  sitemap, robots.txt, and `HomeAndConstructionBusiness` (LocalBusiness) JSON-LD with the phone
  number, Central Arkansas service area and services.

## Credits and licenses

- **HDRI:** "Rooitou Park" by Greg Zaal, [Poly Haven](https://polyhaven.com/a/rooitou_park), CC0.
  The 512 px build comes from [@pmndrs/assets](https://github.com/pmndrs/assets).
- **Excavator, terrain, textures, grass, trees, fence, hay bales, water, frame renders:**
  created for this project in Blender. No third-party models, scans or photos.
- **Fonts:** Barlow and Barlow Condensed by Jeremy Tribby, SIL Open Font License 1.1.
- **Libraries:** three.js, React Three Fiber, drei, postprocessing, GSAP (standard no-charge
  license), Lenis, detect-gpu (MIT), Astro (MIT).

## To confirm with Cody before launch

- [ ] Business hours (not shown yet; `business.hours` in `src/data/site.ts`)
- [ ] A public email address (`business.email`), and the address Formspree should deliver to
- [ ] Whether storm shelters should appear as a service. Today they appear only in the
      Cozy Caverns partner block and as a form option.
- [ ] Real job photos or drone footage we could use (for example a gallery or the poster image)
- [ ] Short descriptions for *Brush Hogging and Vegetation Control* and *Demolition* (his current
      site has titles only, so the site shows titles only)
