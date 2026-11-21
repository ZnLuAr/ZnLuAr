import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from hero.geometry import (
    cube_vertices,
    grid_project,
    ground_from_screen,
    horizon_y,
    make_cube,
)
from hero.scene import SCENE_PATH, load_json


class HeroGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scene = load_json(SCENE_PATH)

    def test_ground_projection_round_trip(self):
        for x, y in ((0, 0), (800, 450), (1600, 900), (200, 700)):
            with self.subTest(x=x, y=y):
                ground = ground_from_screen(x, y, self.scene)
                self.assertIsNotNone(ground)
                projected = grid_project(*ground, self.scene)
                self.assertIsNotNone(projected)
                self.assertAlmostEqual(projected[0], x, places=8)
                self.assertAlmostEqual(projected[1], y, places=8)

    def test_cube_model_uses_the_shared_vertex_order(self):
        world, _ = make_cube(self.scene["cube"])
        for actual, expected in zip(world, cube_vertices(self.scene)):
            for actual_axis, expected_axis in zip(actual, expected):
                self.assertAlmostEqual(actual_axis, expected_axis, places=10)

    def test_horizon_stays_outside_the_frame(self):
        self.assertLess(horizon_y(self.scene), 0)

    def test_persisted_camera_and_grid_angles_are_finite(self):
        angles = (
            self.scene["camera"]["pitch_degrees"],
            self.scene["camera"]["yaw_degrees"],
            self.scene["grid"]["yaw_degrees"],
        )
        self.assertTrue(all(math.isfinite(angle) for angle in angles))


if __name__ == "__main__":
    unittest.main()
