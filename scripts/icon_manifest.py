"""Declarative technology order and upstream sources shared by fetching and rendering."""

SIMPLE_ICONS_COMMIT = "17cd4ee07612198a1d8777a060d4100423762a8b"
DEVICON_COMMIT = "32fe1d3b3f36ad11f90ab94f7db59738139c2bf6"
SIMPLE_ICONS_BASE = (
    "https://raw.githubusercontent.com/simple-icons/simple-icons/"
    f"{SIMPLE_ICONS_COMMIT}"
)
DEVICON_BASE = (
    "https://raw.githubusercontent.com/devicons/devicon/"
    f"{DEVICON_COMMIT}"
)
VSCODE_ICONS_COMMIT = "1b9bfb20a20ca0d7d5bba5b381f4889cff55675b"
VSCODE_ICONS_BASE = (
    "https://raw.githubusercontent.com/vscode-icons/vscode-icons/"
    f"{VSCODE_ICONS_COMMIT}"
)
LIGHTROOM_URL = "https://www.adobe.com/cc-shared/assets/img/product-icons/svg/lightroom-classic-64.svg"


def simple(identifier, name, slug, source_title=None):
    return {
        "id": identifier,
        "name": name,
        "provider": "Simple Icons",
        "slug": slug,
        "source_title": source_title or name,
    }


def devicon(identifier, name, path, brand):
    return {
        "id": identifier,
        "name": name,
        "provider": "Devicon",
        "path": path,
        "brand": brand,
    }


def vscode_icon(identifier, name, path, conversion):
    return {
        "id": identifier,
        "name": name,
        "provider": "vscode-icons",
        "path": path,
        "brand": "https://github.com/vscode-icons/vscode-icons",
        "conversion": conversion,
        "license": "vscode-icons MIT；社区文件类型图标，非 Microsoft 官方 Batch Logo",
    }


def icons8(identifier, name, url, raster_sha256, conversion=None):
    return {
        "id": identifier,
        "name": name,
        "provider": "Icons8",
        "url": url,
        "brand": url,
        "local_source": f"sources/{identifier}.svg",
        "raster_source": f"sources/{identifier}-100.png",
        "raster_sha256": raster_sha256,
        "conversion": conversion,
        "license": "Icons8 免费署名使用；README 与预览保留来源链接；本地 SVG 为派生路径，商标权利仍归原权利人",
    }


def adobe(identifier, name, url, brand, conversion):
    return {
        "id": identifier,
        "name": name,
        "provider": "Adobe",
        "url": url,
        "brand": brand,
        "conversion": conversion,
        "license": "官方品牌资产；Adobe 商标权利保留，未附加开源许可",
    }


def pending(identifier, name):
    return {"id": identifier, "name": name, "provider": None}


ROWS = [
    [
        simple("python", "Python", "python"),
        simple("go", "Go", "go"),
        devicon("java", "Java", "java/java-plain.svg", "https://www.oracle.com/java/"),
        simple("rust", "Rust", "rust"),
        simple("bash", "Bash", "gnubash", "GNU Bash"),
        icons8(
            "vb6",
            "VB6",
            "https://icons8.com/icons/set/microsoft-visual-basic-6",
            "14a081bde00905547ec71536c4bd0860e5cc3bae21a7817def831e7da5ff8122",
        ),
        vscode_icon("batch", "Batch", "icons/file_type_bat.svg", "batch-strokes"),
        pending("vbscript", "VBScript"),
        simple("markdown", "Markdown", "markdown"),
    ],
    [
        simple("git", "Git", "git"),
        simple("github", "GitHub", "github"),
        pending("make", "GNU Make"),
        simple("docker", "Docker", "docker"),
        simple("jenkins", "Jenkins", "jenkins"),
        simple("caddy", "Caddy", "caddy"),
        simple("prometheus", "Prometheus", "prometheus"),
        simple("grafana", "Grafana", "grafana"),
    ],
    [
        simple("latex", "LaTeX", "latex"),
        simple("sqlite", "SQLite", "sqlite"),
        simple("mysql", "MySQL", "mysql"),
        simple("postgresql", "PostgreSQL", "postgresql"),
        simple("debian", "Debian", "debian"),
        simple("ubuntu", "Ubuntu", "ubuntu"),
        pending("msdos", "MS-DOS"),
    ],
    [
        simple("vim", "Vim", "vim"),
        devicon(
            "vscode",
            "VS Code",
            "vscode/vscode-plain.svg",
            "https://github.com/microsoft/vscode",
        ),
        icons8(
            "flstudio",
            "FL Studio",
            "https://icons8.com/icon/33042/fl-studio",
            "b42a74520a49d56eb1dafd49d1f8c033541677f24b7607b3cc0c325320124a9f",
            conversion="flstudio-detail-outline",
        ),
        simple("blender", "Blender", "blender"),
        adobe(
            "lightroom",
            "Lightroom Classic",
            LIGHTROOM_URL,
            "https://www.adobe.com/products/photoshop-lightroom-classic.html",
            "evenodd-cutout",
        ),
        devicon(
            "photoshop",
            "Photoshop",
            "photoshop/photoshop-plain.svg",
            "https://www.adobe.com/products/photoshop.html",
        ),
        devicon(
            "aftereffects",
            "After Effects",
            "aftereffects/aftereffects-plain.svg",
            "https://www.adobe.com/products/aftereffects.html",
        ),
        devicon(
            "dreamweaver",
            "Dreamweaver",
            "dreamweaver/dreamweaver-plain.svg",
            "https://www.adobe.com/products/dreamweaver.html",
        ),
        pending("flash", "Adobe Flash"),
    ],
]


def entries():
    return [entry for row in ROWS for entry in row]


def resolved_entries():
    return [entry for entry in entries() if entry["provider"]]


def pending_entries():
    return [entry for entry in entries() if not entry["provider"]]


def source_url(entry):
    if entry["provider"] == "Simple Icons":
        return f'{SIMPLE_ICONS_BASE}/icons/{entry["slug"]}.svg'
    if entry["provider"] == "Devicon":
        return f'{DEVICON_BASE}/icons/{entry["path"]}'
    if entry["provider"] == "vscode-icons":
        return f'{VSCODE_ICONS_BASE}/{entry["path"]}'
    if entry["provider"] in ("Adobe", "Icons8"):
        return entry["url"]
    raise ValueError(f'No upstream source declared for {entry["id"]}')
