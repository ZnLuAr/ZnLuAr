# 右半区轮播与统计页设计

> 定位：动态版右半区 `TECH ARSENAL` ↔ `CODING INSIGHTS` 双页轮换的时间线、降级策略与统计页排版。

## 双页结构

动态版右半区在两页之间轮换：

- `TECH ARSENAL`：标题 + 副标题 `things i sorta know · stuff i tinker with` + 技术栈图标矩阵（矩阵设计见 [tech-icons](tech-icons.md)）。
- `CODING INSIGHTS`：标题 + 副标题（区间 · UPDATED 日期）+ WakaTime 编码统计（数据链见 [wakatime-data](wakatime-data.md)）。

两页标题共用同一光学中心 `(980,118)`，切换时无位移跳动。两页结构对称：各带一条 13px 副标题（Arsenal 页 y=150，统计页 y=156），Arsenal 副标题在静态版中同样保留。轮播只作用于右半区组；立方体、网格、地面和相机固定，与 400s 旋转互不干扰。

## 时间线

16s 保持 + 1s 淡出 + 0.8s 空窗 + 1s 淡入，两页对称重复，周期 `2×(16+1+0.8+1)=37.6s`。每个动画 9 个关键点，keyTimes `0;0.425532;0.452128;0.473404;0.5;0.925532;0.952128;0.973404;1`，values 首尾一致形成闭环。

选择"先淡出、留空窗、再淡入"而不做交叉淡化：交叉时两页以半透明叠加，等宽字体的统计数字与图标会短暂重影；空窗轮换保证任一时刻只有一页可见，切换节奏也更从容。空窗期间右半区只剩常驻的淡网格装饰，不出现黑块或占位骨架。

四个轮播包裹层均为纯 SMIL opacity 动画，无 JavaScript、按钮或横向滑动。

## 静态降级

静态版（`hero-light.svg` / `hero-dark.svg`）只渲染 `TECH ARSENAL`，不含 `CODING INSIGHTS` 组。理由：静态版服务 reduced-motion 与 `<img>` 兜底场景，轮换本身就是动态行为；技术栈矩阵是常青内容，统计页数字则随快照变化，把静态版绑定在更稳定的一页。

README 侧的 `<picture>` 将动态源限制在 `prefers-reduced-motion: no-preference` 的 `<source>` 中；减少动态效果、媒体查询不受支持或 source 被过滤时回退到静态 source 或 `<img>`。

## 统计页排版

当前坐标（改这些常量只动 `scripts/hero/svg_renderer.py` 的 insights 段，然后正式构建 + 截图复核）：

| 元素 | 位置 |
|---|---|
| 标题 `CODING INSIGHTS` | `(980,118)`，30px、字距 6（与 `TECH ARSENAL` 共用 `heading_svg()`，两页字号一致避免轮换跳变） |
| 副标题（区间 · UPDATED 日期） | y=156，13px |
| TOTAL CODING TIME / DAILY AVERAGE | label y=232，数值 y=276（34px），x=700/1260 居中 |
| 组标签 LANGUAGES / EDITORS | y=352，15px |
| LANGUAGES 6 行 | 名称 x=420、条 x=580、最大条长 380、百分比右对齐 x=1040；行 y=400 起、步距 66 |
| EDITORS 3 行 | 名称 x=1090、条 x=1262、最大条长 188、百分比 x=1520；行 y=400 起、步距 66 |
| OPERATING SYSTEM 标签 | y=600 |
| OPERATING SYSTEM 3 行 | 同右列几何；行 y=648 起、步距 66 |

行名称 20px、百分比 16px（opacity 0.92）、条形高 10px；条长按各列最大百分比归一化（列内榜首满条）。全部继承主题 `stack`/`stackA` 墨色与等宽字体栈。

## 固定槽位与占位

三榜渲染固定数量的行——语言 6、编辑器 3、系统 3。真实条目不足时，空槽在名称列与百分比列各渲染一个低透明度（0.3）`-`，不画条形。这样应对两类场景：近七天没碰电脑（榜单接近全空）、只做文档工作（语言榜残缺）。槽位上限（`MAX_LANGUAGES` 等）同时约束快照 schema 与渲染行数，单一来源在 `scripts/hero/wakatime.py`。
