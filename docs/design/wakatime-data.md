# WakaTime 数据链设计

> 定位：编码统计从 API 到 Hero 的链路——凭据模型、快照 schema、抓取规则与隐私边界。

## 凭据模型

唯一凭据文件是仓库根的 `_wakatime_token.local`（已 gitignore，示例见 `_wakatime_token.local.example`），或环境变量 `WAKATIME_OAUTH_TOKEN`。内容是 OAuth access token（`waka_tok_` 前缀，read_stats 权限）。token 只在抓取时读取，永不进入仓库、快照或 SVG。

不保存 refresh token 和 OAuth app 凭据：授权码流程签发的 access token 有效期 100 年，refresh 流程在本场景永远不会触发；app 凭据只在重新授权时短暂使用，无常驻价值（重新授权步骤见 [usage](../usage.md)）。

实测知识（2026-11-20）：

- 账号 Secret API key（`waka_sec_` 前缀，wakatime.com/api-keys 网页创建）请求 stats 端点返回 401，只能上报；`load_token()` 检测到该前缀直接拒绝。拦截范围是 `waka_sec_` 而非整个 `waka_`，以免误伤 `waka_tok_`。
- OAuth app 可在 WakaTime 网页直接创建（App ID + App Secret）；redirect_uri 在授权与换 token 两步必须完全一致。
- 换 token 端点是 `POST https://wakatime.com/oauth/token`（不带 `/api/v1`，带则 404）。
- 每 app 每用户限 8 个活跃 token（超限自动吊销最旧的）、每小时限 10 个新 token，因此不要频繁重新授权。

## 快照 schema

`gen/hero/wakatime.json`（`scripts/hero/wakatime.py` 校验）：

- `placeholder`（布尔）、`fetched_at`、`range`（last_7_days / last_30_days）。
- `total` 与 `daily_average`：仅 seconds/text，必须为正。
- `languages` ≤6、`editors` ≤3、`operating_systems` ≤3；条目仅 name/percent/text，percent ∈ (0,100]。

字段集封闭：**不存 Projects**（隐私最小化，项目名可能泄露未公开仓库），也不存原始 API 响应。当前快照为真实数据（2026-11-20 起非占位）。

## 抓取规则

`scripts/fetch_wakatime.py`，`GET https://wakatime.com/api/v1/users/current/stats/{range}` Bearer 认证：

- `is_up_to_date=false` 或区间总时长为 0 时拒绝，保留现有快照——统计页宁可数字略旧，不出现空页或半成品。
- `daily_average` 缺失时按 total/天数兜底。
- 语言榜在抓取层过滤归并类别（`EXCLUDED_LANGUAGE_NAMES={"Other"}`），过滤后从更低位补足满额真实语言；全部被过滤时拒绝。
- 默认 dry-run，`--apply` 才写文件。
- 滚动窗口实时增长，快照数字与 dashboard 有分钟级出入属正常。

## 定时同步

`.github/workflows/update-wakatime-stats.yml`：GitHub Actions cron（UTC 18:30，即北京时间 02:30）跑 `fetch --apply` → `build_hero`，`git diff` 有变化才以 `github-actions[bot]` 身份提交推送，无变化静默退出（bot 提交不占 contribution graph）。凭据是仓库 secret `WAKATIME_OAUTH_TOKEN`，与本地文件共用 `load_token()` 入口。抓取失败时 job 显式失败以暴露 token 过期，不静默吞错；同步提交会触发 CI 复验产物一致性。

## 渲染联动

`render_hero()` 经 `load_wakatime()` 读快照；文件不存在时四份产物均无 insights 页。快照变化只使两份 motion 产物过期，静态产物不受影响（静态版不含 insights 页）。

语言榜当前保留 Markdown（真实编码时间，GitHub 语境下展示合理）；排除只需向 `EXCLUDED_LANGUAGE_NAMES` 增加 `"Markdown"`。

多台 Linux 设备装插件后由 WakaTime 服务端同账号聚合，低配机器可以不装，统计不追求全设备覆盖。
