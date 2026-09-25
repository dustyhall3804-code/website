// Shared, mutable hero state. Both the boot script and the lazily loaded
// WebGL chunk import this module, so they see the same object.
export type Quality = 'high' | 'mid' | 'low';

export const heroState = {
  /** smoothed scroll progress through the pinned hero, 0..1 */
  progress: 0,
  /** hero is on screen (render only while true) */
  visible: true,
  /** portrait layout (card at the bottom) */
  portrait: false,
  quality: 'mid' as Quality,
  reducedMotion: false,
};

type Listener = () => void;
const listeners = new Set<Listener>();
export const onProgress = (fn: Listener) => {
  listeners.add(fn);
  return () => listeners.delete(fn);
};
export const emitProgress = () => listeners.forEach((fn) => fn());
