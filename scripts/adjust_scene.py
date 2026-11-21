#!/usr/bin/env python3
"""Adjust scene parameters without changing the cube's screen-space pose."""

import argparse
import copy
import math
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from build_hero import expected_assets
from hero.geometry import (
    cube_rotation,
    horizon_y,
    mat_mul,
    projection_error,
)
from hero.scene import (
    ASSET_DIR,
    ROOT,
    SCENE_PATH,
    THEMES_PATH,
    compensate_pitch,
    change_motion_speed,
    compensate_yaw,
    compensate_zoom,
    grid_screen_scale,
    load_json,
    write_json,
    write_text,
)

CONFIG_PATH = SCENE_PATH
BLENDER_PATH = ROOT / "scripts" / "blender_calibrate.py"


def fmt(value):
    if abs(value) < 0.0000000005:
        value = 0
    return f"{value:.9f}".rstrip("0").rstrip(".")


def replace_block(text, marker, content, path):
    start_marker = f"# BEGIN GENERATED {marker}"
    end_marker = start_marker.replace("BEGIN", "END")
    start = text.find(start_marker)
    end = text.find(end_marker)
    if start < 0 or end < start:
        raise ValueError(f"Missing generated block {marker} in {path}")
    return text[:start] + start_marker + "\n" + content.rstrip() + "\n" + end_marker + text[end + len(end_marker):]


def blender_cube(scene):
    cube = scene["cube"]
    x, y, z = cube["center"]
    location = ", ".join(fmt(value) for value in (x, -z, y))
    # Blender basis B=(x,-z,y) is a proper rotation from SVG Y-up to Blender Z-up.
    svg_rotation = cube_rotation(cube["rotation_degrees"])
    basis = [[1, 0, 0], [0, 0, -1], [0, 1, 0]]
    rotation = mat_mul(basis, mat_mul(svg_rotation, basis))
    rows = ",\n    ".join("(" + ", ".join(fmt(value) for value in row) + ")" for row in rotation)
    return f"""bpy.ops.mesh.primitive_cube_add(size={fmt(cube['size'])}, location=({location}))
cube = bpy.context.object
cube.rotation_euler = Matrix((
    {rows}
)).to_euler()"""


def blender_camera(scene):
    camera = scene["camera"]
    yaw = math.radians(camera["yaw_degrees"])
    direction_x = -math.cos(math.radians(camera["pitch_degrees"])) * math.sin(yaw)
    direction_y = math.cos(math.radians(camera["pitch_degrees"])) * math.cos(yaw)
    return f"""bpy.ops.object.camera_add(location=({fmt(camera['x'])}, {fmt(-camera['z'])}, {fmt(camera['height'])}))
camera = bpy.context.object
pitch = math.radians({fmt(camera['pitch_degrees'])})
direction = Vector(({fmt(direction_x)}, {fmt(direction_y)}, -math.sin(pitch)))
camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
camera.data.lens = {fmt(camera['lens_mm'])}
camera.data.sensor_width = {fmt(camera['sensor_width'])}
camera.data.shift_y = {fmt(camera['shift_y'])}
camera.data.clip_end = 500
scene.camera = camera"""


def apply_scene(scene):
    """Validate every output in memory before replacing persistent generated files."""
    themes = load_json(THEMES_PATH)
    outputs = expected_assets(scene, themes)
    blender = BLENDER_PATH.read_text(encoding="utf-8")
    blender = replace_block(blender, "CUBE", blender_cube(scene), BLENDER_PATH)
    blender = replace_block(blender, "CAMERA", blender_camera(scene), BLENDER_PATH)

    write_json(CONFIG_PATH, scene)
    for filename, content in outputs.items():
        write_text(ASSET_DIR / filename, content)
    write_text(BLENDER_PATH, blender)


def main():
    # Keep °, → and Chinese help readable when Python is piped through Git Bash.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="调整俯角、高度轴旋转、滚轮式距离或三轴旋转速度，并保持立方体的投影与闭环几何不变。",
        epilog="""示例：
  python scripts/adjust_scene.py --pitch 30
      预览 30° 俯角及其联动参数，不写文件。

  python scripts/adjust_scene.py --yaw 30
      摄像机绕高度轴旋转到绝对 30°，立方体屏幕姿态保持不变。

  python scripts/adjust_scene.py --zoom 1.5
      沿当前视线拉远 1.5×，联动相机位置、网格 LOD 和距离淡出。

  python scripts/adjust_scene.py --motion-speed 0.6
      转速降为当前的 60%，循环周期相应除以 0.6，不改变任何采样顶点。

  python scripts/adjust_scene.py --pitch 30 --zoom 2 --apply
      组合调整，验证后更新 gen JSON、静态与动态 SVG 和 Blender 校准脚本。

每项参数都会输出“旧值 → 新值  success”。默认只预览，不写文件。""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--pitch", type=float, metavar="DEGREES", help="新的相机向下俯角，范围 0–90°（不含边界）")
    parser.add_argument("--yaw", type=float, metavar="DEGREES", help="相机绕高度轴的新绝对角度，可为负值；不是相对增量")
    parser.add_argument("--zoom", type=float, metavar="FACTOR", help="相对当前距离的滚轮倍率；>1 拉远，<1 拉近")
    parser.add_argument("--motion-speed", type=float, metavar="FACTOR", help="相对当前三轴转速的倍率；0.6 表示降到 60%%，周期相应变长")
    parser.add_argument("--apply", action="store_true", help="通过投影及 SVG 构建验证后，实际写入持久化生成产物")
    args = parser.parse_args()
    if all(value is None for value in (args.pitch, args.yaw, args.zoom, args.motion_speed)):
        parser.error("至少指定 --pitch、--yaw、--zoom 或 --motion-speed")
    if args.pitch is not None and not 0 < args.pitch < 90:
        parser.error("--pitch 必须在 0–90° 之间（不含边界）")
    if args.yaw is not None and not math.isfinite(args.yaw):
        parser.error("--yaw 必须是有限角度")
    if args.zoom is not None and (not math.isfinite(args.zoom) or args.zoom <= 0):
        parser.error("--zoom 必须是大于 0 的有限倍率")
    if args.motion_speed is not None and (not math.isfinite(args.motion_speed) or args.motion_speed <= 0):
        parser.error("--motion-speed 必须是大于 0 的有限倍率")

    before = load_json(CONFIG_PATH)
    after = copy.deepcopy(before)
    if args.pitch is not None:
        after = compensate_pitch(after, args.pitch)
    if args.yaw is not None:
        after = compensate_yaw(after, args.yaw)
    if args.zoom is not None:
        after = compensate_zoom(after, args.zoom)
    if args.motion_speed is not None:
        after = change_motion_speed(after, args.motion_speed)
    error = projection_error(before, after)
    if error > 1e-8:
        raise AssertionError(f"Compensation changed vertex projections by {error}px")

    def vector(values):
        return "[" + ", ".join(fmt(value) for value in values) + "]"

    def fade(values):
        return "[" + ", ".join(f"{fmt(offset)}:{fmt(opacity)}" for offset, opacity in values) + "]"

    if args.pitch is not None:
        print(f"pitch: {fmt(before['camera']['pitch_degrees'])}° → {fmt(after['camera']['pitch_degrees'])}°  success")
    if args.yaw is not None:
        print(f"camera yaw: {fmt(before['camera']['yaw_degrees'])}° → {fmt(after['camera']['yaw_degrees'])}°  success")
        print(f"camera x: {fmt(before['camera']['x'])} → {fmt(after['camera']['x'])}  success")
        print(f"camera z: {fmt(before['camera']['z'])} → {fmt(after['camera']['z'])}  success")
        old_relative = before["grid"]["yaw_degrees"] - before["camera"]["yaw_degrees"]
        new_relative = after["grid"]["yaw_degrees"] - after["camera"]["yaw_degrees"]
        print(f"grid relative yaw: {fmt(old_relative)}° → {fmt(new_relative)}°  success")
    if args.zoom is not None:
        print(f"zoom: {fmt(before['camera']['zoom'])}× → {fmt(after['camera']['zoom'])}×  success")
        print(f"camera height: {fmt(before['camera']['height'])} → {fmt(after['camera']['height'])}  success")
        print(f"camera x: {fmt(before['camera']['x'])} → {fmt(after['camera']['x'])}  success")
        print(f"camera z: {fmt(before['camera']['z'])} → {fmt(after['camera']['z'])}  success")
        print(f"grid LOD level: {before['grid']['lod_level']} → {after['grid']['lod_level']}  success")
        print(f"grid step: {fmt(before['grid']['step'])} → {fmt(after['grid']['step'])}  success")
        print(f"grid major every: {before['grid']['major_every']} → {after['grid']['major_every']}  success")
        print(f"grid major opacity: {fmt(before['grid']['major_opacity'])} → {fmt(after['grid']['major_opacity'])}  success")
        print(f"grid minor opacity: {fmt(before['grid']['minor_opacity'])} → {fmt(after['grid']['minor_opacity'])}  success")
        print(f"grid major spacing: {fmt(before['grid']['step'] * before['grid']['major_every'])} → {fmt(after['grid']['step'] * after['grid']['major_every'])}  success")
        print(f"grid screen spacing: {fmt(grid_screen_scale(before))}× → {fmt(grid_screen_scale(after))}×  success")
        print(f"grid fade: {fade(before['grid']['fade'])} → {fade(after['grid']['fade'])}  success")
    if args.motion_speed is not None:
        print(f"motion speed: 100% → {fmt(args.motion_speed * 100)}%  success")
        print(f"motion period: {fmt(before['motion']['period_seconds'])}s → {fmt(after['motion']['period_seconds'])}s  success")
    print(f"cube center: {vector(before['cube']['center'])} → {vector(after['cube']['center'])}  success")
    print(f"cube rotation: {vector(before['cube']['rotation_degrees'])} → {vector(after['cube']['rotation_degrees'])}  success")
    print(f"optical horizon y: {horizon_y(before):.6f}px → {horizon_y(after):.6f}px  success")
    print(f"validation: maximum vertex projection change = {error:.3e}px  success")
    if args.apply:
        apply_scene(after)
        print("write: gen/hero/scene.json, static and motion hero SVGs, blender_calibrate.py  success")
    else:
        print("dry-run: no files changed; add --apply to write these parameters")


if __name__ == "__main__":
    main()
