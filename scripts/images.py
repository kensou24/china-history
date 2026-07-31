#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
images.py — 提取《中国通史》插图并压缩为 WebP 缩略图。

- 依据 vol1..5.json 中的正文引用清单提取图片（避免导出无引用图）
- 缩略图: data/images/XXXXX.webp   （长边 ≤ 900px, WebP q82，阅读页使用）
- 原图:   data/images_orig/XXXXX.jpeg（灯箱查看原图）

用法：python3 scripts/images.py [epub路径]
"""
import json
import sys
import zipfile
from pathlib import Path

try:
    from PIL import Image
    import io
except ImportError:
    Image = None

ROOT = Path(__file__).resolve().parent.parent
EPUB = ROOT / "中国通史 五卷本（中国社会科学院撰稿） - 卜宪群.epub"
DATA = ROOT / "data"
THUMB_DIR = DATA / "images"
ORIG_DIR = DATA / "images_orig"
MAX_EDGE = 480      # 缩略图长边像素
QUALITY = 68        # WebP 质量（灯箱看原图，缩略图可激进压缩）


def collect_referenced_images():
    """从分卷正文收集所有被引用的图片 id。"""
    ids = set()
    for i in range(1, 6):
        vol = json.loads((DATA / f"vol{i}.json").read_text(encoding="utf-8"))
        for ch in vol["chapters"]:
            for b in ch["blocks"]:
                if b["t"] == "fig":
                    ids.add(b["img"])
    return ids


def convert_one(z: zipfile.ZipFile, img_id: str):
    """读取并写出缩略图 + 原图，返回 (thumb_bytes, ok) 或 (None, False)。"""
    entry = f"images/{img_id}.jpeg"
    try:
        raw = z.read(entry)
    except KeyError:
        return None, False

    (ORIG_DIR / f"{img_id}.jpeg").write_bytes(raw)

    if Image is None:
        return None, True  # 无 pillow 时仅归档原图

    img = Image.open(io.BytesIO(raw))
    if img.mode not in ("RGB", "L", "RGBA"):
        img = img.convert("RGB")
    w, h = img.size
    if max(w, h) > MAX_EDGE:
        scale = MAX_EDGE / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "WEBP", quality=QUALITY, method=4)
    (THUMB_DIR / f"{img_id}.webp").write_bytes(buf.getvalue())
    return buf.getvalue(), True


def main():
    epub_path = sys.argv[1] if len(sys.argv) > 1 else EPUB
    z = zipfile.ZipFile(epub_path)
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    ORIG_DIR.mkdir(parents=True, exist_ok=True)

    refs = sorted(collect_referenced_images())
    print(f"正文引用图片: {len(refs)} 张")

    if Image is None:
        print("[warn] 未安装 pillow，仅归档原图，跳过 WebP 压缩")

    ok, missing = 0, []
    thumb_total = 0
    for img_id in refs:
        data, success = convert_one(z, img_id)
        if success:
            ok += 1
            if data:
                thumb_total += len(data)
        else:
            missing.append(img_id)
    print(f"成功: {ok} | 缺失: {len(missing)} {missing[:10]}")
    if thumb_total:
        print(f"缩略图总体积: {thumb_total / 1024 / 1024:.1f} MB")
    print(f"输出目录: {THUMB_DIR} (WebP 缩略图), {ORIG_DIR} (原图)")

    # 校验清单落盘
    (DATA / "image_refs.json").write_text(
        json.dumps({"referenced": refs, "missing": missing}, ensure_ascii=False, indent=1),
        encoding="utf-8")


if __name__ == "__main__":
    main()
