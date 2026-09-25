"""Export the scene timeline for the real-time hero: public/hero/timeline.json

Pure Python (no Blender needed). Coordinates are converted to three.js
(x, y, z) = (x, z, -y).
"""
import json
import math
import os

import common as C

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "public", "hero", "timeline.json")
N = 481


def t3(v):
    return [round(v[0], 3), round(v[2], 3), round(-v[1], 3)]


samples = []
for i in range(N):
    p = i / (N - 1)
    pl, tl, ll = C.camera_at(p, 16 / 9)
    pp, tp, lp = C.camera_at(p, 9 / 16)
    st = C.machine_state(p)
    level, w = C.water_level(p)
    samples.append([
        *t3(pl), *t3(tl), round(ll, 2),
        *t3(pp), *t3(tp), round(lp, 2),
        round(C.depth_at(p), 4), round(C.spoil_at(p), 4), round(level, 3), round(w, 4),
        round(st["load"], 3), *t3(C.exhaust_world(p)),
    ])

events = []
for kind, pe in C.events():
    src = C.teeth_world(pe) if kind == "bite" else C.bucket_world(pe)
    ground = C.height(src[0], src[1], C.depth_at(pe), C.spoil_at(pe)) if kind == "bite" else \
        C.height(src[0], src[1], 0, C.spoil_at(pe))
    events.append({"kind": kind, "p": round(pe, 5), "pos": t3(src), "ground": round(ground, 3)})

data = {
    "fields": ["camL.x", "camL.y", "camL.z", "tgtL.x", "tgtL.y", "tgtL.z", "lensL",
               "camP.x", "camP.y", "camP.z", "tgtP.x", "tgtP.y", "tgtP.z", "lensP",
               "pit", "spoil", "waterLevel", "water", "load", "exh.x", "exh.y", "exh.z"],
    "samples": samples,
    "events": events,
    "secondsPerUnit": C.SECONDS_PER_UNIT,
    "terrain": {
        "pitCenter": C.PIT_CENTER, "pitHalf": C.PIT_HALF, "pitWall": C.PIT_WALL, "pitDepth": C.PIT_DEPTH,
        "spoilCenter": C.spoil_center(), "spoilYaw": C.SPOIL_YAW, "spoilRadius": C.SPOIL_RADIUS,
        "spoilHeight": C.SPOIL_HEIGHT, "strata": C.STRATA,
    },
    "sun": {"azimuthDeg": 208, "elevationDeg": 17},
    "cards": {"pond": [C.T_WATER0 - 0.02, 1.0]},
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as f:
    json.dump(data, f, separators=(",", ":"))
print("wrote", OUT, os.path.getsize(OUT), "bytes")
