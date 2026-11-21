import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from fetch_tech_arsenal import (
    DEVICON_COMMIT,
    ICON_DIR,
    PREVIEW_PATH,
    ROWS,
    SIMPLE_ICONS_COMMIT,
    SOURCES_PATH,
    VSCODE_ICONS_COMMIT,
    entries,
    normalize_svg,
    pending_entries,
    resolved_entries,
    source_url,
    verified_local_source,
)

SVG_NS = "{http://www.w3.org/2000/svg}"


class IconNormalizationTests(unittest.TestCase):
    def test_simple_icon_becomes_theme_neutral_without_rewriting_geometry(self):
        result = normalize_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
            '<title>Upstream</title><path fill="#123456" fill-rule="evenodd" d="M0 0h24v24z"/></svg>',
            "Example",
        )
        root = ET.fromstring(result)
        self.assertEqual(root.attrib["viewBox"], "0 0 24 24")
        self.assertEqual(root.attrib["fill"], "currentColor")
        self.assertEqual(root.find(f"{SVG_NS}title").text, "Example")
        path = root.find(f"{SVG_NS}path")
        self.assertEqual(path.attrib["d"], "M0 0h24v24z")
        self.assertEqual(path.attrib["fill-rule"], "evenodd")
        self.assertNotIn("fill", path.attrib)
        self.assertNotIn("#123456", result)

    def test_larger_viewbox_is_scaled_into_the_common_coordinate_system(self):
        result = normalize_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">'
            '<path fill="#000000" d="M1 2h3v4z"/></svg>',
            "Example",
        )
        root = ET.fromstring(result)
        group = root.find(f"{SVG_NS}g")
        self.assertIn("scale(0.1875)", group.attrib["transform"])
        self.assertEqual(group.find(f"{SVG_NS}path").attrib["d"], "M1 2h3v4z")

    def test_none_fill_is_preserved_as_negative_space(self):
        result = normalize_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
            '<path fill="none" d="M0 0h24v24z"/></svg>',
            "Example",
        )
        self.assertEqual(
            ET.fromstring(result).find(f"{SVG_NS}path").attrib["fill"],
            "none",
        )

    def test_multicolor_sources_are_not_destructively_flattened(self):
        source = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
            '<path fill="#000000" d="M0 0h1v1z"/><path fill="#ffffff" d="M1 1h1v1z"/></svg>'
        )
        with self.assertRaisesRegex(ValueError, "Multi-color"):
            normalize_svg(source, "Example")

    def test_lightroom_cutout_preserves_letters_as_negative_space(self):
        result = normalize_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            '<defs><clipPath id="unused"><rect width="64" height="64"/></clipPath></defs>'
            '<path id="tile" fill="#001E36" d="M0 0h64v64H0z"/>'
            '<path id="letter-l" fill="#31A8FF" d="M10 10h4v20h10v4H10z"/>'
            '<path id="letter-r" fill="#31A8FF" d="M28 20h4v14h-4z"/>'
            '<path id="letter-c" fill="#31A8FF" d="M40 20h12v4H44v10h8v4H40z"/>'
            '</svg>',
            "Lightroom Classic",
            "evenodd-cutout",
        )
        root = ET.fromstring(result)
        self.assertEqual(root.attrib["fill"], "currentColor")
        group = root.find(f"{SVG_NS}g")
        self.assertIn("scale(0.375)", group.attrib["transform"])
        path = group.find(f"{SVG_NS}path")
        self.assertEqual(path.attrib["fill-rule"], "evenodd")
        self.assertEqual(path.attrib["d"].count("M"), 4)
        self.assertNotIn("defs", result)
        self.assertNotIn("id=", result)
        self.assertNotIn("#001E36", result)
        self.assertNotIn("#31A8FF", result)

    def test_lightroom_cutout_rejects_unexpected_source_structure(self):
        source = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            '<path fill="#001E36" d="M0 0h64v64H0z"/>'
            '<path fill="#31A8FF" d="M10 10h4v20h10v4H10z"/>'
            '<path fill="#ffffff" d="M28 20h4v14h-4z"/>'
            '<path fill="#31A8FF" d="M40 20h12v4H44v10h8v4H40z"/>'
            '</svg>'
        )
        with self.assertRaisesRegex(ValueError, "Unexpected Lightroom"):
            normalize_svg(source, "Lightroom Classic", "evenodd-cutout")

    def test_batch_conversion_preserves_gear_and_eight_theme_neutral_circle_strokes(self):
        circles = "".join(
            f'<circle cx="{8 + index}" cy="12" r="4" stroke-width="1.5"/>'
            for index in range(8)
        )
        result = normalize_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
            '<defs><radialGradient id="a"><stop offset="0" stop-color="#bedcdc"/></radialGradient></defs>'
            '<path fill="silver" d="M1 1h4v4H1z"/>'
            f'<g fill="none" stroke="url(#a)">{circles}</g></svg>',
            "Batch",
            "batch-strokes",
        )
        root = ET.fromstring(result)
        container = root.find(f"{SVG_NS}g")
        self.assertIn("scale(0.75)", container.attrib["transform"])
        self.assertEqual(container.find(f"{SVG_NS}path").attrib["d"], "M1 1h4v4H1z")
        stroke_group = container.find(f"{SVG_NS}g")
        self.assertEqual(stroke_group.attrib["stroke"], "currentColor")
        self.assertEqual(stroke_group.attrib["fill"], "none")
        self.assertEqual(len(stroke_group.findall(f"{SVG_NS}circle")), 8)
        self.assertNotIn("defs", result)
        self.assertNotIn("url(", result)
        self.assertNotIn("stop-color", result)

    def test_active_or_external_svg_content_is_rejected(self):
        sources = (
            '<!DOCTYPE svg><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M0 0h1v1z"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><script>alert(1)</script><path d="M0 0h1v1z"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><image href="https://example.com/a.png"/><path d="M0 0h1v1z"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path onclick="alert(1)" d="M0 0h1v1z"/></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path stroke="#000" d="M0 0h1v1z"/></svg>',
        )
        for source in sources:
            with self.subTest(source=source[:50]), self.assertRaises(ValueError):
                normalize_svg(source, "Example")


class IconManifestTests(unittest.TestCase):
    def test_layout_contains_all_entries_in_the_approved_horizontal_rhythm(self):
        self.assertEqual([len(row) for row in ROWS], [9, 8, 7, 9])
        all_entries = entries()
        self.assertEqual(len(all_entries), 33)
        self.assertEqual(len(resolved_entries()), 29)
        self.assertEqual(len(pending_entries()), 4)
        identifiers = [entry["id"] for entry in all_entries]
        self.assertEqual(len(identifiers), len(set(identifiers)))

    def test_downloads_are_https_and_versions_are_described_accurately(self):
        for entry in resolved_entries():
            with self.subTest(icon=entry["id"]):
                url = source_url(entry)
                self.assertTrue(url.startswith("https://"))
                if entry["provider"] == "Simple Icons":
                    self.assertTrue(url.startswith("https://raw.githubusercontent.com/"))
                    self.assertIn(SIMPLE_ICONS_COMMIT, url)
                elif entry["provider"] == "Devicon":
                    self.assertTrue(url.startswith("https://raw.githubusercontent.com/"))
                    self.assertIn(DEVICON_COMMIT, url)
                elif entry["provider"] == "vscode-icons":
                    self.assertTrue(url.startswith("https://raw.githubusercontent.com/"))
                    self.assertIn(VSCODE_ICONS_COMMIT, url)
                    self.assertEqual(entry["conversion"], "batch-strokes")
                elif entry["provider"] == "Icons8":
                    self.assertEqual(url, entry["url"])
                    self.assertTrue(url.startswith("https://icons8.com/"))
                    self.assertEqual(entry["local_source"], f'sources/{entry["id"]}.svg')
                    self.assertTrue(verified_local_source(entry).startswith(b"<svg"))
                else:
                    self.assertEqual(entry["provider"], "Adobe")
                    self.assertTrue(url.startswith("https://www.adobe.com/"))
                    self.assertEqual(entry["conversion"], "evenodd-cutout")

    def test_pending_entries_do_not_get_placeholder_assets(self):
        for entry in pending_entries():
            with self.subTest(icon=entry["id"]):
                self.assertFalse((ICON_DIR / f'{entry["id"]}.svg').exists())


class LocalIconOutputTests(unittest.TestCase):
    def test_local_icons_match_the_manifest_and_remain_self_contained(self):
        expected = {f'{entry["id"]}.svg' for entry in resolved_entries()}
        actual = {path.name for path in ICON_DIR.glob("*.svg")}
        self.assertEqual(actual, expected)
        for entry in resolved_entries():
            with self.subTest(icon=entry["id"]):
                content = (ICON_DIR / f'{entry["id"]}.svg').read_text(encoding="utf-8")
                root = ET.fromstring(content)
                self.assertEqual(root.attrib["viewBox"], "0 0 24 24")
                self.assertEqual(root.attrib["fill"], "currentColor")
                self.assertEqual(root.find(f"{SVG_NS}title").text, entry["name"])
                self.assertIsNotNone(root.find(f".//{SVG_NS}path"))
                self.assertNotIn("<script", content)
                self.assertNotIn("<style", content)
                self.assertNotIn("http://", content.replace('xmlns="http://www.w3.org/2000/svg"', ""))
                self.assertNotIn("https://", content)

    def test_icons8_derivations_are_checksum_pinned_real_vector_paths(self):
        derived = [entry for entry in resolved_entries() if entry["provider"] == "Icons8"]
        self.assertEqual({entry["id"] for entry in derived}, {"vb6", "flstudio"})
        for entry in derived:
            with self.subTest(icon=entry["id"]):
                source = verified_local_source(entry)
                root = ET.fromstring(source)
                self.assertIsNotNone(root.find(f"{SVG_NS}path"))
                self.assertIsNone(root.find(f".//{SVG_NS}image"))
                self.assertNotIn("base64", source.decode("utf-8"))
                normalized = (ICON_DIR / f'{entry["id"]}.svg').read_text(encoding="utf-8")
                self.assertEqual(
                    normalized,
                    normalize_svg(source, entry["name"], entry.get("conversion")),
                )
                if entry["id"] == "flstudio":
                    paths = ET.fromstring(normalized).findall(f".//{SVG_NS}path")
                    self.assertEqual(len(paths), 2)
                    main, detail = paths
                    self.assertEqual(main.attrib["fill-rule"], "evenodd")
                    self.assertEqual(detail.attrib["fill"], "none")
                    self.assertEqual(detail.attrib["stroke"], "currentColor")
                    self.assertEqual(detail.attrib["stroke-width"], "1.6")
                    self.assertEqual(detail.attrib["d"].count("M"), 2)
                    self.assertTrue(main.attrib["d"].endswith(detail.attrib["d"]))
                    self.assertNotIn("fill-opacity", detail.attrib)

    def test_flstudio_detail_outline_rejects_changed_stroke_and_implicit_handling(self):
        entry = next(entry for entry in resolved_entries() if entry["id"] == "flstudio")
        source = verified_local_source(entry).decode("utf-8")
        changed = source.replace('stroke-width="1.6"', 'stroke-width="2.0"')
        with self.assertRaisesRegex(ValueError, "detail geometry or stroke"):
            normalize_svg(changed, entry["name"], entry["conversion"])
        with self.assertRaisesRegex(ValueError, "Stroked source"):
            normalize_svg(source, entry["name"])

    def test_icons8_checksum_rejects_a_changed_raster_source(self):
        entry = next(entry for entry in resolved_entries() if entry["id"] == "vb6")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "sources").mkdir()
            (root / entry["local_source"]).write_bytes(
                (ICON_DIR / entry["local_source"]).read_bytes()
            )
            (root / entry["raster_source"]).write_bytes(b"changed raster")
            with patch("fetch_tech_arsenal.ICON_DIR", root):
                with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                    verified_local_source(entry)

    def test_sources_and_static_preview_explain_the_declared_sources(self):
        sources = SOURCES_PATH.read_text(encoding="utf-8")
        preview = PREVIEW_PATH.read_text(encoding="utf-8")
        self.assertIn(SIMPLE_ICONS_COMMIT, sources)
        self.assertIn(DEVICON_COMMIT, sources)
        self.assertIn(VSCODE_ICONS_COMMIT, sources)
        self.assertIn("尚待核验", sources)
        self.assertIn("https://icons8.com/license", sources)
        self.assertIn("不把位图嵌入 SVG", sources)
        self.assertIn("flstudio-detail-outline", sources)
        self.assertIn('stroke-width="1.6"', sources)
        self.assertIn("来源与单色预览", preview)
        for entry in resolved_entries():
            if entry["provider"] == "Icons8":
                self.assertIn(entry["raster_sha256"], sources)
                self.assertIn(entry["name"], preview)
        self.assertIn("https://icons8.com", preview)
        self.assertNotIn("<script", preview)
        for entry in resolved_entries():
            with self.subTest(icon=entry["id"]):
                self.assertIn(source_url(entry), sources)
                icon = (ICON_DIR / f'{entry["id"]}.svg').read_text(encoding="utf-8")
                self.assertEqual(preview.count(icon), 2)
        for entry in pending_entries():
            self.assertIn(entry["name"], sources)
            self.assertIn(entry["name"], preview)

    def test_upstream_license_texts_are_kept_with_the_assets(self):
        simple_license = (ICON_DIR / "LICENSE.simple-icons.txt").read_text(encoding="utf-8")
        devicon_license = (ICON_DIR / "LICENSE.devicon.txt").read_text(encoding="utf-8")
        vscode_license = (ICON_DIR / "LICENSE.vscode-icons.txt").read_text(encoding="utf-8")
        self.assertIn("CC0 1.0 Universal", simple_license)
        self.assertIn("The MIT License", devicon_license)
        self.assertIn("Permission is hereby granted", devicon_license)
        self.assertIn("The MIT License", vscode_license)
        self.assertIn("vscode-icons Contributors", vscode_license)


if __name__ == "__main__":
    unittest.main()
