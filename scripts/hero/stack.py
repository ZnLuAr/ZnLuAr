"""Load normalized local icons and lay out the static Hero technology matrix."""

import xml.etree.ElementTree as ET
from pathlib import Path

from icon_manifest import ROWS, resolved_entries

ROOT = Path(__file__).resolve().parents[2]
ICON_DIR = ROOT / "assets" / "icons"
SVG_NS = "http://www.w3.org/2000/svg"
STACK_CENTER_X = 980
STACK_CENTER_Y = 458
STACK_HEADING = "TECH ARSENAL"
STACK_HEADING_Y = 118
STACK_CELL_WIDTH = 142
STACK_CELL_HEIGHT = 144
STACK_ICON_SIZE = 128
STACK_SAFE_X = (400, 1550)


def local_name(tag):
    return tag.rsplit("}", 1)[-1]


def without_namespace(element):
    element.tag = local_name(element.tag)
    for child in element:
        without_namespace(child)
    return element


def load_stack():
    """Return validated inner SVG geometry; the renderer supplies the theme ink."""
    icons = {}
    for entry in resolved_entries():
        path = ICON_DIR / f'{entry["id"]}.svg'
        source = path.read_text(encoding="utf-8")
        if any(token in source.upper() for token in ("<!DOCTYPE", "<!ENTITY")) or "\x00" in source:
            raise ValueError(f"Unsafe local icon source: {path.name}")
        root = ET.fromstring(source)
        if local_name(root.tag) != "svg" or root.attrib.get("viewBox") != "0 0 24 24":
            raise ValueError(f"Local icon must use the common 24x24 viewBox: {path.name}")
        if root.attrib.get("fill") != "currentColor":
            raise ValueError(f"Local icon must remain theme-neutral: {path.name}")
        for element in root.iter():
            if local_name(element.tag) not in ("svg", "title", "g", "path", "circle"):
                raise ValueError(f"Unsupported element in local icon {path.name}: {element.tag}")
            for attribute, value in element.attrib.items():
                attribute = local_name(attribute)
                if attribute.startswith("on") or attribute in ("style", "href", "class"):
                    raise ValueError(f"Unsupported attribute in local icon {path.name}: {attribute}")
                if attribute == "fill" and value not in ("none", "currentColor"):
                    raise ValueError(f"Unsupported fill in local icon: {path.name}")
                if attribute == "fill-opacity":
                    raise ValueError(f"Fill opacity is not used in local icons: {path.name}")
                if attribute == "stroke" and value not in ("none", "currentColor"):
                    raise ValueError(f"Unsupported stroke in local icon: {path.name}")
                if "url(" in value.lower() or "https://" in value or "http://" in value:
                    raise ValueError(f"External reference in local icon: {path.name}")
        geometry = "".join(
            ET.tostring(without_namespace(child), encoding="unicode", short_empty_elements=True)
            for child in root
            if local_name(child.tag) != "title"
        )
        icons[entry["id"]] = {"name": entry["name"], "geometry": geometry}
    return icons


def stack_layout():
    """Compact missing entries and center each resolved row without visible placeholders."""
    placements = []
    for row_index, row in enumerate(ROWS):
        available = [entry for entry in row if entry["provider"]]
        center_y = STACK_CENTER_Y + (row_index - (len(ROWS) - 1) / 2) * STACK_CELL_HEIGHT
        for column, entry in enumerate(available):
            center_x = STACK_CENTER_X + (column - (len(available) - 1) / 2) * STACK_CELL_WIDTH
            x = center_x - STACK_ICON_SIZE / 2
            y = center_y - STACK_ICON_SIZE / 2
            if x < STACK_SAFE_X[0] or x + STACK_ICON_SIZE > STACK_SAFE_X[1]:
                raise ValueError(f'Technology icon outside the right safe area: {entry["id"]}')
            placements.append({
                "id": entry["id"],
                "name": entry["name"],
                "row": row_index,
                "column": column,
                "x": x,
                "y": y,
                "size": STACK_ICON_SIZE,
            })
    return placements


def stack_names():
    return [entry["name"] for entry in resolved_entries()]
