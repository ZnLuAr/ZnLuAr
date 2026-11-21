"""Sample deterministic camera-space cube rotation for declarative SVG playback."""

import math

from hero.geometry import (
    camera_position,
    cube_rotation,
    face_visible,
    make_cube,
    mat_mul,
    project,
    rotation_x,
    rotation_y,
)


def motion_rotation(scene, phase):
    """Rotate the current pose around camera-space axes without moving its center."""
    base = cube_rotation(scene["cube"]["rotation_degrees"])
    if phase in (0, 1):
        return base
    camera = scene["camera"]
    camera_from_world = mat_mul(
        rotation_x(-math.radians(camera["pitch_degrees"])),
        rotation_y(math.radians(camera["yaw_degrees"])),
    )
    world_from_camera = [list(row) for row in zip(*camera_from_world)]
    delta = cube_rotation([turns * 360 * phase for turns in scene["motion"]["turns"]])
    world_delta = mat_mul(world_from_camera, mat_mul(delta, camera_from_world))
    return mat_mul(world_delta, base)


def sample_motion(scene):
    """Return equally timed projected vertices and face visibility, including an exact loop seam."""
    config = scene["motion"]
    fastest_turns = max(abs(turns) for turns in config["turns"])
    step_count = math.ceil(fastest_turns * 360 / config["angle_step_degrees"])
    camera = camera_position(scene)
    frames = []
    for index in range(step_count + 1):
        phase = index / step_count
        if index in (0, step_count):
            world, faces = make_cube(scene["cube"])
        else:
            world, faces = make_cube(scene["cube"], motion_rotation(scene, phase))
        projected = [project(point, scene) for point in world]
        frames.append({
            "points": [[point[0], point[1]] for point in projected],
            "visible": {face["tag"]: face_visible(face, world, camera) for face in faces},
        })
    return {"period_seconds": config["period_seconds"], "frames": frames}
