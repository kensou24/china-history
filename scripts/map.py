#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
map.py — 疆域时空地图数据管线。

输入：raw/cliopatria.geojson（CC BY 4.0，不入库）
      raw/naturalearth/ne_50m_coastline + ne_50m_rivers_lake_centerlines（公有领域，不入库）
      scripts/map_dynasties.json（朝代映射表，人工校订）
      data/dynasties.json（25 朝代年表）
输出：data/map.json（烘焙好 SVG path 的静态数据）
      data/map_preview/<dynastyId>.svg（每朝代校订预览图）

用法：python3 scripts/map.py
"""
import json
import sys
from pathlib import Path

import shapefile  # pyshp
from pyproj import Transformer
from shapely.geometry import MultiPolygon, box, shape
from shapely.ops import transform as shp_transform

try:
    from shapely.ops import polylabel
except ImportError:  # 无 polylabel 时退回 representative_point
    polylabel = None

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
DATA = ROOT / "data"
PREVIEW = DATA / "map_preview"

WIN_W, WIN_S, WIN_E, WIN_N = 73.0, 15.5, 136.0, 54.0  # 中国视窗（经纬度）
YEAR_MIN, YEAR_MAX = -2100, 1912     # 本书范围：夏之前 ~ 清亡
SIMPLIFY_M = 25_000.0                # Albers 米制抽稀容差（≈25km）；超预算时调大重跑
MIN_PART_M2 = 2e8                    # 舍弃 <200 km² 碎块（海南岛约 3.4 万 km²，安全）
VIEW_W = 1000                        # viewBox 宽，高按投影比例算
BUDGET = 1_200_000                   # map.json 字节预算

ALBERS = ("+proj=aea +lat_1=25 +lat_2=47 +lat_0=0 +lon_0=105 "
          "+datum=WGS84 +units=m +no_defs")

CITIES = [  # 现代城市参考点（名称, 经度, 纬度）
    ("北京", 116.40, 39.90), ("西安", 108.94, 34.34), ("洛阳", 112.45, 34.62),
    ("开封", 114.35, 34.79), ("南京", 118.80, 32.06), ("杭州", 120.16, 30.29),
    ("成都", 104.07, 30.57), ("广州", 113.26, 23.13),
]

to_albers = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True).transform

# 视窗四角 → Albers 米制边界（外扩 1% 吸收投影边缘弧度），SVG 坐标以此为基准
_xs, _ys = [], []
for _lon in (WIN_W, WIN_E):
    for _lat in (WIN_S, WIN_N):
        _x, _y = to_albers(_lon, _lat)
        _xs.append(_x)
        _ys.append(_y)
_mx, _my = max(_xs) - min(_xs), max(_ys) - min(_ys)
M_X0, M_Y1 = min(_xs) - _mx * 0.01, max(_ys) + _my * 0.01
SCALE = VIEW_W / (_mx * 1.02)
VIEW_H = round(_my * 1.02 * SCALE)


def bake_xy(x, y):
    """Albers 米 → SVG 整数坐标（y 轴翻转）"""
    return round((x - M_X0) * SCALE), round((M_Y1 - y) * SCALE)


def albers_geom(g):
    return shp_transform(to_albers, g)


def ring_path(coords):
    pts = [bake_xy(x, y) for x, y in coords]
    if len(pts) < 3:
        return ""
    return (f"M{pts[0][0]} {pts[0][1]}"
            + "".join(f"L{x} {y}" for x, y in pts[1:]) + "Z")


def geom_to_path(g):
    """(Multi)Polygon（Albers 米制）→ (path 字符串, 最大块几何)。"""
    polys = list(g.geoms) if isinstance(g, MultiPolygon) else [g]
    polys = [p for p in polys if p.area >= MIN_PART_M2]
    if not polys:
        return "", None
    d = "".join(ring_path(p.exterior.coords) for p in polys)
    return d, max(polys, key=lambda p: p.area)


def label_of(poly):
    pt = polylabel(poly, tolerance=10_000.0) if polylabel else poly.representative_point()
    return list(bake_xy(pt.x, pt.y))


def line_path(g):
    geoms = list(g.geoms) if hasattr(g, "geoms") else [g]
    d = ""
    for ln in geoms:
        pts = [bake_xy(x, y) for x, y in ln.coords]
        if len(pts) >= 2:
            d += (f"M{pts[0][0]} {pts[0][1]}"
                  + "".join(f"L{x} {y}" for x, y in pts[1:]))
    return d


def read_lines(shp_path, win):
    """shapefile 线要素 → 裁剪到视窗 → Albers 几何列表"""
    out = []
    for sr in shapefile.Reader(str(shp_path)).iterShapeRecords():
        if sr.shape.shapeType == shapefile.NULL:  # rivers 数据含 NULL 空记录，跳过
            continue
        g = shape(sr.shape.__geo_interface__)
        if g.intersects(win):
            c = g.intersection(win)
            if not c.is_empty:
                out.append(albers_geom(c))
    return out


def norm(s):
    return "".join(str(s).lower().split())


def row_matches(row, clio):
    t = norm(clio)
    return t and (t in norm(row["name"]) or t in norm(row["wiki"]))


def emit_shape(shapes, name, dyn_id, f, t, geom, win):
    g = geom.intersection(win)
    if g.is_empty:
        return
    g = albers_geom(g).simplify(SIMPLIFY_M, preserve_topology=True)
    if g.is_empty:
        return
    d, biggest = geom_to_path(g)
    if not d:
        return
    bx0, by0, bx1, by1 = g.bounds
    x0, y0 = bake_xy(bx0, by1)   # 注意 y 翻转：米制 by1（北）对应 SVG 较小 y
    x1, y1 = bake_xy(bx1, by0)
    shapes.append({
        "n": name, "dyn": dyn_id, "from": f, "to": t, "d": d,
        "bbox": [x0, y0, x1 - x0, y1 - y0], "label": label_of(biggest),
    })


def main():
    clio_path = RAW / "cliopatria.geojson"
    if not clio_path.exists():
        sys.exit("缺少 raw/cliopatria.geojson —— 先执行计划 Task 1 的下载步骤")
    mapping = json.loads((ROOT / "scripts" / "map_dynasties.json").read_text("utf-8"))
    dynasties = {d["id"]: d for d in
                 json.loads((DATA / "dynasties.json").read_text("utf-8"))["dynasties"]}
    win = box(WIN_W, WIN_S, WIN_E, WIN_N)

    print("加载 Cliopatria …")
    feats = json.loads(clio_path.read_text("utf-8"))["features"]
    rows = []
    for f in feats:
        p = f.get("properties") or {}
        if p.get("Type") != "POLITY":
            continue
        fy, ty = p.get("FromYear"), p.get("ToYear")
        if fy is None or ty is None or ty < YEAR_MIN or fy > YEAR_MAX:
            continue
        g = shape(f["geometry"])
        if not g.is_valid:
            g = g.buffer(0)
        if g.is_empty or not g.intersects(win):
            continue
        rows.append({"name": p.get("Name", "?"), "wiki": p.get("Wikipedia", ""),
                     "from": int(fy), "to": int(ty), "geom": g})
    print(f"中国区域相关政权记录: {len(rows)} 条")

    # 朝代 shape：映射表驱动，按 dynasties.json 年表切分区间
    shapes, consumed, unmatched = [], set(), []
    for dyn_id, ent in mapping["dynasties"].items():
        dyn = dynasties[dyn_id]
        parts = ent.get("parts") or [{"clio": ent["clio"], "n": dyn["name"]}]
        hit_any = False
        for part in parts:
            names = set()
            for i, r in enumerate(rows):
                if not row_matches(r, part["clio"]):
                    continue
                names.add(r["name"])
                f, t = max(r["from"], dyn["start"]), min(r["to"], dyn["end"])
                if f >= t:
                    continue
                consumed.add(i)
                hit_any = True
                emit_shape(shapes, part["n"], dyn_id, f, t, r["geom"], win)
            if len(names) > 1:
                print(f"  [提示] {dyn_id}「{part['clio']}」匹配多个实体: {sorted(names)}")
        if not hit_any:
            unmatched.append(dyn_id)

    # 中立政权（未被朝代映射消耗的记录）
    neighbors = mapping.get("neighbors", {})
    for i, r in enumerate(rows):
        if i not in consumed:
            emit_shape(shapes, neighbors.get(r["name"], r["name"]), None,
                       max(r["from"], YEAR_MIN), min(r["to"], YEAR_MAX), r["geom"], win)

    # 底图：海岸线 + 河流 + 城市参考点（不画现代国界，spec 决策）
    ne = RAW / "naturalearth"
    coast = "".join(line_path(g) for g in read_lines(
        ne / "ne_50m_coastline" / "ne_50m_coastline.shp", win))
    rivers = [d for d in (line_path(g) for g in read_lines(
        ne / "ne_50m_rivers_lake_centerlines" / "ne_50m_rivers_lake_centerlines.shp",
        win)) if d]
    cities = [{"n": n, "x": bake_xy(*to_albers(lon, lat))[0],
               "y": bake_xy(*to_albers(lon, lat))[1]} for n, lon, lat in CITIES]

    change_years = sorted({y for s in shapes for y in (s["from"], s["to"])})
    out = {
        "viewBox": f"0 0 {VIEW_W} {VIEW_H}",
        "basemap": {"coast": coast, "rivers": rivers, "cities": cities},
        "changeYears": change_years,
        "shapes": shapes,
        "dynastyMap": {k: {"clio": (v.get("clio")
                                    or [p["clio"] for p in v["parts"]]),
                           "year": v["year"]}
                       for k, v in mapping["dynasties"].items()},
        "unmapped": mapping.get("unmapped", []),
    }
    DATA.mkdir(exist_ok=True)
    mp = DATA / "map.json"
    mp.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), "utf-8")
    size = mp.stat().st_size
    print(f"map.json: shapes {len(shapes)} | 年份点 {len(change_years)} | {size/1024:.0f}KB")
    if size > BUDGET:
        print(f"  [警告] 超预算 {size/1e6:.2f}MB > 1.2MB —— 调大 SIMPLIFY_M 后重跑")
    if unmatched:
        print(f"  [警告] 未匹配朝代: {unmatched} —— 对照 map_explore.py 输出修正映射表"
              f"（或确认数据缺失后移入 unmapped）")

    # 校订预览：每朝代一张 SVG（底图 + 该朝高亮 + 同代政权淡显）
    PREVIEW.mkdir(parents=True, exist_ok=True)
    for dyn_id, ent in mapping["dynasties"].items():
        yr = ent["year"]
        body = f'<path d="{coast}" fill="none" stroke="#bbb" stroke-width="1"/>'
        for s in shapes:
            if not (s["from"] <= yr <= s["to"]):
                continue
            on = s["dyn"] == dyn_id
            body += (f'<path d="{s["d"]}" fill="{"#c0392b" if on else "#ccc"}"'
                     f' fill-opacity="{"0.9" if on else "0.4"}"'
                     f' stroke="#888" stroke-width="0.5"/>'
                     f'<text x="{s["label"][0]}" y="{s["label"][1]}" font-size="14"'
                     f' text-anchor="middle">{s["n"]}</text>')
        dyn = dynasties[dyn_id]
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{out["viewBox"]}">'
               f'<rect width="100%" height="100%" fill="#f6f1e7"/>'
               f'<text x="20" y="30" font-size="20">{dyn["name"]} · 代表年 {yr}</text>'
               f'{body}</svg>')
        (PREVIEW / f"{dyn_id}.svg").write_text(svg, "utf-8")
    print(f"预览图: {PREVIEW}/ （{len(mapping['dynasties'])} 张）")


if __name__ == "__main__":
    main()
