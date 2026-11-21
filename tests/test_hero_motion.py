import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from hero.geometry import make_cube, project
from hero.motion import motion_rotation, sample_motion
from hero.scene import SCENE_PATH, load_json


class HeroMotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scene = load_json(SCENE_PATH)
        cls.motion = sample_motion(cls.scene)

    def test_loop_seam_reuses_the_current_static_pose_exactly(self):
        frames = self.motion["frames"]
        self.assertEqual(frames[0], frames[-1])
        world, _ = make_cube(self.scene["cube"])
        expected = [project(point, self.scene)[:2] for point in world]
        self.assertEqual(frames[0]["points"], expected)

    def test_rotation_is_rigid_and_never_moves_the_cube_center(self):
        base_world, _ = make_cube(self.scene["cube"])
        base_distances = sorted(
            math.dist(a, b)
            for index, a in enumerate(base_world)
            for b in base_world[index + 1:]
        )
        for phase in (0, 0.125, 0.3, 0.75, 1):
            with self.subTest(phase=phase):
                world, _ = make_cube(self.scene["cube"], motion_rotation(self.scene, phase))
                center = [sum(point[axis] for point in world) / 8 for axis in range(3)]
                for actual, expected in zip(center, self.scene["cube"]["center"]):
                    self.assertAlmostEqual(actual, expected, places=10)
                distances = sorted(
                    math.dist(a, b)
                    for index, a in enumerate(world)
                    for b in world[index + 1:]
                )
                for actual, expected in zip(distances, base_distances):
                    self.assertAlmostEqual(actual, expected, places=9)
                for point in world:
                    self.assertGreater(project(point, self.scene)[2], 0)

    def test_every_sample_stays_inside_the_approved_horizontal_bound(self):
        frames = self.motion["frames"]
        self.assertEqual(self.motion["period_seconds"], 400)
        self.assertEqual(len(frames), 721)
        for frame in frames:
            self.assertLessEqual(max(point[0] for point in frame["points"]), self.scene["width"] / 4)
            self.assertLessEqual(sum(frame["visible"].values()), 3)
            self.assertGreaterEqual(sum(frame["visible"].values()), 1)
            for point in frame["points"]:
                self.assertTrue(all(math.isfinite(coordinate) for coordinate in point))
        self.assertGreater(len({tuple(frame["points"][0]) for frame in frames}), 100)


if __name__ == "__main__":
    unittest.main()
