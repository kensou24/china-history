# 疆域时空地图 · 设计文档

日期：2026-08-01
状态：已获用户批准（独立地图页 · 全部范围一次做：数据管线 + 地图页 + 时间刷 + 首页联动）

## 背景与目标

站点现有"时间"维度导航（朝代时间轴）已成熟，缺"空间"维度。本功能新增**疆域时空地图**：
中国底图 + 历代政权疆域色块，支持按朝代浏览、按年份拖动（同代并立政权同图可见，
如 1100 年北宋+辽+西夏），并与首页时间轴双向联动。这是站点的第二支柱功能。

约束沿用项目既有原则：无后端、纯静态托管、数据全部经管线预生成、桌面深度阅读优先。

## 数据源与许可（已查证）

| 数据 | 许可 | 用途 |
|---|---|---|
| [Cliopatria](https://github.com/Seshat-Global-History-Databank/cliopatria)（[Zenodo](https://zenodo.org/records/14714684)，[Nature 论文](https://www.nature.com/articles/s41597-025-04516-9)） | CC BY 4.0（署名即可再分发） | 历代政权疆域多边形。约 14K 记录，字段：Name / geometry(EPSG:4326) / Area / Type(POLITY\|RELATION) / **FromYear / ToYear 年份区间** / Wikipedia / Wikidata / SeshatID |
| [Natural Earth](https://www.naturalearthdata.com/) | 公有领域 | 底图：海岸线、黄河长江等大河 |
| `data/dynasties.json` | 自有 | 25 朝代（id/name/start/end/color/chapterIds） |

- 排除项：CHGIS（仅限学术研究，**明确禁止再分发**，数据需进公开仓库故不可用）；
  aourednik/historical-basemaps（GPL-3.0 会传染仓库许可，且中国部分粒度粗）
- Cliopatria 署名写在地图页角落 + README；页面标注"疆域为学术数据集近似示意"
- 原始数据手动下载到 `raw/`（不入库，.gitignore）；`scripts/map.py` 检测不到时打印下载指引

## 数据管线（`scripts/map.py`）

### 数据流

```
raw/cliopatria.geojson（不入库）+ raw/naturalearth（不入库）
data/dynasties.json + scripts/map_dynasties.json（新增映射表，入库，人工校订）
        ↓ scripts/map.py
data/map.json（≤1.2MB，可再生成，不入库）→ sync_web_assets.py → web/public/data/
data/map_preview/*.svg（每朝代预览图，供人工校订，不入库）
```

### 关键决策：沿用 Cliopatria 区间模型，不存逐年快照

每条 shape = 一个政权的一段时期（from/to）。前端查"某年疆域" =
`shapes.filter(s => s.from <= y && y <= s.to)`（数百条，微秒级），无快照冗余存储。
`changeYears` 为全部 from/to 边界的排序去重，供时间刷吸附。

### map.json 结构

```jsonc
{
  "viewBox": "0 0 1000 820",               // 平面坐标系，由管线按烘焙后内容边界自动计算
  "basemap": {
    "coast": "M…",                          // 海岸线（一条 path）
    "rivers": ["M…"],                       // 黄河、长江等大河
    "cities": [{ "n": "西安", "x": 0, "y": 0 }]  // 5-8 个手选现代城市参考点（西安/洛阳/北京/南京/成都等）
  },
  "changeYears": [-1600, -1046, /* … */ 2024],
  "shapes": [
    { "n": "唐", "dyn": "tang", "from": 618, "to": 907, "d": "M…", "label": [523, 410] },
    { "n": "吐蕃", "dyn": null, "from": 618, "to": 842, "d": "M…", "label": [180, 430] }
  ],
  "dynastyMap": { "tang": { "clio": "Tang dynasty", "year": 669 } },
  "unmapped": ["prehistoric", "xia"]
}
```

- 多边形只存几何与朝代 id；**颜色由前端从 dynasties.json 取**（配色改动不用重跑管线）；
  `dyn: null` 为中立政权，前端统一中性色
- `label` 用 shapely pole-of-inaccessibility 算"最内点"，保证名称落在疆域内
- 坐标量化为整数，直接是 SVG path 字符串；**前端零投影、零 GeoJSON 解析**

### 朝代映射表（`scripts/map_dynasties.json`）

- 单一政权朝代（秦/汉/唐/北宋/辽/西夏/金/元/明/清…）→ 1 个 Cliopatria 实体 + 代表年
- **时期朝代**（春秋/战国/三国/南北朝/五代十国）→ 代表年 + 该年多个实体，
  这些实体的 shape `dyn` 标同一朝代 id（选中"三国"时魏蜀吴一起高亮，前端无特殊逻辑）
- 疆域无考/数据缺失（prehistoric、xia 已定；xin 等待探查确认）→ `unmapped`，走降级态
- Cliopatria 实体名（如 `Northern Song`/`Liao`）以实施第一步的数据探查结果为准

### 管线步骤

1. **探查**：按中国区域 bbox 粗筛，打印全部政权名+年份区间 → 供填映射表
2. **简化+烘焙**：shapely `simplify()` 抽稀 → Albers 中国投影（标准纬线 25°N/47°N，
   中央经线 105°E，pyproj）→ 坐标量化整数 → SVG path
3. **底图（已拍板）：不画现代国界线**，只保留海岸线+大河+现代城市参考点。
   理由：① 规避现代边界画法敏感（Natural Earth 国界立场与我国标准地图不一致）；
   ② 视觉即"宣纸古地图"，与站点纸色主题一体
4. **校订走查**：每朝代导出预览 SVG（底图+该朝高亮+同代淡显），逐朝人工核对后改表重跑
5. **校验**：`validate.py` 新增 map 规则——25 朝代映射完整性、shapes 区间与朝代年表自洽、
   path 非空、文件大小预算 1.2MB、basemap 字段齐全

新增依赖：`shapely` + `pyproj`（requirements.txt；不引 geopandas）。

### 风险与回退

若探查发现 Cliopatria 中国政权粒度不足（如缺新朝、某朝区间空洞）：映射表标 unmapped
走降级态即可，不阻塞整体；极端情况再评估手工简化多边形补绘（本设计不预做）。

## 前端架构

### 路由与数据

- 新路由 `/map` → `MapView.vue`，**路由级分包懒加载**（map.json 只在进地图页拉取）；
  顶栏导航加第三项「疆域地图」
- `composables/useMapData.js`：与 useMeta 同模式（模块级缓存、并发去重、`cache: 'no-cache'`），
  暴露 `activeShapes(year)` / `shapesByDynasty(dynId)` / `yearOf(dynId)`

### 组件拆分

| 组件 | 职责 | 输入 | 输出 |
|---|---|---|---|
| `MapView.vue` | 页面编排 + **唯一状态源**：加载/错误态、朝代 chips 行、URL 同步、播放定时器 | route query | — |
| `AtlasMap.vue` | 纯 SVG 地图本体：basemap + 政权色块 + 名称标签；缩放/平移/惯性；选中飞行 | `shapes` `selectedId` `focusKey` | `select(dynId)` |
| `MapTimeBar.vue` | 底部时间刷：年份刻度、拖拽吸附 changeYears、播放/暂停 | `years` `year` `playing` | `update:year` `toggle-play` |
| `MapDynastyCard.vue` | 选中朝代信息卡：名称/起讫/章节列表/「在时间轴查看」/降级文案 | `dynasty` `chapters` `mapped` | 路由跳转 |

职责边界：

- **MapView 持有全部状态**（`mode / year / selectedDynasty`），子组件全受控，单一真相源
- **唯一例外：AtlasMap 相机自治**（view/targetView 分离、wheel 指针锚定、pinch 以捏合起点为基准，
  与 DynastyTimeline 同模式）；父级经 `focusKey` 变化触发 `flyTo(bbox)`（defineExpose）
- **命中检测沿用时间轴方案**：拖拽平移要 setPointerCapture，会吞 path 自身事件——
  pointerdown 记录目标与坐标，pointerup 位移 <5px 视为点击按 down 时目标命中，
  不给 path 单独绑事件
- 朝代 chips 行逻辑薄（25 个横滚按钮），内联在 MapView 模板，不单列组件

### 布局

`app-main` 复用 `read-wide` 1400px 宽版模式；≥1100px = 顶 chips + 中央地图 +
右侧 sticky 信息卡 + 底部时间刷；<1100px = chips 横滚、信息卡改底部浮层、时间刷保留（触控可拖）。

## 交互与状态机

### 双模式

| 用户动作 | 模式 | 表现 |
|---|---|---|
| 点 chips / 点有朝代的政权 | `dynasty` | year 跳到代表年；镜头飞向该朝 bbox；该朝高亮（朝代色），同代政权中性色淡显；右侧信息卡 |
| 拖时间刷 / 播放 | `year` | 清除选中；活跃政权平权显示（有朝代用朝代色、无朝代中性色，同档饱和度） |
| 点中立政权 | 不切模式 | MapDynastyCard 通用态：名称+年份区间，无章节列表 |

### URL 同步与默认态

- dynasty 模式 → `/#/map?d=tang`；year 模式 → `/#/map?y=1100`；
  状态变化走 `router.replace`（不污染历史）；进入读 query 初始化（d 优先于 y）
- 非法 query 静默回落默认态：**有阅读记录 → dynasty 模式选中 lastRead 章所属朝代**；
  无记录 → `year=-221`（秦统一）

### 首页时间轴双向联动

- 时间轴选中朝代浮层加「在疆域地图查看」→ `/map?d=xx`
- 地图信息卡加「在时间轴查看」→ `/#/?d=xx`（hash 路由），DynastyTimeline 复用现有搜索飞行机制
  （matchedDynasty）定位选中，不占搜索框
- 由此批次 2 的"时间轴选中状态同步 URL"以最小形态落地，原批次 2 清单相应收敛

### 动效（遵循仓库约定）

- 疆域随年份变化：shape 以 `n+from` 为 key，进出场 200ms opacity；**不做 path morph**
- 镜头飞行：fitBounds 500ms easeOutCubic，lerp view→targetView；reduced-motion 瞬时
- 播放：1.2s/步进到底自停；reduced-motion 禁用自动播放、按钮变单步
- 相机：wheel 指针锚定缩放、拖拽惯性、双击复位、触控 pinch（pinchView 基准防发散）
- hover 一律 `@media (hover: hover)`；reduced-motion JS+CSS 双保险；配色走 CSS 变量四主题通读

## 边界与错误处理

- map.json 加载失败 → 错误盒 + 重试（同现有模式）
- unmapped 朝代选中 → 卡片"该时期疆域尚无定论" + 章节列表（功能不死）
- 某年无任何 shape（数据空洞，防御）→ 只显示底图 + 提示
- 时间刷稀疏段（史前~秦）→ 吸附最近有数据年

## 验证（无测试框架，三层）

1. **管线**：`validate.py` 新规则全过；25 朝预览 SVG 逐朝人工走查，
   重点核对 1100 年北宋+辽+西夏并立、三国、南北朝
2. **构建**：`npm run build` 通过
3. **dev 走查**：朝代切换 / 时期多政权高亮 / 时间刷吸附 / 播放 / URL 刷新还原 /
   双向联动 / 窄屏 / reduced-motion / 四主题

## 明确不做（YAGNI）

- 在线瓦片 / Leaflet / 任何在线地图服务（违反纯静态约束）
- path morph 动画、现代国界线、地图迷你导航
- 人物/事件图层、章内地名标注（可作为后续独立方向）

## 后续阶段（本轮不实现）

- 章内地名小地图（阅读增强，点数据集，独立管线）
- 时间轴完整 URL 状态机（批次 2 剩余项）
- 人物/事件图层（需新数据源，单独立项）
- 地图迷你导航、疆域面积 readout 等打磨

## 实施顺序提示（细化见实现计划）

数据探查 → 管线 + 映射表校订 → validate → MapView 骨架 + useMapData →
AtlasMap 渲染 + 相机 → chips + 信息卡 → 时间刷 + 播放 → URL 同步 → 首页联动 → 走查收尾
