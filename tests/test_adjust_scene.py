import copy
import math
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from adjust_scene import BLENDER_PATH, fmt
from hero.geometry import (
    cube_rotation,
    cube_vertices,
    mat_mul,
    project,
    projection_error,
    rotation_x,
)
from hero.scene import (
    ASSET_DIR,
    SCENE_PATH,
    THEMES_PATH,
    change_motion_speed,
    compensate_pitch,
    compensate_yaw,
    compensate_zoom,
    grid_screen_scale,
    ground_target,
    load_json,
)

BASE_SCENE = {
    "width": 1600,
    "height": 900,
    "camera": {
        "x": 0,
        "height": 12,
        "z": 0,
        "pitch_degrees": 45,
        "yaw_degrees": 0,
        "lens_mm": 50,
        "sensor_width": 36,
        "shift_y": 0,
        "zoom": 1,
    },
    "cube": {
        "center": [-6.035, 4.539, -7.899],
        "size": 4.24,
        "rotation_degrees": [-10, -4, 45],
    },
    "motion": {
        "period_seconds": 240,
        "turns": [1, 2, 1],
        "angle_step_degrees": 1,
    },
    "grid": {
        "yaw_degrees": 30,
        "base_step": 0.25,
        "step": 0.25,
        "base_major_every": 8,
        "major_every": 8,
        "major_opacity": 1,
        "minor_opacity": 1,
        "lod_level": 0,
        "fade": [[0, 0], [0.18, 0.12], [0.48, 0.65], [1, 1]],
    },
}


class SceneAdjustmentTests(unittest.TestCase):
    def test_every_vertex_keeps_its_screen_projection(self):
        adjusted = compensate_pitch(BASE_SCENE, 25)
        self.assertLess(projection_error(BASE_SCENE, adjusted), 1e-9)

    def test_center_and_orientation_stay_fixed_in_camera_space(self):
        adjusted = compensate_pitch(BASE_SCENE, 30)
        for old_point, new_point in zip(cube_vertices(BASE_SCENE), cube_vertices(adjusted)):
            old_projection = project(old_point, BASE_SCENE)
            new_projection = project(new_point, adjusted)
            self.assertAlmostEqual(old_projection[0], new_projection[0], places=9)
            self.assertAlmostEqual(old_projection[1], new_projection[1], places=9)
            self.assertAlmostEqual(old_projection[2], new_projection[2], places=9)

    def test_repeated_adjustments_preserve_the_same_pose(self):
        first = compensate_pitch(BASE_SCENE, 25)
        second = compensate_pitch(first, 30)
        self.assertLess(projection_error(BASE_SCENE, second), 1e-9)

    def test_pitch_sweep_preserves_projection(self):
        for pitch in (1, 25, 30, 45, 60, 89):
            with self.subTest(pitch=pitch):
                adjusted = compensate_pitch(BASE_SCENE, pitch)
                self.assertLess(projection_error(BASE_SCENE, adjusted), 1e-9)

    def test_zoom_preserves_projection_and_ground_target(self):
        for factor in (0.5, 1.5, 2, 4):
            with self.subTest(factor=factor):
                adjusted = compensate_zoom(BASE_SCENE, factor)
                self.assertLess(projection_error(BASE_SCENE, adjusted), 1e-9)
                for old_axis, new_axis in zip(ground_target(BASE_SCENE), ground_target(adjusted)):
                    self.assertAlmostEqual(old_axis, new_axis, places=9)
                self.assertEqual(adjusted["cube"]["rotation_degrees"], BASE_SCENE["cube"]["rotation_degrees"])

    def test_yaw_preserves_projection_depth_and_ground_target(self):
        for yaw in (-60, -30, 30, 75, 180):
            with self.subTest(yaw=yaw):
                adjusted = compensate_yaw(BASE_SCENE, yaw)
                self.assertLess(projection_error(BASE_SCENE, adjusted), 1e-9)
                for old_point, new_point in zip(cube_vertices(BASE_SCENE), cube_vertices(adjusted)):
                    old_depth = project(old_point, BASE_SCENE)[2]
                    new_depth = project(new_point, adjusted)[2]
                    self.assertAlmostEqual(old_depth, new_depth, places=9)
                for old_axis, new_axis in zip(ground_target(BASE_SCENE), ground_target(adjusted)):
                    self.assertAlmostEqual(old_axis, new_axis, places=9)

    def test_zoom_after_yaw_preserves_projection_and_ground_target(self):
        rotated = compensate_yaw(BASE_SCENE, 35)
        adjusted = compensate_zoom(rotated, 2)
        self.assertLess(projection_error(BASE_SCENE, adjusted), 1e-9)
        for old_axis, new_axis in zip(ground_target(BASE_SCENE), ground_target(adjusted)):
            self.assertAlmostEqual(old_axis, new_axis, places=9)

    def test_pitch_after_yaw_preserves_projection(self):
        rotated = compensate_yaw(BASE_SCENE, 35)
        adjusted = compensate_pitch(rotated, 30)
        self.assertLess(projection_error(BASE_SCENE, adjusted), 1e-9)

    def test_grid_lod_merges_all_lines_and_softens_far_grid(self):
        doubled = compensate_zoom(BASE_SCENE, 2)
        quadrupled = compensate_zoom(BASE_SCENE, 4)
        eightfold = compensate_zoom(BASE_SCENE, 8)
        self.assertEqual(doubled["grid"]["step"], 0.5)
        self.assertEqual(quadrupled["grid"]["step"], 1)
        self.assertEqual(eightfold["grid"]["step"], 2)
        self.assertEqual(doubled["grid"]["major_every"], 4)
        self.assertEqual(quadrupled["grid"]["major_every"], 2)
        self.assertEqual(quadrupled["grid"]["step"] * quadrupled["grid"]["major_every"], 2)
        self.assertLess(doubled["grid"]["fade"][1][1], BASE_SCENE["grid"]["fade"][1][1])
        self.assertLess(quadrupled["grid"]["fade"][2][1], doubled["grid"]["fade"][2][1])

    def test_major_grid_thins_minors_then_demotes_old_major_lines(self):
        expected = {
            1: (0.25, 8, 2),
            2: (0.5, 4, 2),
            4: (1, 2, 2),
            8: (2, 1, 2),
            16: (2, 2, 4),
            32: (4, 2, 8),
            64: (8, 2, 16),
        }
        for factor, (step, major_every, major_spacing) in expected.items():
            with self.subTest(factor=factor):
                adjusted = compensate_zoom(BASE_SCENE, factor)
                grid = adjusted["grid"]
                self.assertEqual(grid["step"], step)
                self.assertEqual(grid["major_every"], major_every)
                self.assertEqual(grid["step"] * grid["major_every"], major_spacing)

    def test_old_major_lines_survive_as_minor_lines_at_next_scale(self):
        exhausted = compensate_zoom(BASE_SCENE, 8)["grid"]
        promoted = compensate_zoom(BASE_SCENE, 16)["grid"]
        self.assertEqual(exhausted["major_every"], 1)
        self.assertEqual(promoted["step"], exhausted["step"])
        self.assertEqual(promoted["major_every"], 2)
        self.assertEqual(
            promoted["step"] * promoted["major_every"],
            2 * exhausted["step"] * exhausted["major_every"],
        )

    def test_logarithmic_grid_fading_keeps_minor_lines_slower(self):
        baseline = compensate_zoom(BASE_SCENE, 1)["grid"]
        doubled = compensate_zoom(BASE_SCENE, 2)["grid"]
        quadrupled = compensate_zoom(BASE_SCENE, 4)["grid"]
        self.assertEqual(baseline["major_opacity"], 1)
        self.assertEqual(baseline["minor_opacity"], 1)
        self.assertAlmostEqual(doubled["major_opacity"], 0.5)
        self.assertAlmostEqual(doubled["minor_opacity"], 0.325)
        self.assertAlmostEqual(quadrupled["major_opacity"], 1 / 3)
        self.assertAlmostEqual(quadrupled["minor_opacity"], 0.1 + 0.9 / 9)
        for exponent in (0, 1, 2, 4, 8, 16):
            with self.subTest(exponent=exponent):
                grid = compensate_zoom(BASE_SCENE, 2 ** exponent)["grid"]
                self.assertLess(0.55 * grid["minor_opacity"], grid["major_opacity"])

    def test_minor_fade_rate_is_higher_order_infinitesimal(self):
        previous_ratio = math.inf
        for exponent in (1, 2, 4, 8, 16, 32, 64, 128):
            t = math.log2(2 ** exponent)
            major_rate = 1 / (1 + t) ** 2
            minor_rate = 1.8 / (1 + t) ** 3
            ratio = minor_rate / major_rate
            self.assertAlmostEqual(ratio, 1.8 / (1 + t))
            self.assertLess(minor_rate, major_rate)
            self.assertLess(ratio, previous_ratio)
            previous_ratio = ratio
        self.assertLess(previous_ratio, 0.025)

    def test_grid_screen_size_scales_until_each_two_x_merge(self):
        halfway = compensate_zoom(BASE_SCENE, 1.5)
        almost_doubled = compensate_zoom(BASE_SCENE, 1.999)
        doubled = compensate_zoom(BASE_SCENE, 2)
        self.assertAlmostEqual(grid_screen_scale(halfway), 1 / 1.5)
        self.assertAlmostEqual(grid_screen_scale(almost_doubled), 1 / 1.999)
        self.assertAlmostEqual(grid_screen_scale(doubled), 1)
        self.assertEqual(doubled["grid"]["step"], 2 * BASE_SCENE["grid"]["step"])

    def test_grid_line_count_stays_bounded_at_extreme_zoom(self):
        baseline_ratio = BASE_SCENE["camera"]["zoom"] / BASE_SCENE["grid"]["step"]
        for exponent in range(0, 21, 2):
            with self.subTest(exponent=exponent):
                adjusted = compensate_zoom(BASE_SCENE, 2 ** exponent)
                self.assertLessEqual(
                    adjusted["camera"]["zoom"] / adjusted["grid"]["step"],
                    2 * baseline_ratio + 1e-9,
                )

    def test_combined_pitch_and_zoom_preserve_projection(self):
        adjusted = compensate_zoom(compensate_pitch(BASE_SCENE, 30), 2)
        self.assertLess(projection_error(BASE_SCENE, adjusted), 1e-9)

    def test_combined_pitch_yaw_and_zoom_preserve_projection(self):
        adjusted = compensate_pitch(BASE_SCENE, 30)
        adjusted = compensate_yaw(adjusted, 35)
        adjusted = compensate_zoom(adjusted, 2)
        self.assertLess(projection_error(BASE_SCENE, adjusted), 1e-9)

    def test_combined_zoom_then_pitch_at_nonzero_yaw_preserves_projection(self):
        adjusted = compensate_yaw(compensate_zoom(BASE_SCENE, 2), 35)
        adjusted = compensate_pitch(adjusted, 30)
        self.assertLess(projection_error(BASE_SCENE, adjusted), 1e-9)

    def test_motion_speed_changes_only_the_loop_period(self):
        adjusted = change_motion_speed(BASE_SCENE, 0.6)
        self.assertEqual(adjusted["motion"]["period_seconds"], 400)
        self.assertEqual(adjusted["motion"]["turns"], BASE_SCENE["motion"]["turns"])
        self.assertEqual(adjusted["motion"]["angle_step_degrees"], BASE_SCENE["motion"]["angle_step_degrees"])
        self.assertEqual(adjusted["camera"], BASE_SCENE["camera"])
        self.assertEqual(adjusted["cube"], BASE_SCENE["cube"])
        self.assertEqual(adjusted["grid"], BASE_SCENE["grid"])
        self.assertEqual(BASE_SCENE["motion"]["period_seconds"], 240)

    def test_input_is_not_mutated(self):
        original = copy.deepcopy(BASE_SCENE)
        compensate_pitch(BASE_SCENE, 25)
        compensate_yaw(BASE_SCENE, 35)
        compensate_zoom(BASE_SCENE, 2)
        self.assertEqual(BASE_SCENE, original)

    def test_euler_round_trip_preserves_rotation_matrix(self):
        adjusted = compensate_pitch(BASE_SCENE, 25)
        expected = mat_mul(rotation_x(math.radians(20)), cube_rotation(BASE_SCENE["cube"]["rotation_degrees"]))
        actual = cube_rotation(adjusted["cube"]["rotation_degrees"])
        for expected_row, actual_row in zip(expected, actual):
            for expected_value, actual_value in zip(expected_row, actual_row):
                self.assertAlmostEqual(expected_value, actual_value, places=9)


class CommandLineTests(unittest.TestCase):
    def run_cli(self, *arguments):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "adjust_scene.py"), *arguments],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def persistent_paths(self):
        return (
            SCENE_PATH,
            THEMES_PATH,
            BLENDER_PATH,
            ASSET_DIR / "hero-light.svg",
            ASSET_DIR / "hero-dark.svg",
            ASSET_DIR / "hero-light-motion.svg",
            ASSET_DIR / "hero-dark-motion.svg",
        )

    def test_help_documents_parameters_and_examples(self):
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout)
        self.assertIn("--pitch", result.stdout)
        self.assertIn("--yaw", result.stdout)
        self.assertIn("--zoom", result.stdout)
        self.assertIn("--motion-speed", result.stdout)
        self.assertIn("--apply", result.stdout)
        self.assertIn("绝对角度", result.stdout)
        self.assertIn("示例", result.stdout)
        self.assertIn("scripts/adjust_scene.py", result.stdout)

    def test_dry_run_reports_old_new_success_without_writing(self):
        paths = self.persistent_paths()
        contents = [path.read_text(encoding="utf-8") for path in paths]
        current_pitch = load_json(SCENE_PATH)["camera"]["pitch_degrees"]
        result = self.run_cli("--pitch", "30")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"pitch: {fmt(current_pitch)}° → 30°  success", result.stdout)
        self.assertIn("cube center:", result.stdout)
        self.assertIn("cube rotation:", result.stdout)
        self.assertIn("optical horizon y:", result.stdout)
        self.assertIn("dry-run: no files changed", result.stdout)
        self.assertEqual([path.read_text(encoding="utf-8") for path in paths], contents)

    def test_yaw_dry_run_reports_old_new_success_without_writing(self):
        paths = self.persistent_paths()
        contents = [path.read_text(encoding="utf-8") for path in paths]
        current_yaw = load_json(SCENE_PATH)["camera"]["yaw_degrees"]
        result = self.run_cli("--yaw", "35")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"camera yaw: {fmt(current_yaw)}° → 35°  success", result.stdout)
        self.assertIn("camera x:", result.stdout)
        self.assertIn("camera z:", result.stdout)
        self.assertIn("grid relative yaw:", result.stdout)
        self.assertIn("validation: maximum vertex projection change", result.stdout)
        self.assertIn("dry-run: no files changed", result.stdout)
        self.assertEqual([path.read_text(encoding="utf-8") for path in paths], contents)

    def test_motion_speed_dry_run_changes_period_without_writing(self):
        paths = self.persistent_paths()
        contents = [path.read_text(encoding="utf-8") for path in paths]
        current_period = load_json(SCENE_PATH)["motion"]["period_seconds"]
        result = self.run_cli("--motion-speed", "0.6")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("motion speed: 100% → 60%  success", result.stdout)
        self.assertIn(
            f"motion period: {fmt(current_period)}s → {fmt(current_period / 0.6)}s  success",
            result.stdout,
        )
        self.assertIn("validation: maximum vertex projection change = 0.000e+00px", result.stdout)
        self.assertIn("dry-run: no files changed", result.stdout)
        self.assertEqual([path.read_text(encoding="utf-8") for path in paths], contents)

    def test_zoom_dry_run_reports_linked_parameters(self):
        scene = load_json(SCENE_PATH)
        result = self.run_cli("--zoom", "2")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"zoom: {fmt(scene['camera']['zoom'])}× → {fmt(scene['camera']['zoom'] * 2)}×  success", result.stdout)
        self.assertIn("camera height:", result.stdout)
        self.assertIn("grid LOD level:", result.stdout)
        self.assertIn("grid major every:", result.stdout)
        self.assertIn("grid major opacity:", result.stdout)
        self.assertIn("grid minor opacity:", result.stdout)
        self.assertIn("grid major spacing:", result.stdout)
        self.assertIn("grid screen spacing:", result.stdout)
        self.assertIn("grid fade:", result.stdout)
        self.assertIn("dry-run: no files changed", result.stdout)


if __name__ == "__main__":
    unittest.main()
