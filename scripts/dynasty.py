#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dynasty.py — 朝代时间轴数据构建。

- 内置权威朝代序列表（起止年份 / 颜色 / 别名）
- 100 章 → 朝代映射（按章节标题驱动，脚本自动生成 ch id 并校验）
- 校验：每章恰好映射一个朝代、朝代不空

输出：data/dynasties.json
用法：python3 scripts/dynasty.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# 朝代序列表（年份为公元前负数）
DYNASTIES = [
    {"id": "prehistoric", "name": "史前", "start": -3000, "end": -2070,
     "color": "#8d8d8d", "alias": ["远古", "石器时代", "上古"]},
    {"id": "xia", "name": "夏", "start": -2070, "end": -1600,
     "color": "#b58900", "alias": ["夏朝", "夏代", "夏王朝"]},
    {"id": "shang", "name": "商", "start": -1600, "end": -1046,
     "color": "#cb4b16", "alias": ["商朝", "殷商", "商代", "殷"]},
    {"id": "west-zhou", "name": "西周", "start": -1046, "end": -771,
     "color": "#dc322f", "alias": ["西周", "周朝", "周代", "周王室"]},
    {"id": "spring-autumn", "name": "春秋", "start": -770, "end": -476,
     "color": "#d33682", "alias": ["春秋"]},
    {"id": "warring-states", "name": "战国", "start": -475, "end": -221,
     "color": "#6c71c4", "alias": ["战国", "列国", "诸子百家"]},
    {"id": "qin", "name": "秦", "start": -221, "end": -207,
     "color": "#2aa198", "alias": ["秦朝", "秦代", "秦始皇", "楚汉"]},
    {"id": "west-han", "name": "西汉", "start": -202, "end": 9,
     "color": "#859900", "alias": ["西汉", "汉朝", "汉代", "汉武", "文景", "昭宣"]},
    {"id": "xin", "name": "新", "start": 9, "end": 23,
     "color": "#93a1a1", "alias": ["王莽", "新朝", "新莽"]},
    {"id": "east-han", "name": "东汉", "start": 25, "end": 220,
     "color": "#b58900", "alias": ["东汉", "光武", "党锢"]},
    {"id": "three-kingdoms", "name": "三国", "start": 220, "end": 280,
     "color": "#cb4b16", "alias": ["三国", "魏", "蜀", "吴", "诸葛亮"]},
    {"id": "west-jin", "name": "西晋", "start": 265, "end": 316,
     "color": "#dc322f", "alias": ["西晋", "晋朝", "魏晋"]},
    {"id": "east-jin", "name": "东晋", "start": 317, "end": 420,
     "color": "#d33682", "alias": ["东晋", "门阀", "魏晋佛教"]},
    {"id": "north-south", "name": "南北朝", "start": 420, "end": 589,
     "color": "#6c71c4", "alias": ["南北朝", "南朝", "北朝", "梁武帝", "北魏", "陈朝"]},
    {"id": "sui", "name": "隋", "start": 581, "end": 618,
     "color": "#2aa198", "alias": ["隋", "隋朝", "炀帝"]},
    {"id": "tang", "name": "唐", "start": 618, "end": 907,
     "color": "#859900", "alias": ["唐", "唐朝", "唐代", "贞观", "武则天", "安史", "吐蕃", "敦煌"]},
    {"id": "five-dynasties", "name": "五代十国", "start": 907, "end": 960,
     "color": "#93a1a1", "alias": ["五代", "五代十国"]},
    {"id": "north-song", "name": "北宋", "start": 960, "end": 1127,
     "color": "#268bd2", "alias": ["北宋", "宋太祖", "澶渊", "王安石", "靖康", "东京"]},
    {"id": "liao", "name": "辽", "start": 916, "end": 1125,
     "color": "#6c71c4", "alias": ["辽", "契丹", "西辽", "辽金"]},
    {"id": "west-xia", "name": "西夏", "start": 1038, "end": 1227,
     "color": "#cb4b16", "alias": ["西夏"]},
    {"id": "jin", "name": "金", "start": 1115, "end": 1234,
     "color": "#d33682", "alias": ["金", "金朝", "完颜阿骨打", "宋金"]},
    {"id": "south-song", "name": "南宋", "start": 1127, "end": 1279,
     "color": "#b58900", "alias": ["南宋", "偏安", "宋金和战"]},
    {"id": "yuan", "name": "元", "start": 1271, "end": 1368,
     "color": "#2aa198", "alias": ["元", "元朝", "蒙古", "忽必烈", "八思巴", "马可·波罗"]},
    {"id": "ming", "name": "明", "start": 1368, "end": 1644,
     "color": "#859900", "alias": ["明", "明朝", "明代", "明太祖", "永乐", "郑和", "张居正", "崇祯", "王阳明"]},
    {"id": "qing", "name": "清", "start": 1644, "end": 1912,
     "color": "#268bd2", "alias": ["清", "清朝", "清代", "康熙", "雍正", "乾隆", "鸦片", "太平天国", "甲午"]},
]

# 章节标题 → 朝代（按卷分组，标题驱动，脚本自动映射 ch id）
TITLE_DYNASTY = {
    # 卷1 史前→战国
    "中华先祖": "prehistoric", "农业起源": "prehistoric", "文明起源": "prehistoric",
    "邦国时代": "prehistoric", "古史传说": "prehistoric",
    "夏王朝觅踪": "xia",
    "殷商兴亡": "shang", "商代文明": "shang",
    "武王克商": "west-zhou", "周公摄政": "west-zhou", "周王室的衰落": "west-zhou",
    "春秋争霸": "spring-autumn", "孔子": "spring-autumn",
    "列国变法": "warring-states", "战国七雄": "warring-states", "诸子百家": "warring-states",
    # 卷2 战国末→南北朝
    "秦国崛起": "warring-states", "秦始皇统一中国": "qin", "楚汉战争": "qin",
    "郡国并行": "west-han", "文景之治": "west-han", "汉武帝": "west-han",
    "两汉经学": "west-han", "昭宣政治": "west-han", "丝绸之路": "west-han",
    "王莽改制": "xin",
    "光武中兴": "east-han", "清议与党锢": "east-han", "黄巾起义": "east-han",
    "三国鼎立": "three-kingdoms", "诸葛亮治蜀": "three-kingdoms",
    "西晋统一": "west-jin", "魏晋风度": "west-jin",
    "门阀政治": "east-jin", "魏晋佛教": "east-jin",
    "梁武帝治国": "north-south", "北魏孝文帝改革": "north-south",
    "北周武帝": "north-south", "陈朝兴亡": "north-south",
    # 卷3 隋唐五代两宋
    "再造统一": "sui", "炀帝功过": "sui",
    "贞观之治": "tang", "武则天": "tang", "开天盛世": "tang", "安史之乱": "tang",
    "中晚唐的困局": "tang", "世界都会长安": "tang", "吐蕃兴衰": "tang",
    "敦煌": "tang", "唐朝对外文化交流": "tang", "唐代宗教": "tang",
    "五代十国": "five-dynasties",
    "宋太祖": "north-song", "澶渊之盟": "north-song",
    "与士大夫共治天下": "north-song", "王安石变法": "north-song", "靖康之难": "north-song",
    "东京梦华": "north-song", "宋代新儒学": "north-song", "宋代文化": "north-song",
    "宋金和战": "south-song", "偏安东南": "south-song",
    # 卷4 辽西夏金元
    "契丹兴起": "liao", "西辽建国": "liao", "辽金文化": "liao",
    "完颜阿骨打": "jin", "金朝兴亡": "jin",
    "西夏兴亡": "west-xia",
    "蒙古兴起": "yuan", "忽必烈大帝": "yuan", "两都巡幸": "yuan",
    "大元帝师八思巴": "yuan", "海上丝绸之路": "yuan", "马可·波罗与中国": "yuan",
    "元顺帝妥懽帖睦尔": "yuan",
    # 卷5 明清
    "明太祖朱元璋": "ming", "永乐迁都": "ming", "郑和下西洋": "ming",
    "内阁制度": "ming", "土木堡之变": "ming", "王阳明心学": "ming",
    "海疆与互市": "ming", "张居正改革": "ming", "耶稣会士来华": "ming",
    "江南市镇": "ming", "白银资本": "ming", "崇祯帝": "ming", "明清更迭": "ming",
    "清王朝的稳固": "qing", "统一大业": "qing", "收复台湾": "qing",
    "军机处": "qing", "摊丁入亩": "qing", "文治与文字狱": "qing",
    "鸦片战争": "qing", "太平天国": "qing", "自强运动": "qing",
    "甲午战争": "qing", "维新与革命": "qing", "帝制的终结": "qing",
}


def main():
    meta = json.loads((DATA / "meta.json").read_text(encoding="utf-8"))
    chapters = [c for v in meta["volumes"] for c in v["chapters"]]

    # 标题驱动生成 ch id → 朝代
    chapter_dynasty = {}
    unmatched = []
    for c in chapters:
        dy = TITLE_DYNASTY.get(c["title"])
        if dy is None:
            unmatched.append(c["title"])
        chapter_dynasty[c["id"]] = dy

    if unmatched:
        print("无映射的章节:", unmatched, file=sys.stderr)
        return 1
    valid_ids = {d["id"] for d in DYNASTIES}
    bad = [cid for cid, dy in chapter_dynasty.items() if dy not in valid_ids]
    if bad:
        print("非法朝代引用:", bad, file=sys.stderr)
        return 1

    # 组装 dynasties.json
    dyn_list = []
    for d in DYNASTIES:
        chs = sorted((cid for cid, dy in chapter_dynasty.items() if dy == d["id"]),
                     key=lambda c: int(c[2:]))
        dyn_list.append({
            "id": d["id"], "name": d["name"], "start": d["start"], "end": d["end"],
            "color": d["color"], "alias": d["alias"], "chapterIds": chs,
        })

    payload = {"dynasties": dyn_list, "chapterDynasty": chapter_dynasty}
    (DATA / "dynasties.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    # 回写 meta.json：为每章填充 dynasty 字段
    for v in meta["volumes"]:
        for c in v["chapters"]:
            c["dynasty"] = chapter_dynasty.get(c["id"])
    meta["book"]["dynasties"] = len(dyn_list)
    (DATA / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

    # 统计输出
    id_to_title = {c["id"]: c["title"] for c in chapters}
    total = 0
    print("朝代数:", len(dyn_list))
    for d in dyn_list:
        titles = "、".join(id_to_title[cid] for cid in d["chapterIds"])
        print(f"  {d['name']:<6} {d['start']}~{d['end']}  {len(d['chapterIds'])} 章  {titles}")
        total += len(d["chapterIds"])
    print("映射章节总数:", total, "| 输出: data/dynasties.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
