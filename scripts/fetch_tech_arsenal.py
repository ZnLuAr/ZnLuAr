#!/usr/bin/env python3
"""Fetch, normalize and document the Tech Arsenal page's local technology icons."""

import argparse
import hashlib
import json
import math
import sys
import tempfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html import escape
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from icon_manifest import (
    DEVICON_BASE,
    DEVICON_COMMIT,
    ROWS,
    SIMPLE_ICONS_BASE,
    SIMPLE_ICONS_COMMIT,
    VSCODE_ICONS_BASE,
    VSCODE_ICONS_COMMIT,
    entries,
    pending_entries,
    resolved_entries,
    source_url,
)

ROOT = Path(__file__).resolve().parents[1]
ICON_DIR = ROOT / "assets" / "icons"
PREVIEW_PATH = ROOT / "preview" / "icons.html"
SOURCES_PATH = ICON_DIR / "SOURCES.md"
SVG_NS = "http://www.w3.org/2000/svg"
MAX_DOWNLOAD = 4 * 1024 * 1024
ALLOWED_DOWNLOAD_HOSTS = {"raw.githubusercontent.com", "www.adobe.com"}
USER_AGENT = "ZnLuAr-local-icon-fetcher/1.0"


def checked_url(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_DOWNLOAD_HOSTS:
        raise ValueError(f"Download URL is not allowlisted: {url}")
    return url


def download_bytes(url, timeout=30):
    checked_url(url)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        checked_url(response.geturl())
        length = response.headers.get("Content-Length")
        if length is not None and int(length) > MAX_DOWNLOAD:
            raise ValueError(f"Download exceeds {MAX_DOWNLOAD} bytes: {url}")
        content = response.read(MAX_DOWNLOAD + 1)
    if len(content) > MAX_DOWNLOAD:
        raise ValueError(f"Download exceeds {MAX_DOWNLOAD} bytes: {url}")
    return content


def local_name(tag):
    return tag.rsplit("}", 1)[-1]


def lightroom_cutout(root, name):
    """Turn Adobe's verified four-path tile into one monochrome evenodd path."""
    if root.attrib.get("viewBox") != "0 0 64 64":
        raise ValueError(f"Lightroom cutout requires the official 64x64 source: {name}")
    paths = []
    for element in root.iter():
        tag = local_name(element.tag)
        if tag in ("title", "desc", "metadata"):
            continue
        if element is root:
            continue
        if tag not in ("path", "defs", "clipPath", "rect"):
            raise ValueError(f"Unexpected element <{tag}> in Lightroom cutout: {name}")
        for attribute, value in element.attrib.items():
            attribute = local_name(attribute)
            if (
                attribute.startswith("on")
                or attribute in ("style", "href", "clip-path", "mask", "filter")
                or "url(" in value.lower()
            ):
                raise ValueError(f"Active reference in Lightroom cutout: {name}")
        if tag == "path":
            if {local_name(attribute) for attribute in element.attrib} - {"d", "fill", "id"}:
                raise ValueError(f"Unexpected path attribute in Lightroom cutout: {name}")
            paths.append(element)
    if len(paths) != 4:
        raise ValueError(f"Lightroom cutout requires one tile and three letter paths: {name}")
    colors = [path.attrib.get("fill", "").lower() for path in paths]
    if colors != ["#001e36", "#31a8ff", "#31a8ff", "#31a8ff"]:
        raise ValueError(f"Unexpected Lightroom cutout colors or path order: {name}: {colors}")
    if any(not path.attrib.get("d", "").strip() for path in paths):
        raise ValueError(f"Empty path in Lightroom cutout: {name}")

    converted = ET.Element(root.tag, {"viewBox": root.attrib["viewBox"]})
    ET.SubElement(
        converted,
        f"{{{SVG_NS}}}path",
        {
            "d": " ".join(path.attrib["d"] for path in paths),
            "fill-rule": "evenodd",
        },
    )
    return converted


def batch_strokes(root, name):
    """Preserve the verified gear paths and circle strokes as theme-neutral geometry."""
    if root.attrib.get("viewBox") != "0 0 32 32":
        raise ValueError(f"Batch conversion requires the vscode-icons 32x32 source: {name}")
    allowed_tags = {"svg", "path", "g", "circle", "defs", "radialGradient", "stop"}
    for element in root.iter():
        tag = local_name(element.tag)
        if tag not in allowed_tags:
            raise ValueError(f"Unexpected element <{tag}> in Batch conversion: {name}")
        for attribute, value in element.attrib.items():
            attribute = local_name(attribute)
            if attribute.startswith("on") or attribute in ("style", "class"):
                raise ValueError(f"Active attribute in Batch conversion: {name}")
            if attribute == "href" and not value.startswith("#"):
                raise ValueError(f"External reference in Batch conversion: {name}")
            if attribute == "transform" and tag != "radialGradient":
                raise ValueError(f"Unexpected transform in Batch conversion: {name}")

    paths = [element for element in root.iter() if local_name(element.tag) == "path"]
    if len(paths) != 1:
        raise ValueError(f"Batch conversion requires exactly one gear path: {name}")
    gear = paths[0]
    if gear.attrib.get("fill", "").lower() != "silver" or not gear.attrib.get("d", "").strip():
        raise ValueError(f"Unexpected Batch gear path: {name}")
    if set(gear.attrib) - {"d", "fill"}:
        raise ValueError(f"Unexpected Batch gear attributes: {name}")

    circles = []
    allowed_strokes = {"silver", "#a9a9a9", "url(#a)", "url(#b)"}

    def collect(element, inherited_stroke=None):
        tag = local_name(element.tag)
        if tag == "defs":
            return
        stroke = element.attrib.get("stroke", inherited_stroke)
        if tag == "g":
            if set(element.attrib) - {"fill", "stroke"} or element.attrib.get("fill", "none") != "none":
                raise ValueError(f"Unexpected Batch group: {name}")
        if tag == "circle":
            if set(element.attrib) - {"cx", "cy", "r", "stroke", "stroke-width"}:
                raise ValueError(f"Unexpected Batch circle attributes: {name}")
            if stroke not in allowed_strokes:
                raise ValueError(f"Unexpected Batch circle stroke: {name}")
            values = []
            for attribute in ("cx", "cy", "r", "stroke-width"):
                try:
                    value = float(element.attrib[attribute])
                except (KeyError, ValueError) as error:
                    raise ValueError(f"Invalid Batch circle geometry: {name}") from error
                if not math.isfinite(value) or (attribute in ("r", "stroke-width") and value <= 0):
                    raise ValueError(f"Invalid Batch circle geometry: {name}")
                values.append(element.attrib[attribute])
            circles.append(dict(zip(("cx", "cy", "r", "stroke-width"), values)))
        for child in element:
            collect(child, stroke)

    collect(root)
    if len(circles) != 8:
        raise ValueError(f"Batch conversion requires eight verified circle strokes: {name}")

    converted = ET.Element(root.tag, {"viewBox": root.attrib["viewBox"]})
    ET.SubElement(converted, f"{{{SVG_NS}}}path", {"d": gear.attrib["d"], "fill": "silver"})
    group = ET.SubElement(
        converted,
        f"{{{SVG_NS}}}g",
        {"fill": "none", "stroke": "currentColor"},
    )
    for circle in circles:
        ET.SubElement(group, f"{{{SVG_NS}}}circle", circle)
    return converted


def flstudio_detail_outline(root, name):
    """Keep the fruit solid while leaving leaves and highlight as transparent outlines."""
    expected_viewbox = "21.19 2.33 65.19 90.27"
    if name != "FL Studio" or root.attrib.get("viewBox") != expected_viewbox:
        raise ValueError(f"Unexpected FL Studio detail-outline source: {name}")
    if set(root.attrib) != {"viewBox", "fill"} or root.attrib.get("fill") != "currentColor":
        raise ValueError(f"Unexpected FL Studio root attributes: {name}")
    paths = list(root)
    if len(paths) != 2 or any(local_name(path.tag) != "path" for path in paths):
        raise ValueError(f"FL Studio detail outline requires exactly two paths: {name}")
    main, detail = paths
    if set(main.attrib) != {"d", "fill-rule"} or main.attrib["fill-rule"] != "evenodd":
        raise ValueError(f"Unexpected FL Studio solid fruit path: {name}")
    if set(detail.attrib) != {"d", "fill", "stroke", "stroke-width"}:
        raise ValueError(f"Unexpected FL Studio detail-outline attributes: {name}")
    main_data = main.attrib["d"].strip()
    detail_data = detail.attrib["d"].strip()
    if (
        detail.attrib["fill"] != "none"
        or detail.attrib["stroke"] != "currentColor"
        or detail.attrib["stroke-width"] != "1.6"
        or detail_data.count("M") != 2
        or main_data.count("M") != 3
        or not main_data.endswith(detail_data)
    ):
        raise ValueError(f"Unexpected FL Studio detail geometry or stroke: {name}")

    converted = ET.Element(root.tag, {"viewBox": expected_viewbox})
    ET.SubElement(converted, f"{{{SVG_NS}}}path", dict(main.attrib))
    ET.SubElement(converted, f"{{{SVG_NS}}}path", dict(detail.attrib))
    return converted


def normalize_svg(source, name, conversion=None):
    """Convert a declared source to a safe, theme-neutral 24px SVG."""
    if isinstance(source, bytes):
        source = source.decode("utf-8-sig")
    if "<!DOCTYPE" in source.upper() or "<!ENTITY" in source.upper() or "\x00" in source:
        raise ValueError(f"DTD, entities and NUL bytes are not allowed in {name}")
    root = ET.fromstring(source)
    if local_name(root.tag) != "svg" or "viewBox" not in root.attrib:
        raise ValueError(f"Source must be an SVG with an explicit viewBox: {name}")
    try:
        min_x, min_y, width, height = [
            float(value) for value in root.attrib["viewBox"].replace(",", " ").split()
        ]
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid viewBox in {name}") from error
    if not all(math.isfinite(value) for value in (min_x, min_y, width, height)):
        raise ValueError(f"Non-finite viewBox in {name}")
    if width <= 0 or height <= 0:
        raise ValueError(f"Empty viewBox in {name}")
    if conversion not in (None, "evenodd-cutout", "batch-strokes", "flstudio-detail-outline"):
        raise ValueError(f"Unknown SVG conversion {conversion}: {name}")
    if conversion == "evenodd-cutout":
        root = lightroom_cutout(root, name)
    elif conversion == "batch-strokes":
        root = batch_strokes(root, name)
    elif conversion == "flstudio-detail-outline":
        root = flstudio_detail_outline(root, name)
    allow_strokes = conversion in ("batch-strokes", "flstudio-detail-outline")

    colors = set()
    geometry_count = 0

    def inspect(element):
        nonlocal geometry_count
        tag = local_name(element.tag)
        if tag in ("title", "desc", "metadata"):
            return
        allowed_tags = ("g", "path", "circle") if allow_strokes else ("g", "path")
        if tag not in allowed_tags:
            raise ValueError(f"Unsupported SVG element <{tag}> in {name}")
        for attribute, value in element.attrib.items():
            attribute = local_name(attribute)
            if attribute.startswith("on") or attribute in ("style", "class", "href"):
                raise ValueError(f"Unsupported SVG attribute {attribute} in {name}")
            if attribute == "fill-opacity":
                raise ValueError(f"Fill opacity is not allowed in theme-neutral icons: {name}")
            if attribute == "fill" and value.strip().lower() != "none":
                colors.add(value.strip().lower())
            if attribute == "stroke" and value.strip().lower() != "none":
                if not allow_strokes or value != "currentColor":
                    raise ValueError(f"Stroked source requires an explicit conversion: {name}")
        if tag == "path":
            if not element.attrib.get("d", "").strip():
                raise ValueError(f"Empty path in {name}")
            geometry_count += 1
        for child in element:
            inspect(child)

    for child in root:
        inspect(child)
    if geometry_count == 0:
        raise ValueError(f"No drawable paths in {name}")
    if len(colors) > 1:
        raise ValueError(f"Multi-color source requires an explicit conversion: {name}: {sorted(colors)}")

    def clean(element):
        tag = local_name(element.tag)
        attributes = {}
        allowed_attributes = ["d", "transform", "fill-rule", "clip-rule"]
        if allow_strokes:
            allowed_attributes.extend(("cx", "cy", "r", "stroke-width"))
        for attribute in allowed_attributes:
            if attribute in element.attrib:
                attributes[attribute] = element.attrib[attribute]
        if element.attrib.get("stroke") == "currentColor":
            attributes["stroke"] = "currentColor"
        if element.attrib.get("fill", "").strip().lower() == "none":
            attributes["fill"] = "none"
        cleaned = ET.Element(f"{{{SVG_NS}}}{tag}", attributes)
        for child in element:
            if local_name(child.tag) not in ("title", "desc", "metadata"):
                cleaned.append(clean(child))
        return cleaned

    output = ET.Element(
        f"{{{SVG_NS}}}svg",
        {
            "viewBox": "0 0 24 24",
            "width": "24",
            "height": "24",
            "role": "img",
            "fill": "currentColor",
        },
    )
    ET.SubElement(output, f"{{{SVG_NS}}}title").text = name
    scale = min(24 / width, 24 / height)
    translate_x = -min_x * scale + (24 - width * scale) / 2
    translate_y = -min_y * scale + (24 - height * scale) / 2
    if (min_x, min_y, width, height) == (0, 0, 24, 24):
        container = output
    else:
        transform = (
            f"translate({translate_x:.12g} {translate_y:.12g}) "
            f"scale({scale:.12g})"
        )
        container = ET.SubElement(output, f"{{{SVG_NS}}}g", {"transform": transform})
    for child in root:
        if local_name(child.tag) not in ("title", "desc", "metadata"):
            container.append(clean(child))
    ET.register_namespace("", SVG_NS)
    return ET.tostring(output, encoding="unicode", short_empty_elements=True) + "\n"


def verified_local_source(entry):
    """Verify the pinned raster provenance and return its reviewed local vector."""
    raster_path = ICON_DIR / entry["raster_source"]
    digest = hashlib.sha256(raster_path.read_bytes()).hexdigest()
    if digest != entry["raster_sha256"]:
        raise ValueError(f'Local Icons8 raster checksum mismatch: {entry["id"]}')
    return (ICON_DIR / entry["local_source"]).read_bytes()


def license_text(metadata):
    license_data = metadata.get("license")
    if not license_data:
        return "Simple Icons CC0-1.0；品牌/商标权利仍归原权利人"
    kind = license_data["type"]
    if license_data.get("url"):
        return f'[{kind}]({license_data["url"]})'
    creative_commons = {
        "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
        "CC-BY-3.0": "https://creativecommons.org/licenses/by/3.0/",
        "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
        "CC-BY-SA-3.0": "https://creativecommons.org/licenses/by-sa/3.0/",
        "CC-BY-SA-4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
        "MIT": "https://opensource.org/license/mit",
    }
    if kind in creative_commons:
        return f"[{kind}]({creative_commons[kind]})"
    return kind


def build_outputs():
    simple_metadata = json.loads(download_bytes(f"{SIMPLE_ICONS_BASE}/data/simple-icons.json"))
    simple_by_title = {item["title"]: item for item in simple_metadata}
    icons = {}
    records = {}
    with tempfile.TemporaryDirectory(prefix="znlular-icon-sources-") as temporary:
        for index, entry in enumerate(resolved_entries(), start=1):
            raw_dir = Path(temporary) / f'{index:02d}-{entry["id"]}'
            raw_dir.mkdir()
            raw_path = raw_dir / ("source.svg" if not entry.get("local_source") else "derived.svg")
            url = source_url(entry)
            if entry.get("local_source"):
                raw_path.write_bytes(verified_local_source(entry))
                action = "verify + normalize local derivation"
            else:
                raw_path.write_bytes(download_bytes(url))
                action = "fetch + normalize"
            icons[entry["id"]] = normalize_svg(
                raw_path.read_bytes(), entry["name"], entry.get("conversion")
            )
            if entry["provider"] == "Simple Icons":
                metadata = simple_by_title.get(entry["source_title"])
                if metadata is None:
                    raise ValueError(f'Simple Icons metadata missing: {entry["source_title"]}')
                records[entry["id"]] = {
                    **entry,
                    "url": url,
                    "brand": metadata["source"],
                    "guidelines": metadata.get("guidelines"),
                    "license": license_text(metadata),
                }
            elif entry["provider"] == "Devicon":
                records[entry["id"]] = {
                    **entry,
                    "url": url,
                    "guidelines": None,
                    "license": "Devicon MIT；品牌/商标权利仍归原权利人",
                }
            elif entry["provider"] == "vscode-icons":
                records[entry["id"]] = {**entry, "url": url, "guidelines": None}
            elif entry["provider"] in ("Adobe", "Icons8"):
                records[entry["id"]] = {**entry, "url": url, "guidelines": None}
            else:
                raise ValueError(f'Unknown icon provider: {entry["provider"]}')
            print(f'{action}: {entry["id"]}.svg ← {url}  success')

    outputs = {
        ICON_DIR / f'{entry["id"]}.svg': icons[entry["id"]]
        for entry in resolved_entries()
    }
    outputs[ICON_DIR / "LICENSE.simple-icons.txt"] = download_bytes(
        f"{SIMPLE_ICONS_BASE}/LICENSE.md"
    ).decode("utf-8")
    outputs[ICON_DIR / "LICENSE.devicon.txt"] = download_bytes(
        f"{DEVICON_BASE}/LICENSE"
    ).decode("utf-8")
    outputs[ICON_DIR / "LICENSE.vscode-icons.txt"] = download_bytes(
        f"{VSCODE_ICONS_BASE}/LICENSE"
    ).decode("utf-8")
    outputs[SOURCES_PATH] = sources_markdown(records)
    outputs[PREVIEW_PATH] = preview_html(icons, records)
    return outputs


def sources_markdown(records):
    lines = [
        "# 技术栈图标来源",
        "",
        "<!-- 本文件由 scripts/fetch_tech_arsenal.py 生成；请修改脚本中的来源声明。 -->",
        "",
        f'当前已格式化 **{len(records)}** 枚，另有 **{len(pending_entries())}** 枚待核验。',
        "正式候选图标全部为本地 SVG，统一为 `0 0 24 24` 视图和 `currentColor` 主题墨色。",
        "普通单色源只移除硬编码填色并等比缩放，不重绘路径；多路径、镂空和 `fill-rule` 保留。",
        "Lightroom Classic 使用显式专用转换：核验官方底板和三条字标后合并为单一路径，以 `evenodd` 将字标保留为透明负形。",
        "Batch 使用显式专用转换：核验 vscode-icons 的齿轮路径与八个圆环描边，移除渐变定义并将全部墨色改为 `currentColor`，保留圆环坐标和线宽；不放宽普通描边源规则。",
        "VB6 与 FL Studio 来自 Icons8 的 100×100 PNG；原始文件及经视觉核验的本地派生 SVG 均保存在 `sources/`。VB6 提取内部线稿；FL Studio 使用 `flstudio-detail-outline` 专用转换：主路径以 `evenodd` 保留实心果身并扣除叶柄和高光，第二路径只用 `fill=\"none\"`、`stroke=\"currentColor\"`、`stroke-width=\"1.6\"` 描绘叶柄和高光轮廓，不做透明度叠加，也不把位图嵌入 SVG。",
        "双语 README 与本页保留 Icons8 署名链接；这些派生图标不是 Microsoft 或 Image-Line 发布的官方矢量文件。",
        "",
        "固定上游版本：",
        "",
        f"- Simple Icons: [`{SIMPLE_ICONS_COMMIT}`](https://github.com/simple-icons/simple-icons/commit/{SIMPLE_ICONS_COMMIT})",
        f"- Devicon: [`{DEVICON_COMMIT}`](https://github.com/devicons/devicon/commit/{DEVICON_COMMIT})",
        f"- vscode-icons: [`{VSCODE_ICONS_COMMIT}`](https://github.com/vscode-icons/vscode-icons/commit/{VSCODE_ICONS_COMMIT})",
        "- Icons8 页面不声称固定到不可变版本；`--check` 核验本地原始 PNG 的 SHA-256 和派生 SVG，完整条款以[官方授权页](https://icons8.com/license)为准。",
        *[f'- {entry["name"]} 原始 PNG SHA-256: `{entry["raster_sha256"]}`' for entry in resolved_entries() if entry["provider"] == "Icons8"],
        "- Adobe 官方 Lightroom Classic 地址没有不可变版本标识；`--check` 核对该 URL 的当前内容，不声称它固定到 commit。",
        "",
        "Simple Icons 的条目同时记录品牌来源；Devicon 与 vscode-icons 是社区维护的图标集合，不能据此推定官方背书。Icons8 是第三方图标来源，也不代表相应软件厂商背书。",
        "Batch 齿轮是与 bat 文件类型关联的社区图标，不是 Microsoft 官方 Logo。",
        "Adobe 条目来自官方产品资产地址，其品牌资产与商标权仍归 Adobe；这不等同于开源授权。",
        "三份上游许可证文本分别保存在 `LICENSE.simple-icons.txt`、`LICENSE.devicon.txt` 和 `LICENSE.vscode-icons.txt`。Icons8 使用免费署名条款，不冒充开源许可证；品牌、商标及个别图标的附加许可仍需遵守。",
        "",
        "| 条目 | 本地文件 | 实际抓取文件 | 品牌/项目来源 | 许可与权利说明 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for entry in resolved_entries():
        record = records[entry["id"]]
        guidelines = record["guidelines"]
        brand = f'[上游]({record["brand"]})'
        if guidelines:
            brand += f' / [品牌规范]({guidelines})'
        source_label = "Icons8 来源页" if record["provider"] == "Icons8" else f'{record["provider"]} SVG'
        lines.append(
            f'| {entry["name"]} | `{entry["id"]}.svg` | '
            f'[{source_label}]({record["url"]}) | {brand} | {record["license"]} |'
        )
    lines.extend([
        "",
        "## 尚待核验",
        "",
        "以下条目没有写入图标文件，也没有使用相近品牌或通用终端图形代替：",
        "",
    ])
    for entry in pending_entries():
        lines.append(f'- **{entry["name"]}**：可信独立 SVG 来源、版本语义和许可仍待专项核验。')
    lines.extend([
        "",
        "## 重新抓取与检查",
        "",
        "```bash",
        "# 默认 dry-run：下载并在内存中验证，不写文件",
        "python scripts/fetch_tech_arsenal.py",
        "",
        "# 写入格式化图标、许可证、来源表和静态预览",
        "python scripts/fetch_tech_arsenal.py --apply",
        "",
        "# 联网核对本地文件是否仍与声明的上游一致，不写文件",
        "python scripts/fetch_tech_arsenal.py --check",
        "```",
        "",
    ])
    return "\n".join(lines)


def preview_html(icons, records):
    icons8_entries = [entry for entry in resolved_entries() if entry["provider"] == "Icons8"]
    attribution = ""
    if icons8_entries:
        links = "、".join(
            f'<a href="{escape(entry["url"], quote=True)}">{escape(entry["name"])}</a>'
            for entry in icons8_entries
        )
        attribution = f'<br>{links} 图标由 <a href="https://icons8.com">Icons8</a> 提供；本地 SVG 为派生路径。'

    def panel(theme):
        parts = [f'<section class="panel {theme}"><h2>{theme}</h2>']
        for row in ROWS:
            parts.append('<div class="stack-row">')
            for entry in row:
                identifier = entry["id"]
                name = escape(entry["name"])
                if identifier in icons:
                    url = escape(records[identifier]["url"], quote=True)
                    parts.append(
                        f'<a class="cell" href="{url}" title="{name} · 查看声明来源">'
                        f'{icons[identifier]}<span>{name}</span></a>'
                    )
                else:
                    parts.append(
                        f'<div class="cell pending" title="{name} · 待核验">'
                        f'<div class="missing">?</div><span>{name}</span></div>'
                    )
            parts.append("</div>")
        parts.append("</section>")
        return "".join(parts)

    return f'''<!doctype html>
<html lang="zh-CN">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>技术栈图标 · 来源与单色预览</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 32px; background: #e9edf0; color: #26343d; font: 14px/1.5 system-ui, sans-serif; }}
  header {{ max-width: 1540px; margin: 0 auto 24px; }}
  h1 {{ margin: 0; font-size: 22px; font-weight: 600; }}
  header p {{ margin: 7px 0 0; color: #5b6972; }}
  .panels {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; max-width: 1540px; margin: auto; }}
  .panel {{ padding: 24px 16px 28px; }}
  .panel.light {{ background: #fff; color: #40515b; }}
  .panel.dark {{ background: #090c11; color: #aebcc5; }}
  .panel h2 {{ margin: 0 0 24px 8px; font-size: 13px; font-weight: 500; }}
  .stack-row {{ display: flex; justify-content: center; gap: 4px; min-height: 74px; }}
  .cell {{ display: flex; width: 68px; min-width: 0; height: 72px; flex-direction: column; align-items: center; gap: 7px; color: inherit; text-decoration: none; }}
  .cell svg, .missing {{ width: 46px; height: 46px; flex: none; }}
  .cell span {{ width: 76px; overflow: hidden; font-size: 10px; text-align: center; text-overflow: ellipsis; white-space: nowrap; }}
  .missing {{ display: grid; place-items: center; border: 1px dashed currentColor; opacity: .32; font-size: 18px; }}
  .pending {{ opacity: .65; }}
  footer {{ max-width: 1540px; margin: 20px auto 0; color: #5b6972; font-size: 12px; }}
  @media (max-width: 1100px) {{ .panels {{ grid-template-columns: 1fr; }} }}
</style>
<header>
  <h1>技术栈图标 · 来源与单色预览</h1>
  <p>{len(records)} 枚已抓取或由本地派生源规范化，{len(pending_entries())} 枚明确留作待核验。点击已显示的图标可打开对应的声明来源。</p>
</header>
<div class="panels">{panel("light")}{panel("dark")}</div>
<footer>此页由 scripts/fetch_tech_arsenal.py 在构建期生成，无 JavaScript、外部字体或运行时请求。正式候选图标使用 currentColor；名称标签仅用于本预览，不进入最终纯图标矩阵。{attribution}</footer>
</html>
'''


def write_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(content, encoding="utf-8", newline="\n")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="从声明的上游抓取技术栈 SVG，安全检查后统一为 24×24 currentColor 图标。",
        epilog="""默认只预览，不写文件。下载内容仅在独立临时目录中解析，不执行其中任何代码。
示例：
  python scripts/fetch_tech_arsenal.py          下载、规范化并报告将写入的文件
  python scripts/fetch_tech_arsenal.py --apply  写入 assets/icons 和 preview/icons.html
  python scripts/fetch_tech_arsenal.py --check  联网核对本地文件，不写文件""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="全部来源验证成功后写入本地候选图标和文档")
    mode.add_argument("--check", action="store_true", help="联网核对本地文件与声明的上游是否一致")
    args = parser.parse_args()

    outputs = build_outputs()
    if args.check:
        differences = [
            path for path, content in outputs.items()
            if not path.is_file() or path.read_text(encoding="utf-8") != content
        ]
        actual_icons = {path.name for path in ICON_DIR.glob("*.svg")}
        expected_icons = {f'{entry["id"]}.svg' for entry in resolved_entries()}
        unexpected = sorted(actual_icons - expected_icons)
        if differences or unexpected:
            for path in differences:
                print(f"check: {path.relative_to(ROOT)} missing or outdated")
            for filename in unexpected:
                print(f"check: unexpected local icon assets/icons/{filename}")
            raise SystemExit(1)
        print(f"check: {len(outputs)} files match declared upstream sources  success")
        return
    if args.apply:
        for path, content in outputs.items():
            write_text(path, content)
            print(f"write: {path.relative_to(ROOT)}  success")
        print(
            f"summary: {len(resolved_entries())} icons written; "
            f"{len(pending_entries())} entries remain explicitly pending  success"
        )
    else:
        print(f"dry-run: {len(outputs)} files validated; no files changed; add --apply to write")


if __name__ == "__main__":
    main()
