import re
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from adjust_scene import BLENDER_PATH, blender_camera, blender_cube, replace_block
from build_hero import check_assets, expected_assets
from build_themes import base_light_theme, invert_theme, lift_metal, theme_state
from hero.geometry import ground_from_screen
from hero.scene import ASSET_DIR, SCENE_PATH, THEMES_PATH, load_json
from hero.svg_renderer import ground_stops, ring_irradiance

STATIC_ASSETS = ("hero-light.svg", "hero-dark.svg")
MOTION_ASSETS = ("hero-light-motion.svg", "hero-dark-motion.svg")
ASSET_NAMES = STATIC_ASSETS + MOTION_ASSETS


def expected_picture_sources(prefix):
    return [
        {
            "media": f"(prefers-color-scheme: {scheme}){motion_query}",
            "srcset": f"{prefix}hero-{scheme}{suffix}.svg",
        }
        for motion_query, suffix in (
            (" and (prefers-reduced-motion: no-preference)", "-motion"),
            ("", ""),
        )
        for scheme in ("dark", "light")
    ]


def expected_preview_sources(prefix):
    return [
        {
            "media": "(prefers-reduced-motion: no-preference)",
            "srcset": f"{prefix}hero-{scheme}-motion.svg",
        }
        for scheme in ("light", "dark")
    ]


class ImageSources(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sources = []
        self.picture_sources = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "img":
            self.sources.append(attributes.get("src"))
        elif tag == "source":
            self.picture_sources.append(attributes)


class HeroOutputTests(unittest.TestCase):
    def test_generated_assets_match_current_persistent_state(self):
        outputs = expected_assets()
        self.assertEqual(set(outputs), set(ASSET_NAMES))
        for filename, content in outputs.items():
            with self.subTest(filename=filename):
                self.assertEqual((ASSET_DIR / filename).read_text(encoding="utf-8"), content)
        self.assertEqual(check_assets(), [])

    def test_theme_state_is_generated_from_its_script(self):
        self.assertEqual(load_json(THEMES_PATH), theme_state())

    def test_svgs_are_self_contained_and_accessible(self):
        for filename in ASSET_NAMES:
            with self.subTest(filename=filename):
                content = (ASSET_DIR / filename).read_text(encoding="utf-8")
                root = ET.fromstring(content)
                self.assertEqual(root.attrib["viewBox"], "0 0 1600 900")
                self.assertEqual(root.attrib["width"], "1600")
                self.assertEqual(root.attrib["height"], "900")
                self.assertEqual(root.attrib["role"], "img")
                self.assertIsNotNone(root.find("{http://www.w3.org/2000/svg}title"))
                self.assertIsNotNone(root.find("{http://www.w3.org/2000/svg}desc"))
                for element in root.iter():
                    local_name = element.tag.rsplit("}", 1)[-1]
                    self.assertNotIn(local_name, ("script", "foreignObject", "image"))
                    for attribute, value in element.attrib.items():
                        if attribute.rsplit("}", 1)[-1] == "href":
                            self.assertTrue(value.startswith("#"), value)
                self.assertGreater(content.count("<line "), 0)
                self.assertGreater(content.count("<polygon "), 0)

    def test_all_svg_ids_and_internal_references_resolve(self):
        for filename in ASSET_NAMES:
            with self.subTest(filename=filename):
                content = (ASSET_DIR / filename).read_text(encoding="utf-8")
                root = ET.fromstring(content)
                ids = [element.attrib["id"] for element in root.iter() if "id" in element.attrib]
                self.assertEqual(len(ids), len(set(ids)))
                for reference in re.findall(r"url\(#([^)]*)\)", content):
                    self.assertIn(reference, ids)
                for reference in root.attrib["aria-labelledby"].split():
                    self.assertIn(reference, ids)

    def test_ring_light_brightens_foreground_without_edge_fading(self):
        namespace = "{http://www.w3.org/2000/svg}"
        scene = load_json(SCENE_PATH)
        themes = theme_state()
        ring = themes["light"]["ringLight"]
        self.assertGreater(ring["radius"], 0)
        self.assertGreater(ring["heightAboveCamera"], 0)
        far = ground_from_screen(scene["width"] / 2, 0, scene)
        near = ground_from_screen(scene["width"] / 2, scene["height"], scene)
        self.assertGreater(ring_irradiance(near, scene, ring), ring_irradiance(far, scene, ring))

        ground = ground_stops(scene, themes["light"])
        self.assertEqual(len(ground), 17)
        self.assertEqual([offset for offset, _ in ground], sorted(offset for offset, _ in ground))
        self.assertTrue(all(int(color[index:index + 2], 16) >= 240 for _, color in ground for index in (1, 3, 5)))
        for name in themes:
            with self.subTest(theme=name):
                content = (ASSET_DIR / f"hero-{name}.svg").read_text(encoding="utf-8")
                self.assertNotIn("page-fade", content)
                self.assertNotIn("vignette", content)
                root = ET.fromstring(content)
                ground_rect = root.find(f"{namespace}rect")
                self.assertNotIn("mask", ground_rect.attrib)
                reflection = root.find(f".//{namespace}radialGradient[@id='{name}-ring-reflection']")
                self.assertIsNotNone(reflection)
                opacities = [float(stop.attrib["stop-opacity"]) for stop in reflection]
                self.assertEqual(opacities[0], 0)
                self.assertEqual(opacities[-1], 0)
                self.assertGreater(max(opacities), 0)

    def test_metal_lift_brightens_both_themes_from_the_same_inverse_base(self):
        themes = theme_state()
        base = base_light_theme()["metal"]
        expected = {
            "light": lift_metal(base),
            "dark": lift_metal(invert_theme(base)),
        }
        for name, base_metal in (("light", base), ("dark", invert_theme(base))):
            with self.subTest(theme=name):
                self.assertEqual(themes[name]["metal"], expected[name])
                for kind in base_metal:
                    base_offsets = [offset for offset, _ in base_metal[kind]]
                    actual_offsets = [offset for offset, _ in themes[name]["metal"][kind]]
                    self.assertEqual(actual_offsets, base_offsets)
                    for (_, base_color), (_, actual_color) in zip(base_metal[kind], themes[name]["metal"][kind]):
                        base_channels = [int(base_color[index:index + 2], 16) for index in (1, 3, 5)]
                        actual_channels = [int(actual_color[index:index + 2], 16) for index in (1, 3, 5)]
                        for before, after in zip(base_channels, actual_channels):
                            self.assertGreater(after, before)

    def test_dark_ring_exposure_lifts_every_ground_edge_to_page_color(self):
        scene = load_json(SCENE_PATH)
        themes = theme_state()
        light_ring = themes["light"]["ringLight"]
        dark_ring = themes["dark"]["ringLight"]
        self.assertEqual(dark_ring["radius"], light_ring["radius"])
        self.assertEqual(dark_ring["heightAboveCamera"], light_ring["heightAboveCamera"])
        self.assertGreater(dark_ring["intensity"], light_ring["intensity"])
        self.assertEqual(themes["dark"]["ambient"], 0)
        self.assertEqual(themes["dark"]["groundBase"], "#000000")
        self.assertEqual(themes["dark"]["groundLit"], "#090c11")

        dark_ground = ground_stops(scene, themes["dark"])
        for _, color in dark_ground:
            channels = [int(color[index:index + 2], 16) for index in (1, 3, 5)]
            for channel, expected in zip(channels, (9, 12, 17)):
                self.assertLessEqual(abs(channel - expected), 1)

        namespace = "{http://www.w3.org/2000/svg}"
        dark_content = (ASSET_DIR / "hero-dark.svg").read_text(encoding="utf-8")
        root = ET.fromstring(dark_content)
        gradient = root.find(f".//{namespace}linearGradient[@id='dark-ground']")
        self.assertEqual(gradient.attrib["gradientUnits"], "userSpaceOnUse")
        self.assertEqual(gradient.attrib["x1"], gradient.attrib["x2"])
        self.assertEqual(gradient.attrib["y1"], "0")
        self.assertEqual(gradient.attrib["y2"], str(scene["height"]))
        actual_stops = [[float(stop.attrib["offset"]), stop.attrib["stop-color"]] for stop in gradient]
        self.assertEqual(actual_stops, dark_ground)
        self.assertNotIn("-fog", dark_content)
        self.assertNotIn("page-fade", dark_content)

    def test_motion_svgs_play_precomputed_geometry_without_css_or_scripts(self):
        namespace = "{http://www.w3.org/2000/svg}"
        scene = load_json(SCENE_PATH)
        sample_count = max(abs(turns) for turns in scene["motion"]["turns"]) * 360 + 1
        for filename in STATIC_ASSETS:
            root = ET.fromstring((ASSET_DIR / filename).read_text(encoding="utf-8"))
            self.assertIsNone(root.find(f".//{namespace}animate"))
        for filename in MOTION_ASSETS:
            with self.subTest(filename=filename):
                content = (ASSET_DIR / filename).read_text(encoding="utf-8")
                root = ET.fromstring(content)
                self.assertNotIn("<style", content)
                self.assertNotIn("<script", content)
                face_animations = root.findall(f".//{namespace}polygon/{namespace}animate")
                self.assertEqual(len(face_animations), 6)
                for animation in face_animations:
                    self.assertEqual(animation.attrib["attributeName"], "points")
                    self.assertEqual(animation.attrib["calcMode"], "linear")
                line_animations = root.findall(f".//{namespace}line/{namespace}animate")
                self.assertGreater(len(line_animations), 0)
                self.assertEqual(len(line_animations) % 4, 0)
                visibility_animations = [
                    animation for animation in root.findall(f".//{namespace}animate")
                    if animation.attrib["attributeName"] == "visibility"
                ]
                self.assertEqual(len(visibility_animations), 6 + len(line_animations) // 4)
                for animation in face_animations + line_animations + visibility_animations:
                    values = animation.attrib["values"].split(";")
                    self.assertEqual(len(values), sample_count)
                    self.assertEqual(values[0], values[-1])
                    self.assertEqual(animation.attrib["dur"], f'{scene["motion"]["period_seconds"]}s')
                    self.assertEqual(animation.attrib["repeatCount"], "indefinite")

    def test_both_motion_themes_share_exactly_the_same_geometry_timeline(self):
        signatures = []
        for filename in MOTION_ASSETS:
            root = ET.fromstring((ASSET_DIR / filename).read_text(encoding="utf-8"))
            signatures.append([
                (animation.attrib["attributeName"], animation.attrib["values"])
                for animation in root.iter("{http://www.w3.org/2000/svg}animate")
            ])
        self.assertEqual(signatures[0], signatures[1])

    def test_preview_is_only_a_declarative_consumer(self):
        preview_path = ROOT / "preview" / "hero.html"
        content = preview_path.read_text(encoding="utf-8")
        for forbidden in ("<script", "<svg", "const CAM", "const CUBE", "GRID_", "innerHTML"):
            self.assertNotIn(forbidden, content)
        parser = ImageSources()
        parser.feed(content)
        self.assertEqual(
            parser.sources,
            ["../assets/hero/hero-light.svg", "../assets/hero/hero-dark.svg"],
        )
        self.assertEqual(parser.picture_sources, expected_preview_sources("../assets/hero/"))
        for source in parser.sources + [item["srcset"] for item in parser.picture_sources]:
            self.assertTrue((preview_path.parent / source).resolve().is_file(), source)
        self.assertIn('href="https://icons8.com/icons/set/microsoft-visual-basic-6"', content)
        self.assertIn('href="https://icons8.com/icon/33042/fl-studio"', content)
        self.assertIn('href="https://icons8.com">Icons8</a>', content)

    def test_both_readmes_prefer_motion_and_keep_static_fallbacks(self):
        for filename in ("README.md", "README.zh-CN.md"):
            with self.subTest(filename=filename):
                content = (ROOT / filename).read_text(encoding="utf-8")
                parser = ImageSources()
                parser.feed(content)
                self.assertEqual(content.count("<picture>"), 1)
                self.assertEqual(parser.picture_sources, expected_picture_sources("assets/hero/"))
                self.assertEqual(parser.sources, ["assets/hero/hero-light.svg"])
                self.assertRegex(content, r"<img[^>]+alt=\"[^\"]+\"")
                self.assertIn('href="https://icons8.com">Icons8</a>', content)
                self.assertNotIn("PowerShell", content)
                self.assertNotIn("Android Studio", content)

    def test_profile_content_blocks_keep_their_reading_order(self):
        expected = {
            "README.md": {
                "order": (
                    "Backend dev still lvling up",
                    ">About Me<",
                    "<picture>",
                    "<h2><samp>Now",
                    "Feeling my way forward",
                ),
            },
            "README.zh-CN.md": {
                "order": (
                    "仍在升级的后端",
                    ">关于我<",
                    "<picture>",
                    "<h2><samp>最近",
                    "……就像这样",
                ),
            },
        }
        for filename, profile in expected.items():
            with self.subTest(filename=filename):
                content = (ROOT / filename).read_text(encoding="utf-8")
                self.assertEqual(content.count("<h1"), 1)
                self.assertEqual(content.count("<table>"), 0)
                self.assertEqual(content.count("<tr>"), 0)
                self.assertGreaterEqual(content.count("<li><samp>"), 3)
                # <samp> 是 phrasing content，不得包住块级元素（h2/p 必须在外层）
                self.assertIsNone(re.search(r"<samp>\s*<h[1-6]", content))
                self.assertIsNone(re.search(r"<samp>\s*<p[ >]", content))
                positions = [content.index(value) for value in profile["order"]]
                self.assertEqual(positions, sorted(positions))
                self.assertLess(content.index("<h1"), positions[0])
                self.assertNotIn("style=", content)

    def test_blender_calibration_matches_persistent_scene(self):
        scene = load_json(SCENE_PATH)
        content = BLENDER_PATH.read_text(encoding="utf-8")
        content = replace_block(content, "CUBE", blender_cube(scene), BLENDER_PATH)
        content = replace_block(content, "CAMERA", blender_camera(scene), BLENDER_PATH)
        self.assertEqual(content, BLENDER_PATH.read_text(encoding="utf-8"))

    def test_build_check_cli_passes_without_writing(self):
        before = {path.name: path.read_text(encoding="utf-8") for path in ASSET_DIR.glob("*.svg")}
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build_hero.py"), "--check"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("up to date", result.stdout)
        after = {path.name: path.read_text(encoding="utf-8") for path in ASSET_DIR.glob("*.svg")}
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
