#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
map_explore.py — 探查 Cliopatria 中与中国区域相关的政权（填映射表前必跑）。

打印：按名称聚合的政权清单（名称 / 年份区间 / 记录数 / Wikipedia 字段）。
用法：python3 scripts/map_explore.py [关键词]   # 可选：只打印名称含关键词的
"""
import json
import sys
from pathlib import Path

from shapely.geometry import box, shape

ROOT = Path(__file__).resolve().parent.parent
WIN = box(73.0, 15.5, 136.0, 54.0)   # 与 map.py 中国视窗一致
YEAR_MIN, YEAR_MAX = -2100, 1912


def main():
    kw = sys.argv[1].lower() if len(sys.argv) > 1 else None
    feats = json.loads((ROOT / "raw" / "cliopatria.geojson").read_text("utf-8"))["features"]
    agg = {}   # name -> [minFrom, maxTo, rows, wiki]
    for f in feats:
        p = f.get("properties") or {}
        if p.get("Type") != "POLITY":
            continue
        fy, ty = p.get("FromYear"), p.get("ToYear")
        if fy is None or ty is None or ty < YEAR_MIN or fy > YEAR_MAX:
            continue
        g = shape(f["geometry"])
        if not g.intersects(WIN):
            continue
        name = p.get("Name", "?")
        if kw and kw not in name.lower() and kw not in str(p.get("Wikipedia", "")).lower():
            continue
        a = agg.setdefault(name, [fy, ty, 0, p.get("Wikipedia", "")])
        a[0] = min(a[0], fy)
        a[1] = max(a[1], ty)
        a[2] += 1
    for name in sorted(agg):
        a = agg[name]
        print(f"{a[0]:>6} ~ {a[1]:>6}  x{a[2]:<3} {name}   | {a[3]}")
    print(f"\n共 {len(agg)} 个政权实体")


if __name__ == "__main__":
    main()
