# 项目说明

> 定位：这个仓库是什么、目录怎么分工、数据怎么流动。操作步骤见 [usage](usage.md)，设计取舍见 [design/](design/)。

## 概述

最终产品是 GitHub Profile 的双语 README（`README.md` / `README.zh-CN.md`），Hero 是其中一个内容块。仓库本身是这个 README 的生成器：Python 在构建期生成自包含的静态与动态 SVG，产物被 README 通过 `<picture>` 引用。

核心架构约束：动态 SVG 只包含预先计算的投影和 SMIL 插值，不含脚本、CSS、外部图片、外部字体或运行时几何计算。GitHub 经 camo 代理展示图片、不执行 JavaScript，这是所有渲染决策的前提。

当前分支 `master`。

## 目录与职责

```text
ZnLuAr/
├── README.md / README.zh-CN.md     # 双语主页，<picture> 引用同一组 Hero
├── _wakatime_token.local.example   # WakaTime token 示例；复制为 _wakatime_token.local 使用（gitignore）
├── assets/                         # 正式产物，GitHub README 直接引用
│   ├── hero/                       # light/dark × 静态/motion 四份 SVG
│   └── icons/                      # 技术栈 SVG、上游许可证、SOURCES.md
│       └── sources/                # Icons8 原始 100px PNG 与经核验的派生矢量源
├── gen/hero/                       # 纳入版本管理的持久化生成状态，不是缓存
│   ├── scene.json                  # adjust_scene.py 维护的场景状态
│   ├── themes.json                 # build_themes.py 生成的双主题变量
│   └── wakatime.json               # WakaTime 统计快照（真实数据）
├── scripts/
│   ├── icon_manifest.py            # 33 项图标顺序、来源及待核验声明（单一来源）
│   ├── fetch_tech_arsenal.py       # 抓取、验证并规范化技术栈 SVG
│   ├── fetch_wakatime.py           # 抓取 WakaTime 统计写入 wakatime.json（默认 dry-run）
│   ├── adjust_scene.py             # pitch/yaw/zoom/motion-speed 中文 CLI
│   ├── build_themes.py             # 生成主题 JSON，并重建 SVG
│   ├── build_hero.py               # 从 JSON、本地图标与快照构建或检查 SVG
│   ├── blender_calibrate.py        # Blender 投影校准
│   └── hero/                       # 渲染实现
│       ├── svg_renderer.py         # 唯一 SVG 渲染实现
│       ├── geometry.py             # 投影、反投影、立方体与网格几何
│       ├── scene.py                # 持久化、校验、相机补偿和网格 LOD
│       ├── motion.py               # 相机空间三轴旋转与确定性投影采样
│       ├── stack.py                # 本地图标安全加载及矩阵布局
│       ├── wakatime.py             # 快照 schema 校验、加载与渲染视图投影
│       └── color.py                # 颜色混合与 RGB 反色
├── preview/
│   ├── hero.html                   # Hero 块预览壳，无 JavaScript
│   └── icons.html                  # 图标双主题与来源预览
├── tests/                          # 场景、几何、产物、README、图标链与 WakaTime 链测试
├── docs/                           # 本文档族
│   ├── architecture.md             # 项目说明（本文件）
│   ├── usage.md                    # 使用说明
│   ├── CHANGELOG.md                # 版本记录
│   └── design/                     # 设计决策：场景渲染 / 轮播 / 数据链 / 图标链
├── .github/workflows/ci.yml        # 轻量 CI：单元测试 + 构建产物同步检查
├── .github/workflows/update-wakatime-stats.yml  # WakaTime 定时同步：抓取 → 重建 → 有变化才提交
└── references/                     # 历史验证截图（本地存档，已 gitignore）
```

`gen/` 是纳入版本管理的持久化生成状态，不是可随意删除的缓存。`assets/hero/` 保留正式产物，因为 GitHub README 直接引用它们。`hero-light.svg` / `hero-dark.svg` 是静态降级，对应 `*-motion.svg` 是动态版本。没有第二套渲染实现。

## 生成链与数据流

三条数据链按来源拆分，不复用笼统的前缀：

```text
gen/hero/scene.json + themes.json + wakatime.json + assets/icons/
    → build_hero.py → assets/hero/ 四份 SVG → README <picture> / preview/hero.html

icon_manifest.py → fetch_tech_arsenal.py → assets/icons/ + SOURCES.md + preview/icons.html

WakaTime API → fetch_wakatime.py → gen/hero/wakatime.json
```

- `build_hero.expected_assets()` 读取并验证本地图标，再传给无文件系统访问的 `render_hero()`；普通构建、`--check`、主题重建和场景调整都经过该入口，本地图标或快照变化会使相应产物被判定为过期。
- 动态版右半区在快照存在时渲染 `TECH ARSENAL` ↔ `CODING INSIGHTS` 双页轮播；静态降级版只渲染 `TECH ARSENAL`。

## README 引用结构

```html
<picture>
  <source media="(prefers-color-scheme: dark) and (prefers-reduced-motion: no-preference)" srcset="assets/hero/hero-dark-motion.svg">
  <source media="(prefers-color-scheme: light) and (prefers-reduced-motion: no-preference)" srcset="assets/hero/hero-light-motion.svg">
  <source media="(prefers-color-scheme: dark)" srcset="assets/hero/hero-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/hero/hero-light.svg">
  <img src="assets/hero/hero-light.svg" alt="..." width="100%">
</picture>
```

每份 SVG 都有 `width=1600`、`height=900`、`viewBox`、标题和描述；根 `desc` 与双语 README `alt` 列出实际展示的 29 项技术名称。HTML 预览无 JavaScript，直接 `file://` 打开；预览中的 light/dark 块固定各自主题。

## 设计文档索引

| 文档 | 内容 |
|---|---|
| [design/scene-rendering.md](design/scene-rendering.md) | 场景坐标约定、相机调整不变量、三轴动态、网格 LOD、光照与曝光、当前参数 |
| [design/carousel.md](design/carousel.md) | 轮播时间线与降级策略、统计页排版、固定槽位占位 |
| [design/wakatime-data.md](design/wakatime-data.md) | 凭据模型、快照 schema、抓取规则与隐私边界 |
| [design/tech-icons.md](design/tech-icons.md) | 图标来源、安全规范化、专用转换、矩阵布局、许可证 |

版本演进记录见 [CHANGELOG](CHANGELOG.md)。

## 测试与 CI

`tests/` 覆盖相机补偿、LOD、静态几何、动态刚体旋转、闭环、双主题一致性、SMIL 结构、静态降级、README 契约、图标链（来源固定、安全拒绝、专用转换、许可证）、WakaTime 链（schema 封闭、视图投影、抓取映射、占位槽渲染、轮播结构）与 workflow 契约（凭据边界、提交范围），共 93 项。

CI（`.github/workflows/ci.yml`）在 push / PR 时跑全部测试和 `build_hero.py --check`（产物与源码同步，防"改了生成器忘重建"）。WakaTime 抓取需要凭据、Blender 校准需要安装，均不进 CI；定时抓取走 `update-wakatime-stats.yml`（设计见 [design/wakatime-data.md](design/wakatime-data.md) 的"定时同步"节），其同步提交反过来触发 CI 复验。真实 GitHub/camo/SMIL/移动端的发布验证状态见 CHANGELOG 的 Unreleased 段。
