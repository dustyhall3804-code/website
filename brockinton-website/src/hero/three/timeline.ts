import { Vector3 } from 'three';

export type HeroEvent = { kind: 'bite' | 'dump'; p: number; pos: [number, number, number]; ground: number };
export type TimelineData = {
  fields: string[];
  samples: number[][];
  events: HeroEvent[];
  secondsPerUnit: number;
};

export type Frame = {
  cam: Vector3;
  target: Vector3;
  lens: number;
  pit: number;
  spoil: number;
  waterLevel: number;
  water: number;
  load: number;
  exhaust: Vector3;
};

/** Linear sampling of the baked timeline (see pipeline/export_timeline.py). */
export class Timeline {
  readonly events: HeroEvent[];
  readonly secondsPerUnit: number;
  private s: number[][];
  private out: Frame = {
    cam: new Vector3(), target: new Vector3(), lens: 30, pit: 0, spoil: 0,
    waterLevel: -3, water: 0, load: 0, exhaust: new Vector3(),
  };
  private row: number[];

  constructor(d: TimelineData) {
    this.s = d.samples;
    this.events = d.events;
    this.secondsPerUnit = d.secondsPerUnit;
    this.row = new Array(d.samples[0].length).fill(0);
  }

  sample(p: number, portrait: boolean): Frame {
    const n = this.s.length - 1;
    const f = Math.min(Math.max(p, 0), 1) * n;
    const i = Math.min(Math.floor(f), n - 1);
    const t = f - i;
    const a = this.s[i], b = this.s[i + 1];
    const r = this.row;
    for (let k = 0; k < r.length; k++) r[k] = a[k] + (b[k] - a[k]) * t;
    const o = this.out;
    const c = portrait ? 7 : 0;
    o.cam.set(r[c], r[c + 1], r[c + 2]);
    o.target.set(r[c + 3], r[c + 4], r[c + 5]);
    o.lens = r[c + 6];
    o.pit = r[14]; o.spoil = r[15]; o.waterLevel = r[16]; o.water = r[17]; o.load = r[18];
    o.exhaust.set(r[19], r[20], r[21]);
    return o;
  }
}

/** Vertical field of view (degrees) for a lens in mm at this aspect (matches common.fov_for_aspect). */
export function fovForAspect(lensMm: number, aspect: number) {
  const hfovLand = 2 * Math.atan(18 / lensMm);
  const vfovLand = 2 * Math.atan(Math.tan(hfovLand / 2) / (16 / 9));
  const hfovMin = hfovLand * 0.74;
  return (Math.max(vfovLand, 2 * Math.atan(Math.tan(hfovMin / 2) / aspect)) * 180) / Math.PI;
}

/** Projection shift (NDC) keeping the machine clear of the service card. */
export function lensShift(aspect: number): [number, number] {
  return aspect >= 1 ? [-0.16, 0.02] : [0, -0.26];
}
