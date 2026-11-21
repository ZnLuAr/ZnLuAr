#!/usr/bin/env python3
"""Persist the hero's theme variables and rebuild its static and motion SVG assets."""

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from build_hero import expected_assets
from hero.color import invert_color, mix_color
from hero.scene import ASSET_DIR, SCENE_PATH, THEMES_PATH, load_json, write_json, write_text


def invert_theme(value):
    if isinstance(value, dict):
        return {key: invert_theme(item) for key, item in value.items()}
    if isinstance(value, list):
        return [invert_theme(item) for item in value]
    if isinstance(value, str):
        return invert_color(value)
    return value


METAL_LIFT = 0.20


def lift_metal(metal, amount=METAL_LIFT):
    """Lift each metallic stop toward white without flattening its gradient offsets."""
    return {
        kind: [[offset, mix_color(color, "#ffffff", amount)] for offset, color in entries]
        for kind, entries in metal.items()
    }


def base_light_theme():
    return {
        "groundBase": "#9aaab2",
        "groundLit": "#ffffff",
        "ambient": 2.8,
        "ringLight": {"radius": 72, "heightAboveCamera": 16, "intensity": 1.3},
        "horizonRGB": "255,255,250",
        "reflectionA": 0.55,
        "reflectionRadius": 0.48,
        "grid": "66,82,92",
        "gridA": 0.38,
        "stack": "66,82,92",
        "stackA": 0.88,
        "metal": {
            "main": [[0, "#71818a"], [0.5, "#a8b4b9"], [1, "#465660"]],
            "lit": [[0, "#94a2aa"], [0.5, "#c7d0d1"], [1, "#647680"]],
            "side": [[0, "#64747e"], [0.5, "#8e9ca4"], [1, "#455761"]],
            "bottom": [[0, "#58656e"], [0.55, "#3e4a54"], [1, "#303b45"]],
            "top": [[0, "#a0afb6"], [0.5, "#c0c9cc"], [1, "#71838f"]],
        },
        "edge": "#f5f7f3",
        "edgeSoft": "213,224,226",
        "sheen": "#ffffff",
        "outlineRGB": "5,10,14",
    }


def theme_state():
    light = base_light_theme()
    dark = invert_theme(light)
    light["metal"] = lift_metal(light["metal"])
    dark["metal"] = lift_metal(dark["metal"])
    dark.update({
        "groundBase": "#000000",
        "groundLit": "#090c11",
        "ambient": 0,
        "ringLight": {**light["ringLight"], "intensity": 1000},
    })
    return {"light": light, "dark": dark}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    themes = theme_state()
    scene = load_json(SCENE_PATH)
    outputs = expected_assets(scene, themes)  # Validate the complete render before replacing persistent state.
    write_json(THEMES_PATH, themes)
    for filename, content in outputs.items():
        write_text(ASSET_DIR / filename, content)
    print("write: gen/hero/themes.json, static and motion hero SVGs  success")


if __name__ == "__main__":
    main()
