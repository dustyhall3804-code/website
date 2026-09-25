"""Shared scene definition for the Brockinton hero.

Everything that moves in the hero is defined here once: terrain and pit shape,
excavator arm geometry, the dig-cycle timeline and the camera path. The Blender
scripts bake it into the excavator GLB (node animation) and `timeline.json`
(camera + scene controls), and the pre-rendered sequence uses the same
functions, so the real-time and rendered versions match frame for frame.

Coordinates are Blender's: metres, +Z up, the machine faces +Y. glTF/three.js
converts to (x, z, -y).
"""
import math

# ---------------------------------------------------------------- scene layout
GROUND_Z = 0.0
SWING_Z = 1.05            # top of the carbody / swing bearing above ground
ARM_X = 0.28              # arm plane sits right of centre, cab on the left

PIT_CENTER = (0.35, 7.25)  # x, y
PIT_HALF = (4.9, 3.25)    # rim half-extents (x, y)
PIT_WALL = 1.75           # horizontal run of the wall slope
PIT_DEPTH = 3.0           # final depth in metres

SPOIL_YAW = -100.0        # cab swing angle (deg) when dumping, right side
SPOIL_DIST = 7.6
SPOIL_RADIUS = (3.4, 2.4)
SPOIL_HEIGHT = 2.3

WATER_FINAL = -0.45       # final water surface, relative to original grade

# Soil strata, depth below original grade (m): topsoil, Arkansas red clay,
# sand and gravel, shale.
STRATA = [0.32, 1.55, 2.35]

N_CYCLES = 6
T_DIG0, T_DIG1 = 0.075, 0.795   # progress range of the dig cycles
T_WATER0, T_WATER1 = 0.80, 0.96


def spoil_center():
    a = math.radians(SPOIL_YAW)
    x, y = ARM_X, SPOIL_DIST
    return (x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a))


# ------------------------------------------------------------------- helpers
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def smoother(x):
    x = clamp(x)
    return x * x * x * (x * (x * 6 - 15) + 10)


def lerp(a, b, t):
    return a + (b - a) * t


def base_height(x, y):
    """Gentle pasture undulation. Mirrored in the terrain shader (terrain.ts)."""
    h = 0.35 * math.sin(x * 0.045 + 1.3) * math.cos(y * 0.038 - 0.4)
    h += 0.18 * math.sin(x * 0.11 - y * 0.07 + 2.1)
    h += 0.06 * math.sin(x * 0.31 + y * 0.27)
    # flatten the work area so the machine sits level
    d = math.hypot(x - 0.5, y - 3.5)
    return h * smooth((d - 9.0) / 14.0)


def pit_mask(x, y):
    """0 outside the rim, 1 on the flat floor (rounded-rectangle footprint)."""
    dx = abs(x - PIT_CENTER[0]) - (PIT_HALF[0] - PIT_WALL)
    dy = abs(y - PIT_CENTER[1]) - (PIT_HALF[1] - PIT_WALL)
    ox, oy = max(dx, 0.0), max(dy, 0.0)
    d = math.hypot(ox, oy) + min(max(dx, dy), 0.0)
    # slight irregularity so the rim is not a perfect CAD shape
    d += 0.18 * math.sin(x * 1.7 + y * 0.9) + 0.1 * math.sin(y * 2.3 - x)
    return smooth(1.0 - d / PIT_WALL)


def spoil_mask(x, y):
    cx, cy = spoil_center()
    a = math.radians(SPOIL_YAW)
    lx = (x - cx) * math.cos(a) + (y - cy) * math.sin(a)
    ly = -(x - cx) * math.sin(a) + (y - cy) * math.cos(a)
    r = math.hypot(lx / SPOIL_RADIUS[1], ly / SPOIL_RADIUS[0])
    lumps = 0.06 * math.sin(x * 3.1 + y * 1.3) + 0.05 * math.sin(y * 4.7 - x * 2.2)
    m = clamp(1.0 - r * r)
    return m ** 1.15 + lumps * m


def height(x, y, pit, spoil):
    """Terrain height at (x, y) for pit and spoil progress in 0..1."""
    return base_height(x, y) - PIT_DEPTH * pit * pit_mask(x, y) + SPOIL_HEIGHT * spoil * spoil_mask(x, y)


# ----------------------------------------------------------- excavator arm
# 2D arm plane in the upper structure's frame: (y forward, z up), origin at
# the swing centre on top of the carbody. Dimensions follow a 20-25 t class
# machine (boom about 5.7 m, stick about 2.9 m, 1.0-1.2 m3 bucket).
BOOM_FOOT = (0.72, 0.88)
BOOM_LEN = 5.70
STICK_LEN = 2.92
BUCKET_TIP = 1.48                   # bucket pivot to tooth tip

# pins, in each part's local frame (u along the part's axis, v "top" side)
BOOM_CYL_BASE = (1.28, -0.02)       # on the upper frame (y, z)
BOOM_CYL_ROD = (2.25, 0.42)         # on the boom belly bracket
STICK_CYL_BASE = (1.95, 1.52)       # on the boom top bracket
STICK_CYL_ROD = (-0.62, 0.34)       # on the stick tail
BKT_CYL_BASE = (0.30, 0.42)         # on the stick
ROCKER_PIVOT = (2.50, 0.10)         # on the stick
ROCKER_LEN = 0.56
LINK_PIN = (-0.10, 0.44)            # on the bucket, relative to its pivot
LINK_LEN = 0.52


def rot(p, a):
    c, s = math.cos(a), math.sin(a)
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c)


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def length(a):
    return math.hypot(a[0], a[1])


def ik(target, bucket_angle):
    """Solve boom/stick/bucket angles (radians, relative) for a bucket pivot target."""
    d = sub(target, BOOM_FOOT)
    L = clamp(length(d), abs(BOOM_LEN - STICK_LEN) + 1e-3, BOOM_LEN + STICK_LEN - 1e-3)
    a1, a2 = BOOM_LEN, STICK_LEN
    cos_s = (L * L - a1 * a1 - a2 * a2) / (2 * a1 * a2)
    s = -math.acos(clamp(cos_s, -1, 1))         # elbow up: stick folds down
    base = math.atan2(d[1], d[0])
    b = base + math.atan2(a2 * math.sin(-s), a1 + a2 * math.cos(s))
    k = bucket_angle - (b + s)
    return b, s, k


def circle_intersect(c0, r0, c1, r1, pick_left=True):
    d = sub(c1, c0)
    dist = max(length(d), 1e-6)
    a = (r0 * r0 - r1 * r1 + dist * dist) / (2 * dist)
    h = math.sqrt(max(r0 * r0 - a * a, 0.0))
    m = (c0[0] + a * d[0] / dist, c0[1] + a * d[1] / dist)
    off = (-d[1] / dist * h, d[0] / dist * h)
    return add(m, off) if pick_left else sub(m, off)


def arm_pose(b, s, k):
    """World-in-upper-frame positions of every pin for joint angles b, s, k."""
    foot = BOOM_FOOT
    tip = add(foot, rot((BOOM_LEN, 0), b))
    sa = b + s
    spiv = add(tip, rot((STICK_LEN, 0), sa))
    ka = sa + k

    def on_boom(p):
        return add(foot, rot(p, b))

    def on_stick(p):
        return add(tip, rot(p, sa))

    def on_bucket(p):
        return add(spiv, rot(p, ka))

    rocker = on_stick(ROCKER_PIVOT)
    link = on_bucket(LINK_PIN)
    # linkage pin P: rocker circle meets link circle, on the top side of the stick
    p_a = circle_intersect(rocker, ROCKER_LEN, link, LINK_LEN, True)
    p_b = circle_intersect(rocker, ROCKER_LEN, link, LINK_LEN, False)
    top = rot((0, 1), sa)
    P = p_a if (sub(p_a, rocker)[0] * top[0] + sub(p_a, rocker)[1] * top[1]) > \
        (sub(p_b, rocker)[0] * top[0] + sub(p_b, rocker)[1] * top[1]) else p_b
    return {
        "boom": (foot, b), "stick": (tip, sa), "bucket": (spiv, ka),
        "teeth": on_bucket((BUCKET_TIP, 0)),
        "boom_cyl": (BOOM_CYL_BASE, on_boom(BOOM_CYL_ROD)),
        "stick_cyl": (on_boom(STICK_CYL_BASE), on_stick(STICK_CYL_ROD)),
        "bkt_cyl": (on_stick(BKT_CYL_BASE), P),
        "rocker": (rocker, P), "link": (P, link),
    }


# ------------------------------------------------------------- dig timeline
def _pose(y, z_ground, dz, phi):
    """Bucket pivot at forward distance y, dz above the given ground (upper frame)."""
    return (y, z_ground - SWING_Z + dz, math.radians(phi))


REST = (4.6, 2.2, math.radians(-215))     # arm tucked, bucket curled
YAW_VARIATION = [4, -9, 7, -4, 10, -6]
REACH_VARIATION = [0.0, 0.35, -0.2, 0.25, -0.3, 0.1]

# key poses inside one cycle: (fraction of cycle, key name)
CYCLE_KEYS = [
    (0.00, "ready"), (0.12, "bite"), (0.36, "curl"), (0.50, "lift"),
    (0.66, "over_spoil"), (0.76, "dump"), (0.86, "dumped"), (1.00, "return"),
]


def depth_at(p):
    """Pit progress (0..1) as a function of overall progress."""
    c = (p - T_DIG0) / (T_DIG1 - T_DIG0) * N_CYCLES
    if c <= 0:
        return 0.0
    i = int(min(c, N_CYCLES - 1e-9))
    f = c - i
    # each cycle removes its slice during the curl phase
    step = smooth((f - 0.14) / 0.24)
    return clamp((i + step) / N_CYCLES)


def spoil_at(p):
    c = (p - T_DIG0) / (T_DIG1 - T_DIG0) * N_CYCLES
    if c <= 0:
        return 0.0
    i = int(min(c, N_CYCLES - 1e-9))
    f = c - i
    step = smooth((f - 0.76) / 0.14)
    return clamp((i + step) / N_CYCLES) ** 0.8


def water_at(p):
    return smoother((p - T_WATER0) / (T_WATER1 - T_WATER0))


def floor_z(depth_frac):
    """Ground height at the pit floor for a given pit progress."""
    return -PIT_DEPTH * depth_frac


def key_pose(name, i):
    """(yaw_deg, (y, z, phi)) for key `name` in cycle i."""
    d0 = i / N_CYCLES
    d1 = (i + 1) / N_CYCLES
    reach = REACH_VARIATION[i]
    yaw = YAW_VARIATION[i]
    if name == "ready":
        return yaw * 0.5, _pose(7.9 + reach, floor_z(d0), 2.4, -55)
    if name == "bite":
        return yaw, _pose(8.9 + reach, floor_z(d0), 0.95, -72)
    if name == "curl":
        return yaw, _pose(5.9 + reach * 0.5, floor_z(d1), 1.05, -188)
    if name == "lift":
        return yaw * 0.6, (6.4, 2.6, math.radians(-228))
    if name == "over_spoil":
        return SPOIL_YAW + yaw * 0.3, (7.2, 3.1, math.radians(-232))
    if name == "dump":
        return SPOIL_YAW + yaw * 0.3, (7.6, 2.9, math.radians(-150))
    if name == "dumped":
        return SPOIL_YAW + yaw * 0.3, (7.8, 2.8, math.radians(-68))
    if name == "return":
        ny = YAW_VARIATION[i + 1] * 0.5 if i + 1 < N_CYCLES else 0.0
        nreach = REACH_VARIATION[i + 1] if i + 1 < N_CYCLES else 0.0
        return ny, _pose(7.9 + nreach, floor_z(d1), 2.4, -55)
    raise KeyError(name)


def lerp_pose(a, b, t):
    return (lerp(a[0], b[0], t), tuple(lerp(x, y, t) for x, y in zip(a[1], b[1])))


def machine_state(p):
    """Returns dict(yaw, b, s, k, fill, load, bite, dump) at overall progress p."""
    fill, load, bite, dump = 0.0, 0.15, 0.0, 0.0
    if p < T_DIG0:
        t = smooth(p / T_DIG0)
        pose = lerp_pose((0.0, REST), key_pose("ready", 0), t)
        load = 0.15 + 0.25 * t
    elif p >= T_DIG1:
        t = smooth((p - T_DIG1) / 0.05)
        park = (0.0, (3.75, -0.05, math.radians(-205)))
        pose = lerp_pose(key_pose("return", N_CYCLES - 1), park, t)
        load = lerp(0.35, 0.08, t)
    else:
        c = (p - T_DIG0) / (T_DIG1 - T_DIG0) * N_CYCLES
        i = int(min(c, N_CYCLES - 1e-9))
        f = c - i
        for j in range(len(CYCLE_KEYS) - 1):
            f0, n0 = CYCLE_KEYS[j]
            f1, n1 = CYCLE_KEYS[j + 1]
            if f0 <= f <= f1:
                t = (f - f0) / (f1 - f0)
                # swings ease in and out, digging moves are more linear
                ease = smoother(t) if n1 in ("over_spoil", "return", "lift") else smooth(t)
                a, b = key_pose(n0, i), key_pose(n1, i)
                # during the curl the pivot follows a shallow arc through the soil
                pose = lerp_pose(a, b, ease)
                if n1 == "curl":
                    y, z, phi = pose[1]
                    pose = (pose[0], (y, z - 0.35 * math.sin(math.pi * t), phi))
                break
        # bucket fill / engine load / impulses for dust
        fill = smooth((f - 0.14) / 0.2) * (1 - smooth((f - 0.74) / 0.1))
        load = 0.3 + 0.7 * math.exp(-((f - 0.28) / 0.12) ** 2) + 0.35 * math.exp(-((f - 0.58) / 0.1) ** 2)
        bite = math.exp(-((f - 0.13) / 0.03) ** 2)
        dump = math.exp(-((f - 0.8) / 0.04) ** 2)
    yaw, (y, z, phi) = pose
    b, s, k = ik((y, z), phi)
    return dict(yaw=math.radians(yaw), b=b, s=s, k=k, fill=fill, load=clamp(load), bite=bite, dump=dump)


# -------------------------------------------------------------- camera path
# (progress, position, target, focal length mm, frame). frame 'world' keys are
# fixed; 'cab' keys ride on the swinging upper structure (over the shoulder).
CAMERA_KEYS = [
    (0.00, (-27.0, -21.0, 8.2), (2.2, 4.2, 1.2), 32, "world"),     # wide establishing
    (0.10, (-19.0, -14.0, 5.0), (1.6, 4.5, 1.6), 34, "world"),
    (0.20, (-6.6, -6.0, 1.0), (0.8, 7.0, 2.2), 22, "world"),       # low beside the tracks
    (0.31, (-7.6, -2.4, 1.1), (0.6, 7.6, 1.9), 22, "world"),
    (0.40, (-3.3, -1.8, 4.6), (-0.4, 8.6, -0.6), 22, "cab"),       # over the operator's shoulder
    (0.52, (-3.2, -1.5, 4.7), (-0.4, 8.4, -1.0), 22, "cab"),
    (0.62, (5.0, 1.2, 17.5), (1.6, 6.2, -1.2), 30, "world"),       # overhead of the pit
    (0.76, (3.4, 3.4, 19.0), (1.2, 6.6, -1.6), 30, "world"),
    (0.86, (-2.4, 11.5, 1.6), (0.3, 3.0, 0.0), 26, "world"),       # low across the water
    (1.00, (-2.8, 11.1, 0.9), (0.3, 3.2, 0.4), 26, "world"),
]


def _catmull(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    return tuple(0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3)
                 for a, b, c, d in zip(p0, p1, p2, p3))


def _key_world(key, yaw):
    _, pos, tgt, lens, frame = key
    if frame == "cab":
        c, s = math.cos(yaw), math.sin(yaw)

        def rz(v):
            return (v[0] * c - v[1] * s, v[0] * s + v[1] * c, v[2])
        return rz(pos), rz(tgt), lens
    return pos, tgt, lens


PORTRAIT_FOCUS = (0.6, 3.2, 1.6)       # machine centre; portrait frames pull toward it


def camera_at(p, aspect=16 / 9):
    pos, tgt, lens = _camera_at(p)
    pos = _keep_above_ground(p, pos)
    if aspect < 1.0:
        k = 0.35
        tgt = tuple(a + (b - a) * k for a, b in zip(tgt, PORTRAIT_FOCUS))
        # pull back so the whole machine fits a tall frame; the final shot keeps
        # its bank position so the pond stays in view
        back = 1.0 if p >= 0.8 else (1.3 if pos[2] < 12 else 1.12)
        pos = tuple(t + (p_ - t) * back for p_, t in zip(pos, tgt))
        pos = _keep_above_ground(p, pos)
        if p < 0.8 and pos[2] < 12:
            # stand above the pasture grass instead of shooting through it
            g = height(pos[0], pos[1], depth_at(p), spoil_at(p))
            pos = (pos[0], pos[1], max(pos[2], g + 1.7))
    return pos, tgt, lens


def _keep_above_ground(p, pos):
    """The spline can overshoot between a high and a low key; never go below
    the ground or the water."""
    floor = height(pos[0], pos[1], depth_at(p), spoil_at(p)) + 0.4
    level, w = water_level(p)
    if w > 0.001:
        floor = max(floor, level + 0.35)
    return (pos[0], pos[1], max(pos[2], floor))


def _camera_at(p):
    ks = CAMERA_KEYS
    yaw = machine_state(p)["yaw"]
    for i in range(len(ks) - 1):
        if ks[i][0] <= p <= ks[i + 1][0]:
            t = smoother((p - ks[i][0]) / (ks[i + 1][0] - ks[i][0]))
            idx = [max(i - 1, 0), i, i + 1, min(i + 2, len(ks) - 1)]
            w = [_key_world(ks[j], yaw) for j in idx]
            pos = _catmull(w[0][0], w[1][0], w[2][0], w[3][0], t)
            tgt = _catmull(w[0][1], w[1][1], w[2][1], w[3][1], t)
            lens = lerp(w[1][2], w[2][2], t)
            return pos, tgt, lens
    w = _key_world(ks[-1], yaw)
    return w


def water_level(p):
    w = water_at(p)
    return lerp(-PIT_DEPTH + 0.05, WATER_FINAL, w), w


# ------------------------------------------------------ world-space helpers
def to_world(st, pt):
    """Upper-frame arm-plane point (y, z) -> world (x, y, z) for machine state st."""
    c, s = math.cos(st["yaw"]), math.sin(st["yaw"])
    x, y, z = ARM_X, pt[0], pt[1] + SWING_Z
    return (x * c - y * s, x * s + y * c, z)


def teeth_world(p):
    st = machine_state(p)
    pose = arm_pose(st["b"], st["s"], st["k"])
    return to_world(st, pose["teeth"])


def bucket_world(p):
    st = machine_state(p)
    pose = arm_pose(st["b"], st["s"], st["k"])
    return to_world(st, pose["bucket"][0])


def exhaust_world(p):
    st = machine_state(p)
    c, s = math.cos(st["yaw"]), math.sin(st["yaw"])
    x, y, z = 0.95, -1.26, SWING_Z + 1.64
    return (x * c - y * s, x * s + y * c, z)


# ---------------------------------------------------------------- particles
# Particles are a pure function of progress, so scrubbing backwards replays
# them exactly. The same algorithm lives in src/hero/particles.ts.
def hash1(n):
    x = math.sin(n * 12.9898 + 78.233) * 43758.5453
    return x - math.floor(x)


CYCLE_LEN = (T_DIG1 - T_DIG0) / N_CYCLES
SECONDS_PER_UNIT = 16.0 / 1.0                     # 1.0 progress ~ 16 s of machine time


def events():
    """(kind, progress) for every bite and dump."""
    ev = []
    for i in range(N_CYCLES):
        c0 = T_DIG0 + i * CYCLE_LEN
        ev.append(("bite", c0 + 0.13 * CYCLE_LEN))
        ev.append(("dump", c0 + 0.80 * CYCLE_LEN))
    return ev


def particles(p):
    """List of dicts: kind ('dust'|'clod'|'smoke'), pos, size, alpha, seed."""
    out = []
    for n, (kind, pe) in enumerate(events()):
        dt = (p - pe) * SECONDS_PER_UNIT
        if dt < 0 or dt > 4.5:
            continue
        src = teeth_world(pe) if kind == "bite" else bucket_world(pe)
        ground = height(src[0], src[1], depth_at(pe), spoil_at(pe)) if kind == "bite" else \
            height(src[0], src[1], 0, spoil_at(pe))
        count = 14 if kind == "bite" else 22
        for j in range(count):
            h = n * 97 + j * 13
            a = hash1(h) * math.tau
            sp = 0.4 + hash1(h + 1) * 1.1
            life = 2.2 + hash1(h + 2) * 2.2
            if dt > life:
                continue
            t = dt / life
            rise = 0.4 + hash1(h + 3) * 1.2
            drift = (0.55, 0.25)                       # light breeze
            x = src[0] + math.cos(a) * sp * (1 - math.exp(-dt * 1.5)) + drift[0] * dt
            y = src[1] + math.sin(a) * sp * (1 - math.exp(-dt * 1.5)) + drift[1] * dt
            z0 = ground if kind == "bite" else ground + 0.4
            z = z0 + 0.25 + rise * (1 - math.exp(-dt * 0.9))
            size = (0.7 + hash1(h + 4) * 0.9) * (0.6 + 1.9 * t) * (1.4 if kind == "dump" else 1.0)
            alpha = (1 - t) ** 1.5 * min(1.0, dt * 6) * (0.55 if kind == "dump" else 0.4)
            out.append(dict(kind="dust", pos=(x, y, z), size=size, alpha=alpha, seed=h))
        if kind == "dump":                            # falling clods
            for j in range(10):
                h = n * 131 + j * 7
                life = 0.9
                if dt > life:
                    continue
                vx = (hash1(h) - 0.5) * 1.6
                vy = (hash1(h + 1) - 0.5) * 1.6
                x = src[0] + vx * dt
                y = src[1] + vy * dt
                z = src[2] - 0.3 - 4.9 * dt * dt
                gz = height(x, y, 0, spoil_at(pe))
                if z < gz:
                    continue
                out.append(dict(kind="clod", pos=(x, y, z), size=0.12 + hash1(h + 2) * 0.16, alpha=1, seed=h))
    # diesel exhaust: a puff every 1/40 of progress-second, denser under load
    rate = 7.0                                        # puffs per machine-second
    t_now = p * SECONDS_PER_UNIT
    for k in range(int(t_now * rate) - 30, int(t_now * rate) + 1):
        if k < 0:
            continue
        ts = k / rate
        age = t_now - ts
        if age < 0 or age > 4.0:
            continue
        ps = ts / SECONDS_PER_UNIT
        load = machine_state(ps)["load"]
        src = exhaust_world(ps)
        t = age / 4.0
        x = src[0] + 0.9 * age + (hash1(k) - 0.5) * 0.4 * age
        y = src[1] + 0.35 * age + (hash1(k + 1) - 0.5) * 0.4 * age
        z = src[2] + 1.1 * age ** 0.7
        dark = load
        out.append(dict(kind="smoke", pos=(x, y, z), size=0.25 + 1.6 * t, alpha=(1 - t) ** 2 * (0.12 + 0.5 * load ** 2),
                        dark=dark, seed=k))
    return out


# ------------------------------------------------------------------ framing
# The hero keeps the machine clear of the service card. Card sits lower-left
# on wide screens and along the bottom on portrait screens; the projection is
# shifted (lens shift) so the subject lands in the free area.
def fov_for_aspect(lens_mm, aspect):
    """Vertical field of view (radians) for a 36 mm-wide sensor at this aspect."""
    hfov_land = 2 * math.atan(18.0 / lens_mm)
    vfov_land = 2 * math.atan(math.tan(hfov_land / 2) / (16 / 9))
    hfov_min = hfov_land * 0.74
    return max(vfov_land, 2 * math.atan(math.tan(hfov_min / 2) / aspect))


def lens_shift(aspect):
    """NDC-space projection offset (x, y) for this aspect."""
    if aspect >= 1.0:
        return (-0.16, 0.02)
    return (0.0, -0.26)
