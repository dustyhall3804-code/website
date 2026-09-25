import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { EffectComposer, N8AO, Bloom, DepthOfField, Noise, ToneMapping, Vignette, SMAA } from '@react-three/postprocessing';
import { BlendFunction, ToneMappingMode, type DepthOfFieldEffect } from 'postprocessing';
import type { QualitySettings } from './quality';

/** Camera-like finishing: ACES, subtle AO, light bloom, DOF on close shots, faint grain. */
export function Effects({ q, focus }: { q: QualitySettings; focus: { current: number } }) {
  const dof = useRef<DepthOfFieldEffect>(null);
  useFrame(() => {
    const d = dof.current;
    if (!d) return;
    const dist = focus.current;
    d.cocMaterial.worldFocusDistance = dist;
    d.cocMaterial.worldFocusRange = Math.max(3, dist * 0.6);
    // bokeh only in the close shots
    d.bokehScale = dist < 14 ? 2.2 * (1 - dist / 14) + 0.4 : 0;
  });
  return (
    <EffectComposer multisampling={0} enableNormalPass={false}>
      {q.ao ? <N8AO halfRes aoRadius={1.2} intensity={1.6} distanceFalloff={0.6} quality="performance" /> : <></>}
      {q.dof ? <DepthOfField ref={dof} worldFocusDistance={10} worldFocusRange={6} bokehScale={0} /> : <></>}
      {q.bloom ? <Bloom mipmapBlur luminanceThreshold={0.92} luminanceSmoothing={0.1} intensity={0.35} /> : <></>}
      <ToneMapping mode={ToneMappingMode.ACES_FILMIC} />
      <SMAA />
      <Noise premultiply blendFunction={BlendFunction.SOFT_LIGHT} opacity={0.22} />
      <Vignette offset={0.3} darkness={0.35} />
    </EffectComposer>
  );
}
