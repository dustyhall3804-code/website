"""Vectorised terrain functions (numpy) matching common.py and terrain.glsl."""
import numpy as np
import common as C


def smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def base_height(x, y):
    h = 0.35 * np.sin(x * 0.045 + 1.3) * np.cos(y * 0.038 - 0.4)
    h += 0.18 * np.sin(x * 0.11 - y * 0.07 + 2.1)
    h += 0.06 * np.sin(x * 0.31 + y * 0.27)
    d = np.hypot(x - 0.5, y - 3.5)
    return h * smooth((d - 9.0) / 14.0)


def pit_mask(x, y):
    dx = np.abs(x - C.PIT_CENTER[0]) - (C.PIT_HALF[0] - C.PIT_WALL)
    dy = np.abs(y - C.PIT_CENTER[1]) - (C.PIT_HALF[1] - C.PIT_WALL)
    d = np.hypot(np.maximum(dx, 0), np.maximum(dy, 0)) + np.minimum(np.maximum(dx, dy), 0)
    d = d + 0.18 * np.sin(x * 1.7 + y * 0.9) + 0.1 * np.sin(y * 2.3 - x)
    return smooth(1.0 - d / C.PIT_WALL)


def spoil_mask(x, y):
    cx, cy = C.spoil_center()
    a = np.radians(C.SPOIL_YAW)
    lx = (x - cx) * np.cos(a) + (y - cy) * np.sin(a)
    ly = -(x - cx) * np.sin(a) + (y - cy) * np.cos(a)
    r = np.hypot(lx / C.SPOIL_RADIUS[1], ly / C.SPOIL_RADIUS[0])
    lumps = 0.06 * np.sin(x * 3.1 + y * 1.3) + 0.05 * np.sin(y * 4.7 - x * 2.2)
    m = np.clip(1.0 - r * r, 0, 1)
    return m ** 1.15 + lumps * m


def height(x, y, pit, spoil):
    return base_height(x, y) - C.PIT_DEPTH * pit * pit_mask(x, y) + C.SPOIL_HEIGHT * spoil * spoil_mask(x, y)


def work_mask(x, y):
    """Stripped work area: pit footprint, spoil pile, machine pad (static)."""
    dx = np.abs(x - C.PIT_CENTER[0]) - (C.PIT_HALF[0] + 1.2)
    dy = np.abs(y - C.PIT_CENTER[1]) - (C.PIT_HALF[1] + 1.2)
    d_pit = np.hypot(np.maximum(dx, 0), np.maximum(dy, 0)) + np.minimum(np.maximum(dx, dy), 0)
    cx, cy = C.spoil_center()
    d_sp = np.hypot((x - cx) / 1.25, (y - cy) / 1.1) - C.SPOIL_RADIUS[0]
    # machine pad and the track path it walked in on (from the south-west)
    px = np.abs(x - 0.0) - 2.4
    py = np.abs(y - 0.2) - 3.4
    d_pad = np.hypot(np.maximum(px, 0), np.maximum(py, 0)) + np.minimum(np.maximum(px, py), 0)
    d = np.minimum(np.minimum(d_pit, d_sp), d_pad)
    d = d + 0.55 * np.sin(x * 0.7 + 1.7 * np.cos(y * 0.45)) + 0.35 * np.sin(y * 1.9 + x * 0.4) + 0.2 * np.sin(x * 3.1 - y * 2.3)
    return smooth(1.0 - d / 1.6)
