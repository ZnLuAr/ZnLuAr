import copy
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_hero import check_assets
from hero.scene import ASSET_DIR
from hero.stack import (
    STACK_CENTER_X,
    STACK_CENTER_Y,
    STACK_HEADING,
    STACK_HEADING_Y,
    STACK_ICON_SIZE,
    STACK_SAFE_X,
    load_stack,
    stack_layout,
)
from hero.svg_renderer import INSIGHTS_HEADING, STACK_SUBHEADING
from icon_manifest import pending_entries, resolved_entries

SVG_NS = "{http://www.w3.org/2000/svg}"
ASSETS = (
    "hero-light.svg",
    "hero-dark.svg",
    "hero-light-motion.svg",
    "hero-dark-motion.svg",
)


def technology_group(root, theme):
    return root.find(f".//{SVG_NS}g[@id='{theme}-stack']")


def stack_icons(group, theme):
    """The icon subgroups in document order, skipping the carousel fade wrapper."""
    prefix = f"{theme}-stack-"
    return [
        element
        for element in group.iter(f"{SVG_NS}g")
        if element is not group and str(element.attrib.get("id", "")).startswith(prefix)
    ]


def assert_closed_opacity_loop(test, group):
    """Every carousel animation in the group fades opacity and returns to its first value."""
    animates = group.findall(f".//{SVG_NS}animate")
    test.assertTrue(animates)
    for animate in animates:
        test.assertEqual(animate.attrib["attributeName"], "opacity")
        values = animate.attrib["values"].split(";")
        test.assertEqual(len(values), 9)
        test.assertEqual(values[0], values[-1])
        keys = animate.attrib["keyTimes"].split(";")
        test.assertEqual(keys[0], "0.000000")
        test.assertEqual(keys[-1], "1.000000")


def geometry_signature(group, theme):
    signature = []
    for icon in stack_icons(group, theme):
        identifier = icon.attrib["id"].removeprefix(f"{theme}-stack-")
        title = icon.find(f"{SVG_NS}title")
        geometry = "".join(
            ET.tostring(child, encoding="unicode")
            for child in icon
            if child is not title
        )
        signature.append((identifier, icon.attrib["transform"], title.text, geometry))
    return signature


class HeroStackTests(unittest.TestCase):
    def test_compact_layout_centers_only_verified_icons_in_the_right_safe_area(self):
        placements = stack_layout()
        self.assertEqual(len(placements), len(resolved_entries()))
        self.assertEqual([placement["id"] for placement in placements], [entry["id"] for entry in resolved_entries()])
        counts = Counter(p["row"] for p in placements)
        self.assertEqual([counts[row] for row in range(4)], [8, 7, 6, 8])
        self.assertEqual(STACK_ICON_SIZE, 128)
        self.assertEqual(next(p["row"] for p in placements if p["id"] == "batch"), 0)
        self.assertEqual(next(p["row"] for p in placements if p["id"] == "markdown"), 0)
        self.assertEqual(next(p["row"] for p in placements if p["id"] == "vb6"), 0)
        self.assertEqual(next(p["row"] for p in placements if p["id"] == "flstudio"), 3)
        self.assertNotIn("powershell", {p["id"] for p in placements})
        self.assertNotIn("androidstudio", {p["id"] for p in placements})
        pending = {entry["id"] for entry in pending_entries()}
        self.assertTrue(pending.isdisjoint(placement["id"] for placement in placements))
        row_widths = []
        for row in range(4):
            icons = [p for p in placements if p["row"] == row]
            row_widths.append(max(p["x"] + p["size"] for p in icons) - min(p["x"] for p in icons))
        self.assertEqual(row_widths[0], row_widths[3])
        self.assertGreater(row_widths[0], row_widths[1])
        self.assertGreater(row_widths[1], row_widths[2])
        for placement in placements:
            with self.subTest(icon=placement["id"]):
                self.assertGreaterEqual(placement["x"], STACK_SAFE_X[0])
                self.assertLessEqual(placement["x"] + STACK_ICON_SIZE, STACK_SAFE_X[1])
                self.assertGreaterEqual(placement["y"], 0)
                self.assertLessEqual(placement["y"] + STACK_ICON_SIZE, 900)
        for row in range(4):
            centers = [p["x"] + p["size"] / 2 for p in placements if p["row"] == row]
            self.assertAlmostEqual(sum(centers) / len(centers), STACK_CENTER_X)
        row_centers = [
            next(p["y"] + p["size"] / 2 for p in placements if p["row"] == row)
            for row in range(4)
        ]
        self.assertAlmostEqual(sum(row_centers) / len(row_centers), STACK_CENTER_Y)

    def test_every_hero_inlines_the_same_static_icons_without_visible_labels(self):
        expected = [entry["id"] for entry in resolved_entries()]
        for filename in ASSETS:
            theme = "dark" if "dark" in filename else "light"
            with self.subTest(filename=filename):
                root = ET.fromstring((ASSET_DIR / filename).read_text(encoding="utf-8"))
                group = technology_group(root, theme)
                self.assertIsNotNone(group)
                icons = stack_icons(group, theme)
                self.assertEqual([icon.attrib["id"].removeprefix(f"{theme}-stack-") for icon in icons], expected)
                self.assertIsNone(group.find(f".//{SVG_NS}text"))
                for icon in icons:
                    self.assertIsNotNone(icon.find(f"{SVG_NS}title"))
                    self.assertIsNotNone(icon.find(f".//{SVG_NS}path"))
                if "motion" in filename:
                    self.assertEqual(len(group.findall(f".//{SVG_NS}animate")), 1)
                    assert_closed_opacity_loop(self, group)
                else:
                    self.assertIsNone(group.find(f".//{SVG_NS}animate"))
                lightroom = group.find(f".//{SVG_NS}g[@id='{theme}-stack-lightroom']")
                path = lightroom.find(f".//{SVG_NS}path")
                self.assertEqual(path.attrib["fill-rule"], "evenodd")
                self.assertEqual(path.attrib["d"].count("M"), 4)
                batch = group.find(f".//{SVG_NS}g[@id='{theme}-stack-batch']")
                self.assertEqual(len(batch.findall(f".//{SVG_NS}circle")), 8)
                self.assertIsNotNone(batch.find(f".//{SVG_NS}g[@stroke='currentColor']"))
                self.assertTrue(group.attrib["color"].startswith("rgb("))
                vb6 = group.find(f".//{SVG_NS}g[@id='{theme}-stack-vb6']")
                self.assertGreater(vb6.find(f".//{SVG_NS}path").attrib["d"].count("M"), 10)
                flstudio = group.find(f".//{SVG_NS}g[@id='{theme}-stack-flstudio']")
                flstudio_paths = flstudio.findall(f".//{SVG_NS}path")
                self.assertEqual(len(flstudio_paths), 2)
                main, detail = flstudio_paths
                self.assertEqual(main.attrib["fill-rule"], "evenodd")
                self.assertEqual(detail.attrib["fill"], "none")
                self.assertEqual(detail.attrib["stroke"], "currentColor")
                self.assertEqual(detail.attrib["stroke-width"], "1.6")
                self.assertTrue(main.attrib["d"].endswith(detail.attrib["d"]))
                self.assertNotIn("fill-opacity", detail.attrib)
                self.assertIsNone(flstudio.find(f".//{SVG_NS}image"))

    def test_heading_is_separate_from_the_replaceable_static_icon_matrix(self):
        first_icon_y = min(placement["y"] for placement in stack_layout())
        for filename in ASSETS:
            theme = "dark" if "dark" in filename else "light"
            motion = "motion" in filename
            with self.subTest(filename=filename):
                root = ET.fromstring((ASSET_DIR / filename).read_text(encoding="utf-8"))
                heading = root.find(f"{SVG_NS}g[@id='{theme}-stack-heading']")
                self.assertIsNotNone(heading)
                labels = heading.findall(f".//{SVG_NS}text")
                expected_labels = (
                    [STACK_HEADING, STACK_SUBHEADING, INSIGHTS_HEADING]
                    if motion
                    else [STACK_HEADING, STACK_SUBHEADING]
                )
                self.assertEqual([label.text for label in labels], expected_labels)
                for label in labels:
                    self.assertEqual(label.attrib["x"], str(STACK_CENTER_X))
                    self.assertEqual(label.attrib["text-anchor"], "middle")
                    self.assertIn("monospace", label.attrib["font-family"])
                    self.assertNotIn("href", label.attrib)
                self.assertEqual(labels[0].attrib["y"], str(STACK_HEADING_Y))
                subheading_y = int(labels[1].attrib["y"])
                self.assertLess(STACK_HEADING_Y, subheading_y)
                self.assertLess(subheading_y, first_icon_y)
                if motion:
                    self.assertEqual(len(heading.findall(f".//{SVG_NS}animate")), 2)
                    assert_closed_opacity_loop(self, heading)
                else:
                    self.assertIsNone(heading.find(f".//{SVG_NS}animate"))
                self.assertIsNone(technology_group(root, theme).find(f".//{SVG_NS}text"))
                self.assertIn(STACK_HEADING, root.find(f"{SVG_NS}desc").text)
                if motion:
                    self.assertIn(INSIGHTS_HEADING, root.find(f"{SVG_NS}desc").text)

    def test_all_four_themes_and_motion_variants_share_icon_geometry(self):
        signatures = []
        for filename in ASSETS:
            theme = "dark" if "dark" in filename else "light"
            root = ET.fromstring((ASSET_DIR / filename).read_text(encoding="utf-8"))
            signatures.append(geometry_signature(technology_group(root, theme), theme))
        self.assertTrue(all(signature == signatures[0] for signature in signatures[1:]))

    def test_svg_descriptions_and_readme_alts_name_the_actual_icons(self):
        descriptions = [
            ET.fromstring((ASSET_DIR / filename).read_text(encoding="utf-8"))
            .find(f"{SVG_NS}desc").text
            for filename in ASSETS
        ]
        alts = []
        for filename in ("README.md", "README.zh-CN.md"):
            content = (ROOT / filename).read_text(encoding="utf-8")
            alts.append(re.search(r'<img[^>]+alt="([^"]+)"', content).group(1))
        for entry in resolved_entries():
            with self.subTest(icon=entry["id"]):
                for text in descriptions + alts:
                    self.assertIn(entry["name"], text)

    def test_changed_local_icon_geometry_marks_all_hero_assets_outdated(self):
        altered = copy.deepcopy(load_stack())
        altered["python"]["geometry"] = altered["python"]["geometry"].replace(
            "<path", '<path data-build-check="changed"', 1
        )
        with patch("build_hero.load_stack", return_value=altered):
            self.assertEqual(set(check_assets()), set(ASSETS))


if __name__ == "__main__":
    unittest.main()
