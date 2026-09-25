import { createRoot } from 'react-dom/client';
import { HeroCanvas, type HeroCallbacks } from './HeroCanvas';

export function mountHero(el: HTMLElement, cb: HeroCallbacks) {
  const root = createRoot(el);
  root.render(<HeroCanvas {...cb} />);
  return () => root.unmount();
}
