#!/usr/bin/env python3
"""Build static and declarative-motion hero SVGs from persistent JSON state."""

import argparse
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from hero.scene import ASSET_DIR, SCENE_PATH, THEMES_PATH, load_json, validate_scene, write_text
from hero.stack import load_stack
from hero.svg_renderer import render_hero
from hero.wakatime import load_wakatime


def expected_assets(scene=None, themes=None, wakatime=None):
    scene = scene if scene is not None else load_json(SCENE_PATH)
    themes = themes if themes is not None else load_json(THEMES_PATH)
    validate_scene(scene)
    if set(themes) != {"light", "dark"}:
        raise ValueError("Theme state must contain exactly light and dark themes")
    return render_hero(scene, themes, load_stack(), wakatime if wakatime is not None else load_wakatime())


def build_assets(scene=None, themes=None):
    outputs = expected_assets(scene, themes)
    for filename, content in outputs.items():
        write_text(ASSET_DIR / filename, content)
    return outputs


def check_assets():
    outdated = [
        filename
        for filename, content in expected_assets().items()
        if not (ASSET_DIR / filename).is_file() or (ASSET_DIR / filename).read_text(encoding="utf-8") != content
    ]
    return outdated


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="从 gen/hero 的持久化 JSON 生成 README 使用的双主题静态与动态 SVG。")
    parser.add_argument("--check", action="store_true", help="只检查生成产物是否最新，不写文件；有过期产物时返回 1")
    args = parser.parse_args()
    if args.check:
        outdated = check_assets()
        if outdated:
            for filename in outdated:
                print(f"outdated: assets/hero/{filename}")
            return 1
        print("check: static and motion hero SVGs are up to date  success")
        return 0
    build_assets()
    print("write: static and motion hero SVGs  success")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
