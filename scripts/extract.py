#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract.py — 将《中国通史》五卷本 EPUB 提取为结构化 JSON。

输出：
  data/meta.json          书籍 + 五卷 + 100 章元数据（标题/字数/摘要/朝代占位）
  data/vol1..5.json       分卷正文（blocks: 段落/小节/插图）

用法：python3 scripts/extract.py [epub路径]
"""
import json
import re
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EPUB = ROOT / "中国通史 五卷本（中国社会科学院撰稿） - 卜宪群.epub"
OUT = ROOT / "data"

# 卷序列表（目录文件序号，来自实测探测）
VOLUME_TOC = [
    ("中国通史.从中华先祖到春秋战国", 13),
    ("中国通史.秦汉魏晋南北朝", 44),
    ("中国通史.隋唐五代两宋", 82),
    ("中国通史.辽西夏金元", 120),
    ("中国通史.明清", 148),
]
# 前置/非正文章节标题
SKIP_TITLES = {
    "封面", "总目录", "国家2011计划", "文前彩插", "编委会",
    "让史学研究成果服务于人民群众", "历史为鉴 光影为媒", "探寻历史 走向未来",
    "影像版的中国历史全书", "《中国通史》总目", "目录",
}


class BodyParser(HTMLParser):
    """解析 body 直接子元素，输出扁平 block 序列。"""

    def __init__(self):
        super().__init__()
        self.in_body = False
        self.depth = 0          # body 内深度
        self.p_depth = 0        # 当前 <p> 深度（0 = 不在 p 内）
        self.blocks = []        # [{type, cls, text_parts: [(bold, text)], img}]
        self.cur = None
        self.bold = False
        self.in_head = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "body":
            self.in_body = True
            self.depth = 0
            return
        if not self.in_body:
            return
        self.depth += 1
        if tag == "p":
            self.p_depth = self.depth
            self.cur = {"cls": a.get("class", ""), "parts": [], "img": None}
            return
        if self.cur is not None and tag == "b":
            self.bold = True
        elif self.cur is not None and tag == "img":
            src = a.get("src", "")
            m = re.search(r"images/(\d+)\.jpe?g", src)
            self.cur["img"] = m.group(1) if m else src

    def handle_endtag(self, tag):
        if tag == "body":
            self.in_body = False
            return
        if not self.in_body:
            return
        if tag == "p" and self.p_depth == self.depth:
            if self.cur is not None:
                self.blocks.append(self.cur)
                self.cur = None
            self.p_depth = 0
        if tag == "b":
            self.bold = False
        self.depth -= 1

    def handle_data(self, data):
        if self.cur is not None and self.p_depth:
            t = data.strip()
            if t:
                self.cur["parts"].append((self.bold, t))


def parse_part(html: str) -> dict:
    """解析单个章节 HTML → {title, blocks}。blocks 元素：
       {t:'p', text} | {t:'sec', title} | {t:'fig', img, caption}
    """
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    title = re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""
    parser = BodyParser()
    parser.feed(html)

    raw = []
    for b in parser.blocks:
        text = "".join(t for _, t in b["parts"])
        if b["img"] is not None and not text:
            # 纯图段落（tp-c 或正文内嵌）
            raw.append({"type": "fig", "img": b["img"], "caption": ""})
        elif b["cls"] == "tp-c" and b["img"] is None and text:
            # 图注：并入上一张图
            if raw and raw[-1]["type"] == "fig" and not raw[-1]["caption"]:
                raw[-1]["caption"] = text
            else:
                raw.append({"type": "caption", "text": text})
        elif b["cls"] == "tp-c" and b["img"] is not None and text:
            # 图注文字与图同段
            raw.append({"type": "fig", "img": b["img"], "caption": text})
        elif text:
            # 段首粗体小节标题（如「初试锋芒。」+ 正文同段）
            first_bold, first_txt = b["parts"][0] if b["parts"] else (False, "")
            if first_bold and re.match(r"^[^，。；：？！、\n]{1,12}[。、]?$", first_txt):
                raw.append({"type": "sec", "title": first_txt.rstrip("。、"),
                            "body": text[len(first_txt):].strip()})
            else:
                raw.append({"type": "p", "text": text})

    # 组装 blocks
    blocks = []
    for r in raw:
        if r["type"] == "sec":
            blocks.append({"t": "sec", "title": r["title"]})
            if r.get("body"):
                blocks.append({"t": "p", "text": r["body"]})
        elif r["type"] == "p" and r["text"].startswith("　"):
            blocks.append({"t": "p", "text": r["text"].lstrip("　")})
        elif r["type"] == "p" and r["text"]:
            blocks.append({"t": "p", "text": r["text"]})
        elif r["type"] == "fig":
            blocks.append({"t": "fig", "img": r["img"], "caption": r["caption"]})
        elif r["type"] == "caption":
            blocks.append({"t": "cap", "text": r["text"]})
    return {"title": title, "blocks": blocks}


def word_count(text: str) -> int:
    return len(re.sub(r"\s", "", text))


def main():
    epub_path = sys.argv[1] if len(sys.argv) > 1 else EPUB
    z = zipfile.ZipFile(epub_path)
    out_dir = OUT
    out_dir.mkdir(parents=True, exist_ok=True)

    # 扫描全部 part 文件 → 标题
    title_map = {}
    for n in z.namelist():
        m = re.match(r"text/part(\d{4})\.html$", n)
        if not m:
            continue
        idx = int(m.group(1))
        html = z.read(n).decode("utf-8", errors="replace")
        hm = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
        title = re.sub(r"<[^>]+>", "", hm.group(1)).strip() if hm else ""
        title_map[idx] = (title, html)

    # 卷边界
    volumes = []
    for vi, (vtitle, toc_idx) in enumerate(VOLUME_TOC):
        end_idx = VOLUME_TOC[vi + 1][1] if vi + 1 < len(VOLUME_TOC) else 9999
        chapters = []
        for idx in range(toc_idx + 1, end_idx):
            if idx not in title_map:
                continue
            title, html = title_map[idx]
            if not title or title in SKIP_TITLES:
                continue
            parsed = parse_part(html)
            blocks = parsed["blocks"]
            # 摘要：第一个正文段落（导语段）
            summary = next((b["text"] for b in blocks if b["t"] == "p"), "")
            chars = sum(word_count(b["text"]) for b in blocks if b["t"] in ("p", "cap"))
            # 图片清单（正文内引用）
            imgs = [b["img"] for b in blocks if b["t"] == "fig"]
            chapters.append({
                "file": f"part{idx:04d}",
                "title": parsed["title"] or title,
                "wordCount": chars,
                "summary": summary,
                "imageCount": len(imgs),
                "images": imgs,
                "blocks": blocks,
            })
        volumes.append({"id": vi + 1, "title": vtitle, "chapters": chapters})

    total_chars = sum(c["wordCount"] for v in volumes for c in v["chapters"])
    total_imgs = sum(c["imageCount"] for v in volumes for c in v["chapters"])

    # 输出 meta.json（轻量元数据，供目录/时间轴）
    meta_volumes = []
    ch_seq = 0
    for v in volumes:
        vmeta = {"id": v["id"], "title": v["title"], "chapters": []}
        for c in v["chapters"]:
            ch_seq += 1
            vmeta["chapters"].append({
                "id": f"ch{ch_seq:03d}",
                "file": c["file"],
                "title": c["title"],
                "wordCount": c["wordCount"],
                "summary": c["summary"],
                "imageCount": c["imageCount"],
                "dynasty": None,
            })
        meta_volumes.append(vmeta)

    meta = {
        "book": {
            "title": "中国通史 五卷本",
            "subtitle": "中国社会科学院撰稿 · 卜宪群主编",
            "volumes": len(volumes),
            "chapters": ch_seq,
            "totalChars": total_chars,
            "totalImages": total_imgs,
        },
        "volumes": meta_volumes,
    }
    (out_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

    # 输出分卷正文 volN.json（章节 id 全书连续编号）
    ch_seq = 0
    for v in volumes:
        for c in v["chapters"]:
            ch_seq += 1
            c["id"] = f"ch{ch_seq:03d}"
            c.pop("images", None)
        payload = {"volume": {"id": v["id"], "title": v["title"]}, "chapters": v["chapters"]}
        (out_dir / f"vol{v['id']}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"卷数: {len(volumes)}")
    for v in volumes:
        print(f"  卷{v['id']} {v['title']}: {len(v['chapters'])} 章, "
              f"{sum(c['wordCount'] for c in v['chapters'])} 字, "
              f"{sum(c['imageCount'] for c in v['chapters'])} 图")
    print(f"总章数: {ch_seq} | 总字数: {total_chars} | 引用图片: {total_imgs}")
    print("输出: data/meta.json, data/vol1..5.json")


if __name__ == "__main__":
    main()
