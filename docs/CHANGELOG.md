# CHANGELOG

只记录决定性更新（结构性、架构级变化）；参数微调与试验回退不在此列，设计细节见 `docs/design/`。版本号沿用 Hero 视觉版本（vN），新版本在前。

## Unreleased

- WakaTime 数据链真实化：OAuth 授权换得 access token，快照替换为真实统计。
- 凭据精简为单文件 `_wakatime_token.local`，删除 app 凭据与 refresh token 两个本地文件。
- 文档重构：交接文档拆分为 docs/ 项目说明、使用说明、CHANGELOG 与设计决策四份。
- 新增轻量 CI：单元测试 + 构建产物同步检查。
- 新增 WakaTime 定时同步 workflow：每日抓取统计并重建 Hero，有变化才以 bot 身份提交。
- 仓库代码以 MIT License 发布；第三方图标资产保留各自上游许可证（见 design/tech-icons.md）。
- `TECH ARSENAL` 页新增副标题 `things i sorta know · stuff i tinker with`，与统计页副标题形成对称结构。

## v54（2026-11-21）

- 统计页三榜改为固定槽位（语言 6、编辑器 3、系统 3），空槽渲染 `-` 占位，应对无编码数据的周。
- 页标题与行名称加大、内容块纵向重排。

## v53

- 轮播定稿为空窗轮换（先淡出、留空窗、再淡入），取代交叉淡化。
- 语言榜在抓取层过滤归并类别 `Other` 并从更低位补足。

## v52

- 数据链按来源拆分为 `fetch_tech_arsenal.py` 与 `fetch_wakatime.py`，WakaTime 快照落地。
- 动态版右半区加入 `TECH ARSENAL` ↔ `CODING INSIGHTS` 双页轮播。

## v47

- 技术栈图标矩阵接入 Hero 右半区，定版 128px、上下宽中间窄的 8–7–6–8 布局。

## v43

- 立方体加入三轴缓慢旋转，动态版确立"构建期采样 + SMIL 插值"形态。

## v42

- 静态构图与光照基线：斜向俯视网格、左侧超画框金属体、环形曝光、双主题同源。
