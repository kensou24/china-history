#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate.py — 数据管线完整性校验。

校验项：
  1. 卷数/章数（100 章，各卷 16/23/23/13/25）
  2. 章节 id 唯一连续 ch001..ch100
  3. blocks 类型合法（p/sec/fig/cap）
  4. 每章摘要非空、字数 > 0
  5. 插图引用均有 WebP 缩略图与 JPEG 原图
  6. meta.json 与 volN.json 的章节标题/字数一致

用法：python3 scripts/validate.py
退出码：0 全部通过，1 存在错误
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
EXPECTED = {1: 16, 2: 23, 3: 23, 4: 13, 5: 25}
VALID_T = {"p", "sec", "fig", "cap"}
MAP_BUDGET = 1_200_000  # map.json 字节预算


def validate_map():
    m = json.loads((DATA / "map.json").read_text(encoding="utf-8"))
    dynasties = json.loads((DATA / "dynasties.json").read_text(encoding="utf-8"))["dynasties"]
    ids = [d["id"] for d in dynasties]
    # basemap 字段
    for k in ("coast", "rivers", "cities"):
        if k not in m.get("basemap", {}):
            errors.append(f"map.json basemap 缺 {k}")
    if not m["basemap"]["coast"].startswith("M"):
        errors.append("map.json coast path 异常")
    # 25 朝代：必须出现在 dynastyMap 或 unmapped 之一
    dm, un = m.get("dynastyMap", {}), set(m.get("unmapped", []))
    for i in ids:
        if i not in dm and i not in un:
            errors.append(f"map.json 朝代 {i} 既不在 dynastyMap 也不在 unmapped")
    for i in dm:
        if i not in ids:
            errors.append(f"map.json dynastyMap 含未知朝代 {i}")
    # shapes 自洽
    valid = set(ids) | {None}
    boundaries = set()
    for s in m.get("shapes", []):
        if s["dyn"] not in valid:
            errors.append(f"map.json shape「{s['n']}」dyn 非法: {s['dyn']}")
        if not s["from"] <= s["to"]:  # 闭区间模型：from==to 为合法单年记录（中立政权）
            errors.append(f"map.json shape「{s['n']}」年份区间非法")
        if not s["d"].startswith("M"):
            errors.append(f"map.json shape「{s['n']}」path 为空")
        if len(s.get("bbox", [])) != 4 or len(s.get("label", [])) != 2:
            errors.append(f"map.json shape「{s['n']}」缺 bbox/label")
        boundaries.update((s["from"], s["to"]))
    cy = m.get("changeYears", [])
    if cy != sorted(set(cy)) or set(cy) != boundaries:
        errors.append("map.json changeYears 与 shapes 边界不一致")
    size = (DATA / "map.json").stat().st_size
    if size > MAP_BUDGET:
        errors.append(f"map.json 超预算: {size/1e6:.2f}MB > 1.2MB（调大 map.py 的 SIMPLIFY_M）")
    print(f"地图: shapes {len(m['shapes'])} | 年份点 {len(cy)} | {size/1024:.0f}KB")


errors, warnings = [], []


def main():
    meta = json.loads((DATA / "meta.json").read_text(encoding="utf-8"))
    vols = {v["id"]: json.loads((DATA / f"vol{v['id']}.json").read_text(encoding="utf-8"))
            for v in meta["volumes"]}

    # 1. 卷数/章数
    if len(meta["volumes"]) != 5:
        errors.append(f"卷数异常: {len(meta['volumes'])}")
    for v in meta["volumes"]:
        got = len(v["chapters"])
        if got != EXPECTED.get(v["id"]):
            errors.append(f"卷{v['id']} 章数 {got} ≠ 预期 {EXPECTED.get(v['id'])}")
    all_chapters = [c for v in meta["volumes"] for c in v["chapters"]]
    if len(all_chapters) != 100:
        errors.append(f"总章数 {len(all_chapters)} ≠ 100")

    # 2. 章节 id 连续
    ids = [c["id"] for v in meta["volumes"] for c in v["chapters"]]
    expect_ids = [f"ch{i:03d}" for i in range(1, 101)]
    if ids != expect_ids:
        errors.append("章节 id 不连续")

    # 3-4. 逐章校验（meta 与 vol 一致性）
    for v in meta["volumes"]:
        vv = vols[v["id"]]
        if len(vv["chapters"]) != len(v["chapters"]):
            errors.append(f"卷{v['id']} meta/vol 章数不一致")
            continue
        for mc, vc in zip(v["chapters"], vv["chapters"]):
            for field in ("id", "title", "wordCount"):
                if mc[field] != vc[field]:
                    errors.append(f"{mc['id']} meta/vol 的 {field} 不一致")
            for b in vc["blocks"]:
                if b["t"] not in VALID_T:
                    errors.append(f"{vc['id']} 非法 block 类型: {b['t']}")
            if not mc["summary"]:
                warnings.append(f"{mc['id']} {mc['title']}: 摘要为空")
            if mc["wordCount"] <= 0:
                errors.append(f"{mc['id']} {mc['title']}: 字数 0")

    # 5. 图片引用完整性
    for v in meta["volumes"]:
        vv = vols[v["id"]]
        for vc in vv["chapters"]:
            for b in vc["blocks"]:
                if b["t"] == "fig":
                    img = b["img"]
                    if not (DATA / "images" / f"{img}.webp").exists():
                        errors.append(f"{vc['id']} 缺缩略图: {img}.webp")
                    if not (DATA / "images_orig" / f"{img}.jpeg").exists():
                        errors.append(f"{vc['id']} 缺原图: {img}.jpeg")

    # 6. 疆域地图（无 map.json 时跳过：仅有 EPUB 的管线使用方不需要它）
    if (DATA / "map.json").exists():
        validate_map()
    else:
        print("（无 map.json，跳过地图校验）")

    # 汇总
    total_chars = meta["book"]["totalChars"]
    calc_chars = sum(c["wordCount"] for v in meta["volumes"] for c in v["chapters"])
    if total_chars != calc_chars:
        errors.append(f"meta 总字数 {total_chars} ≠ 实际 {calc_chars}")

    print(f"卷数: {len(meta['volumes'])} | 章数: {len(all_chapters)} | "
          f"总字数: {calc_chars} | 引用图片: {meta['book']['totalImages']}")
    print(f"错误: {len(errors)} | 警告: {len(warnings)}")
    for e in errors[:20]:
        print("  [ERR]", e)
    for w in warnings[:10]:
        print("  [WARN]", w)

    if errors:
        print("校验未通过")
        return 1
    print("校验通过 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
