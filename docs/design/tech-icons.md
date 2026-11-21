# 技术栈图标链设计

> 定位：29 枚图标的来源、安全规范化、专用转换、矩阵布局与许可证边界。

## 单一来源清单

来源与顺序只维护在 `scripts/icon_manifest.py`，按 **9–8–7–9** 四行声明全部 33 项；抓取器（`fetch_tech_arsenal.py`）和 Hero 布局（`scripts/hero/stack.py`）共同读取，不存在第二套顺序声明。Hero 省略未核验项并将各行居中，当前实际渲染 **8–7–6–8** 共 29 枚，不伪造图标或显示空槽。

当前声明顺序：第一行 Python、Go、Java、Rust、Bash、VB6、Batch、VBScript、Markdown；第二行 Git、GitHub、GNU Make、Docker、Jenkins、Caddy、Prometheus、Grafana；第三行 LaTeX、SQLite、MySQL、PostgreSQL、Debian、Ubuntu、MS-DOS；第四行 Vim、VS Code、FL Studio、Blender、Lightroom Classic、Photoshop、After Effects、Dreamweaver、Adobe Flash。

## 矩阵布局

- 128×128 图标、列距 142、行距 144，中心 `(980,458)`，标题基线 y=118；最宽行边界约 `x=419–1541`，纵向约 `y=178–738`。
- 上下两行宽、中间两行窄（8–7–6–8）。
- 立方体完整动画最右投影约 333px，与矩阵左缘间隔约 86px。
- 布局只针对当前 29 枚校准；未来补项导致超界时构建明确报错，必须重新校准布局，不沿用旧版容量承诺。
- 图标无独立动画、底板、胶囊、边框、发光或可见文字标签，不表达熟练度、进度或排名。LrC/Ps/Ae/Dw 自带的圆角方形属于原始 Logo 几何。

## 上游来源与固定性

当前来源：Simple Icons 20 枚、Devicon 5 枚、vscode-icons 1 枚、Adobe 官方 1 枚、Icons8 2 枚。

- Simple Icons、Devicon、vscode-icons 固定完整 commit。
- Adobe 官方 LrC URL 无不可变版本标识，来源表明确 `--check` 核对其当前内容，不声称固定到 commit。
- Icons8 条目使用本地原始 PNG 的固定 SHA-256 和受审派生 SVG，不声称官方或不可变上游。

## 安全规范化

正式本地图标统一为 `0 0 24 24`、`currentColor` 和原始路径几何；128×128 等源视图通过容器变换等比缩放，保留 `fill-rule`、镂空及多路径。危险 SVG（脚本、外部引用、事件属性等）默认拒绝；多颜色源默认拒绝；描边源默认拒绝。专用转换（下节）是对特定已核验源的显式豁免，不放宽通用规则。

输出均为真正的 `<path>`，无 `<image>`、base64 或运行时图像处理。每次运行重建 `SOURCES.md`、三份上游许可证副本和静态双主题预览；`--check` 联网逐字核对远端输出并校验本地派生输出，本地共 34 个输出与声明来源一致。

## 专用转换

- **LrC（`evenodd-cutout`）**：只接受官方 64×64、一个 `#001E36` 底板和三个 `#31A8FF` 字标的已核验结构，拒绝活动引用和额外路径变换；四条路径合并为一个 `evenodd` 路径，`LrC` 字标成为透明负形，等比缩放到 24×24。
- **Batch（`batch-strokes`）**：vscode-icons commit `1b9bfb20a20ca0d7d5bba5b381f4889cff55675b` 的 `icons/file_type_bat.svg`（MIT）。它是与 bat 文件类型关联的**社区图标，不是 Microsoft 官方 Batch Logo**。转换只接受已核验的 32×32 银色齿轮路径和八个圆环，删除渐变及原始颜色，圆环统一 `fill="none"`、`stroke="currentColor"`，`scale(0.75)` 纳入 24×24。Hero 图标父组同时设置主题 `fill` 和 `color`，描边继承同一墨色。
- **VB6（Icons8 派生）**：本地 100×100 PNG（SHA-256 固定）提取圆柱/立方体线稿。
- **FL Studio（`flstudio-detail-outline`）**：第一条路径以 `evenodd` 保留实心果身并扣除叶柄和高光两个子轮廓；第二条路径以 `fill="none"`、`stroke="currentColor"`、`stroke-width="1.6"` 只描绘细节轮廓。果身外缘不描边，细节不叠加独立灰度。转换强制核验路径数、子轮廓数及主路径末尾完全包含细节几何，避免把覆盖误当挖空；篡改线宽与未经显式转换的描边源均有拒绝测试。

`verified_local_source()` 在校验原始 PNG 后把本地矢量交给既有 `normalize_svg()`，因此 `--check` 同时覆盖本地派生链。

## 名称语义

GoLang 记为 Go；VBS 记为 VBScript；Visual Basic 明确为经典 **VB6**，不得误用 VB.NET 语义；vi/Vim 只展示一枚 Vim；bash/shell 只声明 Bash。Dreamweaver、Flash、MS-DOS 等早期工具不因年代删除，排在阅读顺序后部，不制造"考古"标签或熟练度暗示。

## 许可证与署名

双语 README 与预览页保留 VB6 / FL Studio 的 Icons8 署名链接，署名不进入 Hero 画面。Adobe 品牌资产与商标权归 Adobe，官方可下载不等同于开源授权。Icons8 非开源许可证，完整条款以其官方授权页为准。

## 待核验边界（4 项）

- MS-DOS：有 Commons `Msdos-icon.svg`（标为 Microsoft + Expat/MIT + Trademark），但原始来源链是 Seeklogo 而非 Microsoft 发布页，需保守复核。
- Flash：有 Commons 社区矢量化候选，存在 CS6/CC 识别争议，不得描述成无争议的 Adobe 官方原图。
- VBScript：未找到可信独立 Logo/SVG。
- GNU Make：未找到专用官方独立 Logo，通用 GNU 头不能冒充。

上述边界在采用前需要逐一决定，不拿通用图标凑满矩阵。
