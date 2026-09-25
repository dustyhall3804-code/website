import type { Quality } from '../state';

export type QualitySettings = {
  dpr: [number, number];
  shadowMap: number;
  grass: number;          // grass clumps (each ~7 blades)
  terrainSegments: number;
  ao: boolean;
  dof: boolean;
  bloom: boolean;
  reflectorRes: number;
  treeCount: number;
};

export const QUALITY: Record<Quality, QualitySettings> = {
  high: { dpr: [1, 1.75], shadowMap: 2048, grass: 26000, terrainSegments: 420, ao: true, dof: true, bloom: true, reflectorRes: 1024, treeCount: 1 },
  mid: { dpr: [0.85, 1.25], shadowMap: 1024, grass: 14000, terrainSegments: 320, ao: true, dof: false, bloom: true, reflectorRes: 512, treeCount: 0.8 },
  low: { dpr: [0.6, 1], shadowMap: 1024, grass: 6000, terrainSegments: 220, ao: false, dof: false, bloom: false, reflectorRes: 256, treeCount: 0.6 },
};

export const downgrade = (q: Quality): Quality => (q === 'high' ? 'mid' : 'low');
