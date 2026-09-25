import { useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { fovForAspect, lensShift, type Frame, type Timeline } from './timeline';
import { heroState } from '../state';

/** Drives the camera from the baked path; runs first each frame and publishes the frame. */
export function CameraRig({ timeline, frame, focus }: { timeline: Timeline; frame: { current: Frame }; focus: { current: number } }) {
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const size = useThree((s) => s.size);
  const gl = useThree((s) => s.gl);
  const lastP = useRef(-1);

  useFrame(() => {
    const aspect = size.width / size.height;
    const portrait = aspect < 1;
    const f = timeline.sample(heroState.progress, portrait);
    frame.current = f;
    camera.position.copy(f.cam);
    camera.lookAt(f.target);
    camera.fov = fovForAspect(f.lens, aspect);
    camera.near = 0.1;
    camera.far = 5000;
    camera.updateProjectionMatrix();
    // lens shift so the machine sits clear of the service card
    const [sx, sy] = lensShift(aspect);
    camera.projectionMatrix.elements[8] += sx;
    camera.projectionMatrix.elements[9] += sy;
    camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
    focus.current = f.cam.distanceTo(f.target);
    // shadows are static unless something moved
    if (Math.abs(heroState.progress - lastP.current) > 1e-5) {
      gl.shadowMap.needsUpdate = true;
      lastP.current = heroState.progress;
    }
  }, -10);
  return null;
}
