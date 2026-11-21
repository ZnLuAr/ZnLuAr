import copy
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_hero import check_assets
from fetch_wakatime import format_duration, snapshot_from_response
from hero.scene import ASSET_DIR
from hero.svg_renderer import wakatime_svg
from hero.wakatime import (
    MAX_EDITORS,
    MAX_LANGUAGES,
    MAX_OPERATING_SYSTEMS,
    RANGE_DAYS,
    load_wakatime,
    validate_wakatime,
    wakatime_view,
)

SVG_NS = "{http://www.w3.org/2000/svg}"
MOTION_ASSETS = ("hero-light-motion.svg", "hero-dark-motion.svg")
STATIC_ASSETS = ("hero-light.svg", "hero-dark.svg")


def make_snapshot(languages=2, editors=2, systems=1):
    def entries(prefix, count):
        return [
            {
                "name": f"{prefix} {index}",
                "percent": 100.0 if count == 1 else 100.0 / (index + 1),
                "text": f"{count - index} hrs 1 min",
            }
            for index in range(count)
        ]

    return {
        "placeholder": True,
        "fetched_at": "2026-11-20T08:30:00+00:00",
        "range": "last_7_days",
        "total": {"seconds": 3600, "text": "1 hrs 0 mins"},
        "daily_average": {"seconds": 514, "text": "0 hrs 9 mins"},
        "languages": entries("Language", languages),
        "editors": entries("Editor", editors),
        "operating_systems": entries("System", systems),
    }


def api_payload(languages=2, editors=2, systems=1, total=3600, daily=None, up_to_date=True):
    def entries(prefix, count):
        return [
            {
                "name": f"{prefix} {index}",
                "percent": 10.0 * (count - index),
                "total_seconds": 600,
            }
            for index in range(count)
        ]

    return {
        "data": {
            "is_up_to_date": up_to_date,
            "total_seconds": total,
            "total_seconds_including_other_language": total,
            "human_readable_total": "1 hrs 0 mins",
            "daily_average": daily,
            "human_readable_daily_average": "0 hrs 8 mins" if daily else None,
            "languages": entries("Language", languages),
            "editors": entries("Editor", editors),
            "operating_systems": entries("System", systems),
        }
    }


class ValidateWakaTimeTests(unittest.TestCase):
    def test_repository_snapshot_validates(self):
        snapshot = load_wakatime()
        self.assertIsNotNone(snapshot)
        self.assertIs(validate_wakatime(snapshot), snapshot)
        self.assertIsInstance(snapshot["placeholder"], bool)
        self.assertEqual(snapshot["range"], "last_7_days")

    def test_valid_snapshot_passes_for_both_ranges(self):
        for range_slug in RANGE_DAYS:
            snapshot = make_snapshot()
            snapshot["range"] = range_slug
            self.assertIs(validate_wakatime(snapshot), snapshot)

    def test_schema_is_closed(self):
        snapshot = make_snapshot()
        snapshot["projects"] = []
        with self.assertRaises(ValueError):
            validate_wakatime(snapshot)
        del snapshot["projects"]
        del snapshot["daily_average"]
        with self.assertRaises(ValueError):
            validate_wakatime(snapshot)

    def test_placeholder_flag_and_range_are_typed(self):
        snapshot = make_snapshot()
        snapshot["placeholder"] = "true"
        with self.assertRaises(ValueError):
            validate_wakatime(snapshot)
        snapshot["placeholder"] = True
        snapshot["range"] = "all_time"
        with self.assertRaises(ValueError):
            validate_wakatime(snapshot)

    def test_entry_percent_bounds(self):
        snapshot = make_snapshot()
        for percent, ok in ((0, False), (100, True), (100.01, False), (-1, False)):
            with self.subTest(percent=percent):
                broken = copy.deepcopy(snapshot)
                broken["languages"][0]["percent"] = percent
                if ok:
                    validate_wakatime(broken)
                else:
                    with self.assertRaises(ValueError):
                        validate_wakatime(broken)

    def test_entry_fields_are_closed_and_non_empty(self):
        snapshot = make_snapshot()
        snapshot["editors"][0]["extra"] = 1
        with self.assertRaises(ValueError):
            validate_wakatime(snapshot)
        del snapshot["editors"][0]["extra"]
        snapshot["editors"][0]["name"] = "  "
        with self.assertRaises(ValueError):
            validate_wakatime(snapshot)

    def test_lists_have_entry_limits(self):
        snapshot = make_snapshot(languages=MAX_LANGUAGES + 1)
        with self.assertRaises(ValueError):
            validate_wakatime(snapshot)
        snapshot = make_snapshot(editors=MAX_EDITORS + 1)
        with self.assertRaises(ValueError):
            validate_wakatime(snapshot)
        snapshot = make_snapshot(languages=0)
        with self.assertRaises(ValueError):
            validate_wakatime(snapshot)

    def test_durations_must_be_positive(self):
        snapshot = make_snapshot()
        snapshot["total"]["seconds"] = 0
        with self.assertRaises(ValueError):
            validate_wakatime(snapshot)
        snapshot["total"]["seconds"] = 3600
        snapshot["total"]["text"] = " "
        with self.assertRaises(ValueError):
            validate_wakatime(snapshot)


class WakatimeViewTests(unittest.TestCase):
    def test_view_projects_labels_and_values(self):
        snapshot = make_snapshot(languages=MAX_LANGUAGES, editors=MAX_EDITORS)
        view = wakatime_view(snapshot)
        self.assertEqual(view["range_label"], "LAST 7 DAYS")
        self.assertEqual(view["updated_label"], "2026-11-20")
        self.assertEqual(view["total"], "1 hrs 0 mins")
        self.assertEqual(view["daily_average"], "0 hrs 9 mins")
        self.assertEqual(len(view["languages"]), MAX_LANGUAGES)
        self.assertEqual(len(view["editors"]), MAX_EDITORS)
        self.assertEqual(view["operating_systems"], [("System 0", 100.0)])
        self.assertEqual(view["languages"][0], ("Language 0", 100.0))

    def test_view_validates_input(self):
        with self.assertRaises(ValueError):
            wakatime_view({"placeholder": True})


class InsightsSlotRenderingTests(unittest.TestCase):
    THEME = {"stack": "36,41,51", "stackA": 0.92}

    def render(self, snapshot):
        return wakatime_svg(self.THEME, "light", wakatime_view(snapshot))

    def test_empty_slots_render_placeholder_dashes(self):
        svg = self.render(make_snapshot(languages=3, editors=1, systems=1))
        empty_slots = (MAX_LANGUAGES - 3) + (MAX_EDITORS - 1) + (MAX_OPERATING_SYSTEMS - 1)
        # 每个空槽在名称列和百分比列各渲染一个占位横线。
        self.assertEqual(svg.count(">-</text>"), 2 * empty_slots)

    def test_full_snapshot_renders_no_placeholder_dashes(self):
        svg = self.render(make_snapshot(
            languages=MAX_LANGUAGES, editors=MAX_EDITORS, systems=MAX_OPERATING_SYSTEMS,
        ))
        self.assertNotIn(">-</text>", svg)


class SnapshotFromResponseTests(unittest.TestCase):
    def test_maps_response_and_truncates_lists(self):
        snapshot = snapshot_from_response(
            api_payload(languages=7, editors=5, systems=3, daily=480),
            "last_7_days",
            "2026-11-20T09:00:00+00:00",
        )
        self.assertFalse(snapshot["placeholder"])
        self.assertEqual(snapshot["fetched_at"], "2026-11-20T09:00:00+00:00")
        self.assertEqual(len(snapshot["languages"]), MAX_LANGUAGES)
        self.assertEqual(len(snapshot["editors"]), MAX_EDITORS)
        self.assertEqual(len(snapshot["operating_systems"]), MAX_OPERATING_SYSTEMS)
        self.assertEqual(snapshot["total"]["text"], "1 hrs 0 mins")
        self.assertEqual(snapshot["daily_average"]["text"], "0 hrs 8 mins")

    def test_duration_text_falls_back_to_seconds(self):
        payload = api_payload()
        del payload["data"]["human_readable_total"]
        del payload["data"]["human_readable_daily_average"]
        snapshot = snapshot_from_response(payload, "last_7_days", "2026-11-20T09:00:00+00:00")
        self.assertEqual(snapshot["total"]["text"], "1 hrs 0 mins")
        self.assertEqual(
            snapshot["daily_average"]["text"], format_duration(3600 / RANGE_DAYS["last_7_days"])
        )
        self.assertEqual(snapshot["languages"][0]["text"], format_duration(600))

    def test_stale_or_empty_stats_are_rejected(self):
        with self.assertRaises(SystemExit):
            snapshot_from_response(api_payload(up_to_date=False), "last_7_days", "now")
        with self.assertRaises(SystemExit):
            snapshot_from_response(api_payload(total=0), "last_7_days", "now")

    def test_merged_other_language_is_dropped_not_ranked(self):
        payload = api_payload(languages=3)
        payload["data"]["languages"].insert(1, {"name": "Other", "percent": 40.0, "total_seconds": 900})
        snapshot = snapshot_from_response(payload, "last_7_days", "2026-11-20T09:00:00+00:00")
        names = [entry["name"] for entry in snapshot["languages"]]
        self.assertNotIn("Other", names)
        self.assertEqual(names, ["Language 0", "Language 1", "Language 2"])

    def test_languages_filled_from_beyond_the_merged_bucket(self):
        payload = api_payload(languages=7)
        payload["data"]["languages"].insert(0, {"name": "Other", "percent": 90.0, "total_seconds": 900})
        snapshot = snapshot_from_response(payload, "last_7_days", "2026-11-20T09:00:00+00:00")
        names = [entry["name"] for entry in snapshot["languages"]]
        self.assertNotIn("Other", names)
        self.assertEqual(names, [f"Language {index}" for index in range(MAX_LANGUAGES)])

    def test_snapshot_without_real_languages_is_rejected(self):
        payload = api_payload(languages=1)
        payload["data"]["languages"] = [{"name": "Other", "percent": 100.0, "total_seconds": 900}]
        with self.assertRaises(SystemExit):
            snapshot_from_response(payload, "last_7_days", "now")


class CarouselRenderingTests(unittest.TestCase):
    def parse(self, filename):
        return ET.fromstring((ASSET_DIR / filename).read_text(encoding="utf-8"))

    def test_static_heroes_stay_on_tech_arsenal(self):
        for filename in STATIC_ASSETS:
            theme = "dark" if "dark" in filename else "light"
            with self.subTest(filename=filename):
                content = (ASSET_DIR / filename).read_text(encoding="utf-8")
                root = ET.fromstring(content)
                self.assertNotIn("CODING INSIGHTS", content)
                self.assertIsNone(root.find(f".//{SVG_NS}g[@id='{theme}-insights']"))

    def test_motion_heroes_render_both_carousel_pages(self):
        for filename in MOTION_ASSETS:
            theme = "dark" if "dark" in filename else "light"
            with self.subTest(filename=filename):
                root = self.parse(filename)
                insights = root.find(f".//{SVG_NS}g[@id='{theme}-insights']")
                self.assertIsNotNone(insights)
                texts = "".join(
                    element.text or "" for element in insights.findall(f".//{SVG_NS}text")
                )
                snapshot = load_wakatime()
                self.assertIn("TOTAL CODING TIME", texts)
                self.assertIn(snapshot["total"]["text"], texts)
                self.assertIn("LANGUAGES", texts)
                self.assertIn("OPERATING SYSTEM", texts)
                for system in snapshot["operating_systems"]:
                    self.assertIn(system["name"], texts)
                self.assertIn(snapshot["fetched_at"][:10], texts)
                heading = root.find(f".//{SVG_NS}g[@id='{theme}-stack-heading']")
                stack = root.find(f".//{SVG_NS}g[@id='{theme}-stack']")
                for group, expected_animates in ((heading, 2), (stack, 1), (insights, 1)):
                    animates = group.findall(f".//{SVG_NS}animate")
                    self.assertEqual(len(animates), expected_animates)
                    for animate in animates:
                        self.assertEqual(animate.attrib["attributeName"], "opacity")
                        self.assertEqual(animate.attrib["dur"], "37.6s")
                        values = animate.attrib["values"].split(";")
                        self.assertEqual(len(values), 9)
                        self.assertEqual(values[0], values[-1])

    def test_changed_wakatime_snapshot_marks_only_motion_assets_outdated(self):
        altered = copy.deepcopy(load_wakatime())
        altered["total"]["text"] = "99 hrs 59 mins"
        with patch("build_hero.load_wakatime", return_value=altered):
            self.assertEqual(set(check_assets()), set(MOTION_ASSETS))


if __name__ == "__main__":
    unittest.main()
