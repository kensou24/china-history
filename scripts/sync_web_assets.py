#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_web_assets.py — 将 data/ 生成的数据同步到 web/public/（前端静态资产）。

- data/*.json        → web/public/data/
- data/images/*.webp → web/public/images/
- data/images_orig/  → web/public/images_orig/

用法：python3 scripts/sync_web_assets.py [--skip-orig]
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PUBLIC = ROOT / "web" / "public"

SKIP_ORIG = "--skip-orig" in sys.argv


def sync_dir(src: Path, dst: Path):
    dst.mkdir(parents=True, exist_ok=True)
    # 清空目标，保证与数据一致
    for f in dst.iterdir():
        if f.is_dir():
            shutil.rmtree(f)
        else:
            f.unlink()
    n = 0
    for f in src.iterdir():
        if f.is_file():
            shutil.copy2(f, dst / f.name)
            n += 1
    print(f"  {src.name} → {dst}: {n} 个文件")


def main():
    print("同步数据到前端 public/ …")
    sync_dir(DATA, PUBLIC / "data")
    sync_dir(DATA / "images", PUBLIC / "images")
    if not SKIP_ORIG:
        sync_dir(DATA / "images_orig", PUBLIC / "images_orig")
    else:
        print("  （跳过原图同步）")
    print("完成。")


if __name__ == "__main__":
    main()
