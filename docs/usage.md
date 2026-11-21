# 使用说明

> 定位：日常操作手册——构建、抓数据、调参、测试、验证。架构与目录分工见 [architecture](architecture.md)。

## 前提

- Python 3.13+，只用标准库，无需安装依赖。
- 可选：Edge（截图验证）、Blender 5.3（投影校准）。
- 抓取编码统计需要 WakaTime OAuth token（见下文"抓取编码统计"）。

所有命令在仓库根目录执行。

## 构建

```bash
python scripts/build_hero.py          # 重新生成四份 SVG（light/dark × 静态/动态）
python scripts/build_hero.py --check  # 只检查 JSON 与 SVG 是否同步，不写文件
```

预期输出 `write: static and motion hero SVGs  success`（或 check 版的 `check: ... up to date  success`）。`--check` 失败说明生成源或输入数据变了而产物没重建，重跑不带 `--check` 的构建即可。

## 抓取编码统计

### 配置凭据（一次性）

1. 复制 `_wakatime_token.local.example` 为仓库根的 `_wakatime_token.local`（已 gitignore）。
2. 从 https://wakatime.com/oauth 获取个人 OAuth token（read_stats 权限），或走下文的 app 授权流程。
3. 文件内容只留一行 token（`waka_tok_` 前缀）。

编辑器插件的 API key（`waka_sec_` 前缀）是 write-only，读取统计会 401，脚本会直接拒绝并提示。token 授权码流程签发后有效期 100 年，无需刷新。

### 日常刷新

```bash
python -I scripts/fetch_wakatime.py           # dry-run，只预览
python -I scripts/fetch_wakatime.py --apply   # 写入 gen/hero/wakatime.json
python scripts/build_hero.py                  # 重建四份 Hero
```

预期输出 `stats: last_7_days total ... · daily ... · top ... success`。抓取失败（网络、聚合未完成、区间无数据）时保留现有快照，不会写坏文件。滚动窗口实时增长，快照数字比 dashboard 略旧属正常。

### 自动同步（GitHub Actions，一次性启用）

`.github/workflows/update-wakatime-stats.yml` 每日 UTC 18:30 自动执行与上文相同的管线（抓取 → 重建 → 有变化才以 bot 身份提交推送）。启用步骤：

1. 仓库 **Settings → Secrets and variables → Actions → New repository secret**：名称 `WAKATIME_OAUTH_TOKEN`，值为 `_wakatime_token.local` 里的同一 token。
2. Actions 页面 **WakaTime Sync → Run workflow** 手动跑一次验证。

### token 失效时重新授权

前提：WakaTime 账号，且已创建 OAuth app（WakaTime 网页可建；redirect_uri 两步必须完全一致，选一个没有服务监听的本地端口即可——授权后浏览器跳转过去只会显示打不开，code 从地址栏复制；不要用已有服务在监听的端口，避免 code 落进该服务的访问日志）。

1. 浏览器打开（替换 `<App ID>` 和 `<redirect_uri>`）：

   ```text
   https://wakatime.com/oauth/authorize?client_id=<App ID>&response_type=code&scope=read_stats&redirect_uri=<redirect_uri>
   ```

2. 授权后浏览器跳到 `redirect_uri?code=<一次性 code>`（页面打不开没关系，从地址栏复制 code）。
3. 换 token（端点不带 `/api/v1`；code 短时效且一次性）：

   ```bash
   curl -s -X POST https://wakatime.com/oauth/token \
     -d grant_type=authorization_code \
     -d client_id=<App ID> -d client_secret=<App Secret> \
     -d redirect_uri=<redirect_uri> -d code=<code>
   ```

4. 返回 JSON 的 `access_token`（`waka_tok_` 前缀）写入 `_wakatime_token.local`。

注意每 app 每用户限 8 个活跃 token（超限自动吊销最旧的）、每小时限 10 个新 token，不要频繁重授权。此流程 2026-11-20 经等效请求验证（Python urllib；端点与参数同上）。

## 技术栈图标

```bash
python -I scripts/fetch_tech_arsenal.py           # dry-run
python -I scripts/fetch_tech_arsenal.py --apply   # 写入图标 SVG、来源表和预览
python -I scripts/fetch_tech_arsenal.py --check   # 联网核对声明来源
```

预期摘要 `29 icons written; 4 entries remain explicitly pending  success`、`check: 34 files match declared upstream sources  success`。来源与顺序只在 `scripts/icon_manifest.py` 声明，新增图标先改它（设计边界见 [design/tech-icons.md](design/tech-icons.md)，含 4 个待核验项的采用条件）。上游网络故障（如 raw.githubusercontent.com 503）时重试即可，已写入的本地派生不受影响。

## 场景调参

```bash
python scripts/adjust_scene.py --help   # 查看全部参数
python scripts/adjust_scene.py --pitch 30 --zoom 2 --apply
```

- `--pitch` / `--yaw`：绝对角度。
- `--zoom`：相对当前距离的倍率，大于 1 拉远、小于 1 拉近。
- `--motion-speed`：相对当前转速的倍率（如 `0.6` 降到 60%），周期相应除以该值，不改采样点。
- 默认 dry-run；`--apply` 先在内存验证全部顶点投影和 SVG 构建，再写 `scene.json`、四份 SVG 和 Blender 校准脚本。

逐项输出 `旧值 → 新值  success`。调整过程中的几何不变量见 [design/scene-rendering.md](design/scene-rendering.md)。

## 测试

```bash
python -m unittest discover -s tests -v
```

当前 91 项全过。改动渲染、数据链或图标后必须重跑；CI 在 push / PR 时跑同一组测试加构建检查。

## 截图验证（静态副本法）

headless 的 `--virtual-time-budget` 对 SMIL 推进不可靠，验证某一轮播页时用翻转初始 opacity 的静态副本：

1. 用正则把 `<g opacity="([01])"><animate .../></>` 替换为翻转 opacity 且去掉 animate，写入 `gen/hero/.comparison/`（gitignore）。
2. Edge 截图：

   ```bash
   "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --headless=new \
     --screenshot="<绝对路径>.png" --window-size=1600,900 "file:///<副本路径>.svg"
   ```

3. 肉眼或视觉模型核验后删除副本。

## 工作约定

- 不擅自 commit、推送或发布；commit 由仓库所有者明确发起。
- 凭据永不进仓库：`_wakatime_token.local` 是唯一的本地凭据文件（已 gitignore）。
- 脚本输出保持中文、`旧值 → 新值  success` 风格。
- 参数调整一律走 `scripts/adjust_scene.py`，不手改 `scene.json`；文档与代码同步更新。
