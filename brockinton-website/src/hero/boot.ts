import { heroState, emitProgress, type Quality } from './state';

type Mode = 'webgl' | 'frames' | 'static';

/** Boot the scroll hero: pick a render mode, wire scroll progress, drive the cards. */
export async function bootHero() {
  const hero = document.querySelector<HTMLElement>('[data-hero]');
  if (!hero) return;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  heroState.reducedMotion = reduced;
  const params = new URLSearchParams(location.search);
  const forced = params.get('hero') as Mode | null;
  const forcedQ = params.get('q') as Quality | null;

  if ((reduced && forced !== 'webgl' && forced !== 'frames') || forced === 'static') {
    hero.dataset.mode = 'static';
    return;
  }

  const portraitMq = matchMedia('(max-aspect-ratio: 1/1)');
  const setPortrait = () => (heroState.portrait = portraitMq.matches);
  setPortrait();
  portraitMq.addEventListener('change', setPortrait);

  wireCards(hero);
  await wireScroll(hero);
  watchVisibility(hero);

  const mode = forced ?? (await chooseMode());
  if (forcedQ && ['high', 'mid', 'low'].includes(forcedQ)) heroState.quality = forcedQ;
  if (mode === 'static') {
    hero.dataset.mode = 'static';
    return;
  }
  if (mode === 'webgl') {
    try {
      await startWebGL(hero);
      return;
    } catch (err) {
      console.warn('[hero] WebGL failed, falling back to frames', err);
    }
  }
  startFrames(hero);
}

// ------------------------------------------------------------------ mode
async function chooseMode(): Promise<Mode> {
  const canvas = document.createElement('canvas');
  const gl = canvas.getContext('webgl2');
  if (!gl) return 'frames';
  const nav = navigator as Navigator & { deviceMemory?: number; connection?: { saveData?: boolean } };
  if (nav.connection?.saveData) return 'frames';
  if (nav.deviceMemory && nav.deviceMemory <= 2) return 'frames';
  try {
    const { getGPUTier } = await import('detect-gpu');
    const t = await getGPUTier({ benchmarksURL: '/detect-gpu', glContext: gl });
    // tier 0: blocklisted / unknown-slow; tier 1 on phones struggles with the full scene
    if (t.tier === 0 || (t.isMobile && t.tier === 1)) return 'frames';
    heroState.quality = t.tier >= 3 && !t.isMobile ? 'high' : t.tier >= 2 ? 'mid' : 'low';
  } catch {
    heroState.quality = 'mid';
  }
  return 'webgl';
}

// ------------------------------------------------------------- scrolling
async function wireScroll(hero: HTMLElement) {
  const [{ gsap }, { ScrollTrigger }, { default: Lenis }] = await Promise.all([
    import('gsap'),
    import('gsap/ScrollTrigger'),
    import('lenis'),
  ]);
  gsap.registerPlugin(ScrollTrigger);

  const lenis = new Lenis({ lerp: 0.1, smoothWheel: true });
  lenis.on('scroll', ScrollTrigger.update);
  gsap.ticker.add((t) => lenis.raf(t * 1000));
  gsap.ticker.lagSmoothing(0);
  // in-page anchors go through Lenis so they glide instead of jumping
  document.addEventListener('click', (e) => {
    const a = (e.target as HTMLElement).closest<HTMLAnchorElement>('a[href^="#"]');
    if (!a || a.getAttribute('href') === '#') return;
    const target = document.querySelector(a.getAttribute('href')!);
    if (!target) return;
    e.preventDefault();
    lenis.scrollTo(target as HTMLElement, { offset: a.getAttribute('href') === '#top' ? 0 : -72 });
    history.replaceState(null, '', a.getAttribute('href'));
    (target as HTMLElement).focus?.({ preventScroll: true });
  });

  const proxy = { p: 0 };
  gsap.to(proxy, {
    p: 1,
    ease: 'none',
    scrollTrigger: { trigger: hero, start: 'top top', end: 'bottom bottom', scrub: 0.6 },
    onUpdate: () => {
      heroState.progress = proxy.p;
      emitProgress();
    },
  });
}

function watchVisibility(hero: HTMLElement) {
  new IntersectionObserver(([e]) => (heroState.visible = e.isIntersecting), { rootMargin: '64px' }).observe(hero);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) heroState.visible = false;
  });
}

// ------------------------------------------------------------------- cards
function wireCards(hero: HTMLElement) {
  const cards = [...hero.querySelectorAll<HTMLElement>('[data-card]')].map((el) => ({
    el,
    start: parseFloat(el.dataset.start!),
    end: parseFloat(el.dataset.end!),
  }));
  const intro = hero.querySelector<HTMLElement>('[data-intro]')!;
  const cue = hero.querySelector<HTMLElement>('[data-cue]')!;
  let active: HTMLElement | null = null;
  const update = () => {
    const p = heroState.progress;
    const next = cards.find((c) => p >= c.start && p < c.end)?.el ?? null;
    if (next !== active) {
      active?.classList.remove('is-active');
      next?.classList.add('is-active');
      active = next;
    }
    intro.classList.toggle('is-hidden', p > 0.03);
    cue.classList.toggle('is-hidden', p > 0.01);
  };
  import('./state').then(({ onProgress }) => onProgress(update));
  update();
}

// ------------------------------------------------------------------- webgl
async function startWebGL(hero: HTMLElement) {
  const mount = hero.querySelector<HTMLElement>('[data-gl]')!;
  const bar = hero.querySelector<HTMLElement>('[data-loader-bar]')!;
  hero.dataset.loading = '';
  const { mountHero } = await import('./three/mount');
  await new Promise<void>((resolve, reject) => {
    mountHero(mount, {
      onLoadProgress: (f) => (bar.style.width = `${Math.round(f * 100)}%`),
      onReady: () => {
        delete hero.dataset.loading;
        hero.dataset.mode = 'webgl';
        resolve();
      },
      onError: reject,
    });
  });
}

// ------------------------------------------------------------------ frames
// frames per orientation (pipeline/render_frames.py --frames)
const FRAME_COUNTS: Record<string, number> = { landscape: 160, portrait: 120 };

async function supportsAvif() {
  const img = new Image();
  img.src =
    'data:image/avif;base64,AAAAIGZ0eXBhdmlmAAAAAGF2aWZtaWYxbWlhZk1BMUIAAADybWV0YQAAAAAAAAAoaGRscgAAAAAAAAAAcGljdAAAAAAAAAAAAAAAAGxpYmF2aWYAAAAADnBpdG0AAAAAAAEAAAAeaWxvYwAAAABEAAABAAEAAAABAAABGgAAAB0AAAAoaWluZgAAAAAAAQAAABppbmZlAgAAAAABAABhdjAxQ29sb3IAAAAAamlwcnAAAABLaXBjbwAAABRpc3BlAAAAAAAAAAIAAAACAAAAEHBpeGkAAAAAAwgICAAAAAxhdjFDgQ0MAAAAABNjb2xybmNseAACAAIAAYAAAAAXaXBtYQAAAAAAAAABAAEEAQKDBAAAACVtZGF0EgAKCBgANogQEAwgMg8f8D///8WfhwB8+ErK42A=';
  try {
    await img.decode();
    return img.width > 0;
  } catch {
    return false;
  }
}

async function startFrames(hero: HTMLElement) {
  const canvas = hero.querySelector<HTMLCanvasElement>('[data-frames]')!;
  const ctx = canvas.getContext('2d', { alpha: false })!;
  const ext = (await supportsAvif()) ? 'avif' : 'webp';
  const sets: Record<string, (HTMLImageElement | null)[]> = {};
  const loadSet = (orient: string) => {
    if (sets[orient]) return sets[orient];
    const FRAME_COUNT = FRAME_COUNTS[orient];
    const arr: (HTMLImageElement | null)[] = new Array(FRAME_COUNT).fill(null);
    sets[orient] = arr;
    // coarse-to-fine: every 16th frame first; the rest once the visitor scrolls
    // or the page goes idle, so the first paint is not competing for bandwidth
    const order: number[] = [];
    for (const stride of [16, 8, 4, 2, 1])
      for (let i = 0; i < FRAME_COUNT; i += stride) if (!order.includes(i)) order.push(i);
    const coarse = Math.ceil(FRAME_COUNT / 16);
    let unlocked = false;
    const unlock = () => {
      if (unlocked) return;
      unlocked = true;
      next();
    };
    let inflight = 0;
    let started = 0;
    const next = () => {
      while (inflight < 4 && order.length && (unlocked || started < coarse)) {
        const i = order.shift()!;
        started++;
        const img = new Image();
        img.decoding = 'async';
        img.src = `/hero/frames/${orient}/f_${String(i).padStart(4, '0')}.${ext}`;
        inflight++;
        img.onload = img.onerror = () => {
          inflight--;
          if (img.naturalWidth) arr[i] = img;
          draw();
          next();
        };
      }
    };
    addEventListener('scroll', unlock, { once: true, passive: true });
    ('requestIdleCallback' in window ? requestIdleCallback : setTimeout)(() => setTimeout(unlock, 2500));
    next();
    return arr;
  };

  let last = -1;
  const draw = () => {
    const orient = heroState.portrait ? 'portrait' : 'landscape';
    const arr = loadSet(orient);
    const FRAME_COUNT = arr.length;
    const want = Math.round(heroState.progress * (FRAME_COUNT - 1));
    // nearest loaded frame
    let idx = -1;
    for (let d = 0; d < FRAME_COUNT; d++) {
      if (arr[want - d]) { idx = want - d; break; }
      if (arr[want + d]) { idx = want + d; break; }
    }
    if (idx < 0) return;
    const dpr = Math.min(devicePixelRatio, 2);
    const w = Math.round(canvas.clientWidth * dpr), h = Math.round(canvas.clientHeight * dpr);
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; last = -1; }
    const key = idx + (heroState.portrait ? 10000 : 0);
    if (key === last) return;
    last = key;
    const img = arr[idx]!;
    const s = Math.max(w / img.naturalWidth, h / img.naturalHeight);
    const dw = img.naturalWidth * s, dh = img.naturalHeight * s;
    ctx.drawImage(img, (w - dw) / 2, (h - dh) / 2, dw, dh);
    hero.dataset.mode = 'frames';
  };
  const { onProgress } = await import('./state');
  onProgress(() => heroState.visible && draw());
  addEventListener('resize', () => { last = -1; draw(); });
  draw();
}
