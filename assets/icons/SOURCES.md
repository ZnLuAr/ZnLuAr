# 技术栈图标来源

<!-- 本文件由 scripts/fetch_tech_arsenal.py 生成；请修改脚本中的来源声明。 -->

当前已格式化 **29** 枚，另有 **4** 枚待核验。
正式候选图标全部为本地 SVG，统一为 `0 0 24 24` 视图和 `currentColor` 主题墨色。
普通单色源只移除硬编码填色并等比缩放，不重绘路径；多路径、镂空和 `fill-rule` 保留。
Lightroom Classic 使用显式专用转换：核验官方底板和三条字标后合并为单一路径，以 `evenodd` 将字标保留为透明负形。
Batch 使用显式专用转换：核验 vscode-icons 的齿轮路径与八个圆环描边，移除渐变定义并将全部墨色改为 `currentColor`，保留圆环坐标和线宽；不放宽普通描边源规则。
VB6 与 FL Studio 来自 Icons8 的 100×100 PNG；原始文件及经视觉核验的本地派生 SVG 均保存在 `sources/`。VB6 提取内部线稿；FL Studio 使用 `flstudio-detail-outline` 专用转换：主路径以 `evenodd` 保留实心果身并扣除叶柄和高光，第二路径只用 `fill="none"`、`stroke="currentColor"`、`stroke-width="1.6"` 描绘叶柄和高光轮廓，不做透明度叠加，也不把位图嵌入 SVG。
双语 README 与本页保留 Icons8 署名链接；这些派生图标不是 Microsoft 或 Image-Line 发布的官方矢量文件。

固定上游版本：

- Simple Icons: [`17cd4ee07612198a1d8777a060d4100423762a8b`](https://github.com/simple-icons/simple-icons/commit/17cd4ee07612198a1d8777a060d4100423762a8b)
- Devicon: [`32fe1d3b3f36ad11f90ab94f7db59738139c2bf6`](https://github.com/devicons/devicon/commit/32fe1d3b3f36ad11f90ab94f7db59738139c2bf6)
- vscode-icons: [`1b9bfb20a20ca0d7d5bba5b381f4889cff55675b`](https://github.com/vscode-icons/vscode-icons/commit/1b9bfb20a20ca0d7d5bba5b381f4889cff55675b)
- Icons8 页面不声称固定到不可变版本；`--check` 核验本地原始 PNG 的 SHA-256 和派生 SVG，完整条款以[官方授权页](https://icons8.com/license)为准。
- VB6 原始 PNG SHA-256: `14a081bde00905547ec71536c4bd0860e5cc3bae21a7817def831e7da5ff8122`
- FL Studio 原始 PNG SHA-256: `b42a74520a49d56eb1dafd49d1f8c033541677f24b7607b3cc0c325320124a9f`
- Adobe 官方 Lightroom Classic 地址没有不可变版本标识；`--check` 核对该 URL 的当前内容，不声称它固定到 commit。

Simple Icons 的条目同时记录品牌来源；Devicon 与 vscode-icons 是社区维护的图标集合，不能据此推定官方背书。Icons8 是第三方图标来源，也不代表相应软件厂商背书。
Batch 齿轮是与 bat 文件类型关联的社区图标，不是 Microsoft 官方 Logo。
Adobe 条目来自官方产品资产地址，其品牌资产与商标权仍归 Adobe；这不等同于开源授权。
三份上游许可证文本分别保存在 `LICENSE.simple-icons.txt`、`LICENSE.devicon.txt` 和 `LICENSE.vscode-icons.txt`。Icons8 使用免费署名条款，不冒充开源许可证；品牌、商标及个别图标的附加许可仍需遵守。

| 条目 | 本地文件 | 实际抓取文件 | 品牌/项目来源 | 许可与权利说明 |
| --- | --- | --- | --- | --- |
| Python | `python.svg` | [Simple Icons SVG](https://raw.githubusercontent.com/simple-icons/simple-icons/17cd4ee07612198a1d8777a060d4100423762a8b/icons/python.svg) | [上游](https://www.python.org/community/logos/) / [品牌规范](https://www.python.org/community/logos/) | Simple Icons CC0-1.0；品牌/商标权利仍归原权利人 |
| Go | `go.svg` | [Simple Icons SVG](https://raw.githubusercontent.com/simple-icons/simple-icons/17cd4ee07612198a1d8777a060d4100423762a8b/icons/go.svg) | [上游](https://blog.golang.org/go-brand) / [品牌规范](https://blog.golang.org/go-brand) | Simple Icons CC0-1.0；品牌/商标权利仍归原权利人 |
| Java | `java.svg` | [Devicon SVG](https://raw.githubusercontent.com/devicons/devicon/32fe1d3b3f36ad11f90ab94f7db59738139c2bf6/icons/java/java-plain.svg) | [上游](https://www.oracle.com/java/) | Devicon MIT；品牌/商标权利仍归原权利人 |
| Rust | `rust.svg` | [Simple Icons SVG](https://raw.githubusercontent.com/simple-icons/simple-icons/17cd4ee07612198a1d8777a060d4100423762a8b/icons/rust.svg) | [上游](https://www.rust-lang.org) / [品牌规范](https://www.rust-lang.org/policies/media-guide) | [CC-BY-SA-4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| Bash | `bash.svg` | [Simple Icons SVG](https://raw.githubusercontent.com/simple-icons/simple-icons/17cd4ee07612198a1d8777a060d4100423762a8b/icons/gnubash.svg) | [上游](https://github.com/odb/official-bash-logo/tree/61eff022f2dad3c7468f5deb4f06652d15f2c143) / [品牌规范](https://github.com/odb/official-bash-logo) | [MIT](https://opensource.org/license/mit) |
| VB6 | `vb6.svg` | [Icons8 来源页](https://icons8.com/icons/set/microsoft-visual-basic-6) | [上游](https://icons8.com/icons/set/microsoft-visual-basic-6) | Icons8 免费署名使用；README 与预览保留来源链接；本地 SVG 为派生路径，商标权利仍归原权利人 |
| Batch | `batch.svg` | [vscode-icons SVG](https://raw.githubusercontent.com/vscode-icons/vscode-icons/1b9bfb20a20ca0d7d5bba5b381f4889cff55675b/icons/file_type_bat.svg) | [上游](https://github.com/vscode-icons/vscode-icons) | vscode-icons MIT；社区文件类型图标，非 Microsoft 官方 Batch Logo |
| Markdown | `markdown.svg` | [Simple Icons SVG](https://raw.githubusercontent.com/simple-icons/simple-icons/17cd4ee07612198a1d8777a060d4100423762a8b/icons/markdown.svg) | [上游](https://github.com/dcurtis/markdown-mark/tree/360a3657fef7f6ad0b303296a95ad52985caa0d3) / [品牌规范](https://github.com/dcurtis/markdown-mark) | [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| Git | `git.svg` | [Simple Icons SVG](https://raw.githubusercontent.com/simple-icons/simple-icons/17cd4ee07612198a1d8777a060d4100423762a8b/icons/git.svg) | [上游](https://git-scm.com/community/logos) | [CC-BY-3.0](https://creativecommons.org/licenses/by/3.0/) |
| GitHub | `github.svg` | [Simple Icons SVG](https://raw.githubusercontent.com/simple-icons/simple-icons/17cd4ee07612198a1d8777a060d4100423762a8b/icons/github.svg) | [上游](https://github.com/logos) / [品牌规范](https://github.com/logos) | Simple Icons CC0-1.0；品牌/商标权利仍归原权利人 |
| Docker | `docker.svg` | [Simple Icons SVG](https://raw.githubusercontent.com/simple-icons/simple-icons/17cd4ee07612198a1d8777a060d4100423762a8b/icons/docker.svg) | [上游](https://www.docker.com/company/newsroom/media-resources) | Simple Icons CC0-1.0；品牌/商标权利仍归原权利人 |
| Jenkins | `jenkins.svg` | [Simple Icons SVG](https://raw.githubusercontent.com/simple-icons/simple-icons/17cd4ee07612198a1d8777a060d4100423762a8b/icons/jenkins.svg) | [上游](https://get.jenkins.io/art/) / [品牌规范](https://www.jenkins.io/press/) | [CC-BY-SA-3.0](https://creativecommons.org/licenses/by-sa/3.0/) |
| Caddy | `caddy.svg` | [Simple Icons SVG](https://raw.githubusercontent.com/simple-icons/simple-icons/17cd4ee07612198a1d8777a060d4100423762a8b/icons/caddy.svg) | [上游](https://caddyserver.com) | Simple Icons CC0-1.0；品牌/商标权利仍归原权利人 |
| Prometheus | `prometheus.svg` | [Simple Icons SVG](https://raw.githubusercontent.com/simple-icons/simple-icons/17cd4ee07612198a1d8777a060d4100423762a8b/icons/prometheus.svg) | [上游](https://prometheus.io) | Simple Icons CC0-1.0；品牌/商标权利仍归原权利人 |
| Grafana | `grafana.svg` | [Simple Icons SVG](https://raw.githubusercontent.com/simple-icons/simple-icons/17cd4ee07612198a1d8777a060d4100423762a8b/icons/grafana.svg) | [上游](https://grafana.com) | Simple Icons CC0-1.0；品牌/商标权利仍归原权利人 |
| LaTeX | `latex.svg` | [Simple Icons SVG](https://raw.githubusercontent.com/simple-icons/simple-icons/17cd4ee07612198a1d8777a060d4100423762a8b/icons/latex.svg) | [上游](https://github.com/latex3/branding/tree/9def6b5f6075567d62b67424e11dbe6d4d5245b4) | Simple Icons CC0-1.0；品牌/商标权利仍归原权利人 |
| SQLite | `sqlite.svg` | [Simple Icons SVG](https://raw.githubusercontent.com/simple-icons/simple-icons/17cd4ee07612198a1d8777a060d4100423762a8b/icons/sqlite.svg) | [上游](https://github.com/sqlite/sqlite/blob/43e862723ec680542ca6f608f9963c0993dd7324/art/sqlite370.eps) | Simple Icons CC0-1.0；品牌/商标权利仍归原权利人 |
| MySQL | `mysql.svg` | [Simple Icons SVG](https://raw.githubusercontent.com/simple-icons/simple-icons/17cd4ee07612198a1d8777a060d4100423762a8b/icons/mysql.svg) | [上游](https://www.mysql.com/about/legal/logos.html) / [品牌规范](https://www.mysql.com/about/legal/logos.html) | Simple Icons CC0-1.0；品牌/商标权利仍归原权利人 |
| PostgreSQL | `postgresql.svg` | [Simple Icons SVG](https://raw.githubusercontent.com/simple-icons/simple-icons/17cd4ee07612198a1d8777a060d4100423762a8b/icons/postgresql.svg) | [上游](https://wiki.postgresql.org/wiki/Logo) / [品牌规范](https://www.postgresql.org/about/policies/trademarks/) | Simple Icons CC0-1.0；品牌/商标权利仍归原权利人 |
| Debian | `debian.svg` | [Simple Icons SVG](https://raw.githubusercontent.com/simple-icons/simple-icons/17cd4ee07612198a1d8777a060d4100423762a8b/icons/debian.svg) | [上游](https://www.debian.org/logos) / [品牌规范](https://www.debian.org/logos/) | [CC-BY-SA-3.0](https://creativecommons.org/licenses/by-sa/3.0/) |
| Ubuntu | `ubuntu.svg` | [Simple Icons SVG](https://raw.githubusercontent.com/simple-icons/simple-icons/17cd4ee07612198a1d8777a060d4100423762a8b/icons/ubuntu.svg) | [上游](https://design.ubuntu.com/resources) / [品牌规范](https://design.ubuntu.com/brand) | Simple Icons CC0-1.0；品牌/商标权利仍归原权利人 |
| Vim | `vim.svg` | [Simple Icons SVG](https://raw.githubusercontent.com/simple-icons/simple-icons/17cd4ee07612198a1d8777a060d4100423762a8b/icons/vim.svg) | [上游](https://commons.wikimedia.org/wiki/File:Vimlogo.svg) | Simple Icons CC0-1.0；品牌/商标权利仍归原权利人 |
| VS Code | `vscode.svg` | [Devicon SVG](https://raw.githubusercontent.com/devicons/devicon/32fe1d3b3f36ad11f90ab94f7db59738139c2bf6/icons/vscode/vscode-plain.svg) | [上游](https://github.com/microsoft/vscode) | Devicon MIT；品牌/商标权利仍归原权利人 |
| FL Studio | `flstudio.svg` | [Icons8 来源页](https://icons8.com/icon/33042/fl-studio) | [上游](https://icons8.com/icon/33042/fl-studio) | Icons8 免费署名使用；README 与预览保留来源链接；本地 SVG 为派生路径，商标权利仍归原权利人 |
| Blender | `blender.svg` | [Simple Icons SVG](https://raw.githubusercontent.com/simple-icons/simple-icons/17cd4ee07612198a1d8777a060d4100423762a8b/icons/blender.svg) | [上游](https://www.blender.org/about/logo) / [品牌规范](https://www.blender.org/about/logo) | Simple Icons CC0-1.0；品牌/商标权利仍归原权利人 |
| Lightroom Classic | `lightroom.svg` | [Adobe SVG](https://www.adobe.com/cc-shared/assets/img/product-icons/svg/lightroom-classic-64.svg) | [上游](https://www.adobe.com/products/photoshop-lightroom-classic.html) | 官方品牌资产；Adobe 商标权利保留，未附加开源许可 |
| Photoshop | `photoshop.svg` | [Devicon SVG](https://raw.githubusercontent.com/devicons/devicon/32fe1d3b3f36ad11f90ab94f7db59738139c2bf6/icons/photoshop/photoshop-plain.svg) | [上游](https://www.adobe.com/products/photoshop.html) | Devicon MIT；品牌/商标权利仍归原权利人 |
| After Effects | `aftereffects.svg` | [Devicon SVG](https://raw.githubusercontent.com/devicons/devicon/32fe1d3b3f36ad11f90ab94f7db59738139c2bf6/icons/aftereffects/aftereffects-plain.svg) | [上游](https://www.adobe.com/products/aftereffects.html) | Devicon MIT；品牌/商标权利仍归原权利人 |
| Dreamweaver | `dreamweaver.svg` | [Devicon SVG](https://raw.githubusercontent.com/devicons/devicon/32fe1d3b3f36ad11f90ab94f7db59738139c2bf6/icons/dreamweaver/dreamweaver-plain.svg) | [上游](https://www.adobe.com/products/dreamweaver.html) | Devicon MIT；品牌/商标权利仍归原权利人 |

## 尚待核验

以下条目没有写入图标文件，也没有使用相近品牌或通用终端图形代替：

- **VBScript**：可信独立 SVG 来源、版本语义和许可仍待专项核验。
- **GNU Make**：可信独立 SVG 来源、版本语义和许可仍待专项核验。
- **MS-DOS**：可信独立 SVG 来源、版本语义和许可仍待专项核验。
- **Adobe Flash**：可信独立 SVG 来源、版本语义和许可仍待专项核验。

## 重新抓取与检查

```bash
# 默认 dry-run：下载并在内存中验证，不写文件
python scripts/fetch_tech_arsenal.py

# 写入格式化图标、许可证、来源表和静态预览
python scripts/fetch_tech_arsenal.py --apply

# 联网核对本地文件是否仍与声明的上游一致，不写文件
python scripts/fetch_tech_arsenal.py --check
```
