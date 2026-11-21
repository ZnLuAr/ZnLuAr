"""Persistent scene state and camera adjustments for the profile hero."""

import copy
import json
import math
from pathlib import Path

from hero.geometry import (
    add,
    camera_position,
    cube_rotation,
    mat_mul,
    mat_vec,
    rotation_to_euler,
    rotation_x,
    rotation_y,
    subtract,
)

ROOT = Path(__file__).resolve().parents[2]
GEN_DIR = ROOT / "gen" / "hero"
SCENE_PATH = GEN_DIR / "scene.json"
THEMES_PATH = GEN_DIR / "themes.json"
ASSET_DIR = ROOT / "assets" / "hero"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path, content):
    """Write generated UTF-8 text atomically within its destination directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(content, encoding="utf-8", newline="\n")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json(path, value):
    write_text(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def validate_scene(scene):
    if scene["width"] <= 0 or scene["height"] <= 0:
        raise ValueError("Scene dimensions must be positive")
    camera = scene["camera"]
    if not 0 < camera["pitch_degrees"] < 90:
        raise ValueError("Camera pitch must be between 0 and 90 degrees")
    if camera["lens_mm"] <= 0 or camera["sensor_width"] <= 0:
        raise ValueError("Camera lens and sensor width must be positive")
    if camera["zoom"] <= 0:
        raise ValueError("Camera zoom must be positive")
    if scene["cube"]["size"] <= 0:
        raise ValueError("Cube size must be positive")
    motion = scene["motion"]
    if not math.isfinite(motion["period_seconds"]) or motion["period_seconds"] <= 0:
        raise ValueError("Motion period must be finite and positive")
    if len(motion["turns"]) != 3 or any(not isinstance(turns, int) for turns in motion["turns"]):
        raise ValueError("Motion turns must contain three integer cycle counts")
    if not any(motion["turns"]):
        raise ValueError("At least one motion axis must rotate")
    if not math.isfinite(motion["angle_step_degrees"]) or motion["angle_step_degrees"] <= 0:
        raise ValueError("Motion angle step must be finite and positive")
    grid = scene["grid"]
    if grid["base_step"] <= 0 or grid["base_major_every"] < 1:
        raise ValueError("Grid base step and major interval must be positive")


def compensate_pitch(scene, new_pitch):
    """Rotate the cube around the camera so every camera-space vector is unchanged."""
    adjusted = copy.deepcopy(scene)
    old_pitch = scene["camera"]["pitch_degrees"]
    delta = math.radians(old_pitch - new_pitch)
    yaw = math.radians(scene["camera"]["yaw_degrees"])
    compensation = mat_mul(rotation_y(yaw), mat_mul(rotation_x(delta), rotation_y(-yaw)))

    relative_center = subtract(scene["cube"]["center"], camera_position(scene))
    new_center = add(camera_position(scene), mat_vec(compensation, relative_center))
    new_rotation = mat_mul(compensation, cube_rotation(scene["cube"]["rotation_degrees"]))

    adjusted["camera"]["pitch_degrees"] = new_pitch
    adjusted["cube"]["center"] = new_center
    adjusted["cube"]["rotation_degrees"] = rotation_to_euler(new_rotation)
    return adjusted


def ground_target(scene):
    """Return the ground point at the center of the current view."""
    camera = scene["camera"]
    pitch = math.radians(camera["pitch_degrees"])
    yaw = math.radians(camera["yaw_degrees"])
    distance = camera["height"] / math.sin(pitch)
    forward = [
        -math.sin(yaw) * math.cos(pitch),
        -math.sin(pitch),
        -math.cos(yaw) * math.cos(pitch),
    ]
    return add(camera_position(scene), [distance * axis for axis in forward])


def compensate_yaw(scene, new_yaw):
    """Orbit around the ground target while keeping the cube fixed in camera space."""
    adjusted = copy.deepcopy(scene)
    camera = scene["camera"]
    delta = math.radians(new_yaw - camera["yaw_degrees"])
    compensation = rotation_y(delta)
    target = ground_target(scene)

    new_camera = add(target, mat_vec(compensation, subtract(camera_position(scene), target)))
    new_center = add(target, mat_vec(compensation, subtract(scene["cube"]["center"], target)))
    new_rotation = mat_mul(compensation, cube_rotation(scene["cube"]["rotation_degrees"]))
    adjusted["camera"]["yaw_degrees"] = new_yaw
    adjusted["camera"]["x"] = new_camera[0]
    adjusted["camera"]["height"] = new_camera[1]
    adjusted["camera"]["z"] = new_camera[2]
    adjusted["cube"]["center"] = new_center
    adjusted["cube"]["rotation_degrees"] = rotation_to_euler(new_rotation)
    return adjusted


def compensate_zoom(scene, factor):
    """Dolly along the view ray, preserving its ground target and the cube's projection."""
    if not math.isfinite(factor) or factor <= 0:
        raise ValueError("Zoom factor must be finite and positive")
    adjusted = copy.deepcopy(scene)
    camera = adjusted["camera"]
    pitch = math.radians(camera["pitch_degrees"])
    yaw = math.radians(camera["yaw_degrees"])
    distance = camera["height"] / math.sin(pitch)
    travel = (factor - 1) * distance
    delta = [
        math.sin(yaw) * math.cos(pitch) * travel,
        math.sin(pitch) * travel,
        math.cos(yaw) * math.cos(pitch) * travel,
    ]

    new_camera = add(camera_position(adjusted), delta)
    camera["x"], camera["height"], camera["z"] = new_camera
    camera["zoom"] *= factor
    adjusted["cube"]["center"] = add(adjusted["cube"]["center"], delta)
    update_grid_lod(adjusted)
    return adjusted


def change_motion_speed(scene, factor):
    """Scale angular speed while preserving the sampled geometry and exact loop."""
    if not math.isfinite(factor) or factor <= 0:
        raise ValueError("Motion speed factor must be finite and positive")
    adjusted = copy.deepcopy(scene)
    adjusted["motion"]["period_seconds"] /= factor
    return adjusted


def update_grid_lod(scene):
    """Thin minor lines first, then demote old major lines into the next scale."""
    grid = scene["grid"]
    zoom = scene["camera"]["zoom"]
    level = max(0, math.floor(math.log2(zoom) + 1e-12))
    grid["lod_level"] = level
    if level <= 3:
        grid["step"] = grid["base_step"] * 2 ** level
        grid["major_every"] = max(1, grid["base_major_every"] // 2 ** level)
    else:
        # Old majors remain and alternate as minor/major lines at the next scale.
        grid["step"] = grid["base_step"] * grid["base_major_every"] * 2 ** (level - 4)
        grid["major_every"] = 2
    log_zoom = max(0, math.log2(zoom))
    grid["major_opacity"] = 1 / (1 + log_zoom)
    grid["minor_opacity"] = 0.1 + 0.9 / (1 + log_zoom) ** 2
    grid["fade"] = [
        [0, 0],
        [0.18, min(1, 0.12 / zoom)],
        [0.48, min(1, 0.65 / math.sqrt(zoom))],
        [1, 1],
    ]


def grid_screen_scale(scene):
    """Projected grid spacing relative to zoom=1, before pitch-dependent distortion."""
    grid = scene["grid"]
    return (grid["step"] / grid["base_step"]) / scene["camera"]["zoom"]
