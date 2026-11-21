"""Serialize the current hero scene as deterministic, self-contained SVG files."""

import math
from html import escape

from hero.color import mix_color
from hero.geometry import (
    camera_position,
    face_visible,
    grid_project,
    ground_from_screen,
    make_cube,
    project_svg,
)
from hero.wakatime import (
    MAX_EDITORS,
    MAX_LANGUAGES,
    MAX_OPERATING_SYSTEMS,
    wakatime_view,
)
from hero.motion import sample_motion
from hero.stack import STACK_CENTER_X, STACK_HEADING, STACK_HEADING_Y, stack_layout, stack_names

CAROUSEL_HOLD_SECONDS = 16.0
CAROUSEL_FADE_SECONDS = 1.0
CAROUSEL_GAP_SECONDS = 0.8
CAROUSEL_PERIOD_SECONDS = 2 * (CAROUSEL_HOLD_SECONDS + CAROUSEL_FADE_SECONDS + CAROUSEL_GAP_SECONDS + CAROUSEL_FADE_SECONDS)
INSIGHTS_HEADING = "CODING INSIGHTS"
STACK_SUBHEADING = "things i sorta know · stuff i tinker with"
MONO_FONT = "ui-monospace, 'Cascadia Mono', Consolas, 'Liberation Mono', monospace"


def number(value):
    return str(value)


def fixed(value, digits=1):
    return f"{value:.{digits}f}"


def point_string(points):
    return " ".join(f"{fixed(point[0])},{fixed(point[1])}" for point in points)


def stops(entries):
    return "".join(
        f'<stop offset="{number(offset)}" stop-color="{color}"/>'
        for offset, color in entries
    )


def ring_irradiance(point, scene, ring):
    """Integrate a horizontal point-light ring above the camera over a ground point."""
    camera = camera_position(scene)
    x, z = point
    sample_count = 64
    total = 0
    for index in range(sample_count):
        angle = 2 * math.pi * (index + 0.5) / sample_count
        dx = camera[0] + ring["radius"] * math.cos(angle) - x
        dy = camera[1] + ring["heightAboveCamera"]
        dz = camera[2] + ring["radius"] * math.sin(angle) - z
        total += dy / (dx * dx + dy * dy + dz * dz) ** 1.5 / sample_count
    return total


def ground_stops(scene, theme):
    """Sample ring illumination along the view center and apply photographic exposure."""
    samples = []
    for index in range(17):
        offset = index / 16
        point = ground_from_screen(scene["width"] / 2, scene["height"] * offset, scene)
        if point is None:
            raise ValueError("The visible ground must cover the vertical view center")
        samples.append((offset, ring_irradiance(point, scene, theme["ringLight"])))
    peak = max(energy for _, energy in samples)
    if peak <= 0:
        raise ValueError("Ring light must illuminate the visible ground")
    return [
        [
            offset,
            mix_color(
                theme["groundBase"],
                theme["groundLit"],
                1 - math.exp(-(theme["ambient"] + theme["ringLight"]["intensity"] * energy / peak)),
            ),
        ]
        for offset, energy in samples
    ]


def classify(normal):
    if normal[1] < -0.5:
        return "bottom"
    if normal[1] > 0.5:
        return "top"
    if normal[0] > 0.35:
        return "lit"
    if normal[2] > 0.35:
        return "main"
    return "side"


def grid_svg(scene, theme, name):
    width, height = scene["width"], scene["height"]
    quad = [ground_from_screen(x, y, scene) for x, y in [(0, 0), (width, 0), (width, height), (0, height)]]
    if any(point is None for point in quad):
        return ""

    def clip_line(axis, value):
        other = 1 - axis
        hits = []
        for index, a in enumerate(quad):
            b = quad[(index + 1) % len(quad)]
            delta = b[axis] - a[axis]
            if abs(delta) < 1e-9:
                continue
            t = (value - a[axis]) / delta
            if t < 0 or t > 1:
                continue
            point = [0, 0]
            point[axis] = value
            point[other] = a[other] + t * (b[other] - a[other])
            hits.append(point)
        if len(hits) < 2:
            return None
        lo, hi = hits[0], hits[0]
        for point in hits:
            if point[other] < lo[other]:
                lo = point
            if point[other] > hi[other]:
                hi = point
        return [grid_project(lo[0], lo[1], scene), grid_project(hi[0], hi[1], scene)]

    grid = scene["grid"]
    step = grid["step"]
    output = [f'<g fill="none" stroke="rgb({theme["grid"]})" mask="url(#{name}-grid-fade)">']
    for axis in range(2):
        lo = min(point[axis] for point in quad)
        hi = max(point[axis] for point in quad)
        start = math.ceil(lo / step) * step
        value = start
        index = math.floor(start / step + 0.5)
        while value <= hi:
            segment = clip_line(axis, value)
            if segment is not None and all(point is not None for point in segment):
                a, b = segment
                major = index % grid["major_every"] == 0
                opacity = theme["gridA"] * (
                    grid["major_opacity"] if major else grid["minor_opacity"] * 0.55
                )
                output.append(
                    f'<line x1="{fixed(a[0])}" y1="{fixed(a[1])}" x2="{fixed(b[0])}" y2="{fixed(b[1])}" '
                    f'stroke-opacity="{number(opacity)}" stroke-width="{1.15 if major else 0.65}"/>'
                )
            value += step
            index += 1
    output.append("</g>")
    return "".join(output)


def projected_cube_faces(scene, world, faces):
    camera = camera_position(scene)
    visible = []
    for face in faces:
        if not face_visible(face, world, camera):
            continue
        projected = [project_svg(world[index], scene) for index in face["v"]]
        if any(point is None for point in projected):
            continue
        depth = sum(point[2] for point in projected) / 4
        visible.append({**face, "pr": projected, "depth": depth})
    visible.sort(key=lambda face: face["depth"], reverse=True)
    return visible


def edge_between(a, b):
    if a is None or b is None:
        return []
    return [vertex for vertex in a["v"] if vertex in b["v"]]


def accent_edges(visible):
    lit_face = next((face for face in visible if classify(face["n"]) == "lit"), None)
    main_face = next((face for face in visible if classify(face["n"]) == "main"), None)
    third_face = next((face for face in visible if classify(face["n"]) not in ("lit", "main")), None)
    return [
        (edge_between(main_face, lit_face), 1.65, 0.96),
        (edge_between(main_face, third_face), 0.85, 0.38),
        (edge_between(lit_face, third_face), 1.05, 0.62),
    ]


def cube_svg(scene, theme, name):
    world, faces = make_cube(scene["cube"])
    visible = projected_cube_faces(scene, world, faces)

    def element_id(suffix):
        return f"{name}-{suffix}"

    output = []
    for face in visible:
        kind = classify(face["n"])
        points = point_string(face["pr"])
        output.append(
            f'<polygon points="{points}" fill="url(#{element_id("metal-" + kind)})" '
            f'stroke="rgb({theme["outlineRGB"]})" stroke-opacity="0.30" stroke-width="2.2" stroke-linejoin="round"/>'
        )
        output.append(
            f'<polygon points="{points}" fill="url(#{element_id("ring-reflection")})"/>'
        )
        if kind in ("main", "lit"):
            opacity = "0.20" if kind == "main" else "0.14"
            output.append(f'<polygon points="{points}" fill="url(#{element_id("sheen")})" opacity="{opacity}"/>')

    def draw_edge(vertices, core_width, core_opacity):
        if len(vertices) != 2:
            return
        a = project_svg(world[vertices[0]], scene)
        b = project_svg(world[vertices[1]], scene)
        if a is None or b is None:
            return
        coords = (
            f'x1="{fixed(a[0])}" y1="{fixed(a[1])}" '
            f'x2="{fixed(b[0])}" y2="{fixed(b[1])}"'
        )
        output.append(
            f'<line {coords} stroke="rgb({theme["edgeSoft"]})" stroke-opacity="{fixed(core_opacity * 0.32, 2)}" '
            f'stroke-width="{fixed(core_width * 5)}" filter="url(#{element_id("edge-blur")})"/>'
        )
        output.append(
            f'<line {coords} stroke="{theme["edge"]}" stroke-opacity="{number(core_opacity)}" stroke-width="{number(core_width)}"/>'
        )

    for vertices, core_width, core_opacity in accent_edges(visible):
        draw_edge(vertices, core_width, core_opacity)
    return "".join(output)


def smil_animation(attribute, values, duration, calc_mode="linear", key_times=None):
    extra = f' keyTimes="{key_times}"' if key_times else ""
    return (
        f'<animate attributeName="{attribute}" dur="{number(duration)}s" repeatCount="indefinite" '
        f'calcMode="{calc_mode}"{extra} values="{values}"/>'
    )


def carousel_values(visible_first):
    """Keyframes that hold a panel, fade out into a blank gap, then fade the panel back in.

    Both panels share one timeline: hold, fade to blank, gap, fade the other panel in,
    hold, fade to blank, gap, fade this panel back — a closed loop with no cross-fade.
    """
    hold = CAROUSEL_HOLD_SECONDS / CAROUSEL_PERIOD_SECONDS
    fade = CAROUSEL_FADE_SECONDS / CAROUSEL_PERIOD_SECONDS
    gap = CAROUSEL_GAP_SECONDS / CAROUSEL_PERIOD_SECONDS
    keys = (
        0.0,
        hold,
        hold + fade,
        hold + fade + gap,
        0.5,
        0.5 + hold,
        0.5 + hold + fade,
        0.5 + hold + fade + gap,
        1.0,
    )
    first = ("1", "1", "0", "0", "0", "0", "0", "0", "1")
    second = ("0", "0", "0", "0", "1", "1", "0", "0", "0")
    values = first if visible_first else second
    return ";".join(values), ";".join(f"{key:.6f}" for key in keys)


def motion_cube_svg(scene, theme, name, motion):
    """Serialize precomputed motion; the browser never evaluates scene geometry."""
    frames = motion["frames"]
    duration = motion["period_seconds"]
    initial_world, initial_faces = make_cube(scene["cube"])
    visible = projected_cube_faces(scene, initial_world, initial_faces)
    face_by_tag = {face["tag"]: face for face in initial_faces}
    initial_points = frames[0]["points"]

    def element_id(suffix):
        return f"{name}-motion-{suffix}"

    definitions = []
    output = []
    for face in initial_faces:
        tag = face["tag"]
        kind = classify(face["n"])
        face_id = element_id(f"face-{tag}")
        initial = point_string([initial_points[index] for index in face["v"]])
        point_values = ";".join(
            point_string([frame["points"][index] for index in face["v"]])
            for frame in frames
        )
        definitions.append(
            f'<polygon id="{face_id}" points="{initial}">'
            f'{smil_animation("points", point_values, duration)}</polygon>'
        )
        visibility_values = ";".join(
            "visible" if frame["visible"][tag] else "hidden"
            for frame in frames
        )
        initial_visibility = "visible" if frames[0]["visible"][tag] else "hidden"
        uses = [
            f'<use href="#{face_id}" fill="url(#{name}-metal-{kind})" stroke="rgb({theme["outlineRGB"]})" '
            f'stroke-opacity="0.30" stroke-width="2.2" stroke-linejoin="round"/>',
            f'<use href="#{face_id}" fill="url(#{name}-ring-reflection)"/>',
        ]
        if kind in ("main", "lit"):
            opacity = "0.20" if kind == "main" else "0.14"
            uses.append(
                f'<use href="#{face_id}" fill="url(#{name}-sheen)" opacity="{opacity}"/>'
            )
        output.append(
            f'<g visibility="{initial_visibility}">'
            f'{smil_animation("visibility", visibility_values, duration, "discrete")}{"".join(uses)}</g>'
        )

    for edge_index, (vertices, core_width, core_opacity) in enumerate(accent_edges(visible)):
        if len(vertices) != 2:
            continue
        edge_id = element_id(f"edge-{edge_index}")
        initial = [initial_points[index] for index in vertices]
        definitions.append(
            f'<line id="{edge_id}" x1="{fixed(initial[0][0])}" y1="{fixed(initial[0][1])}" '
            f'x2="{fixed(initial[1][0])}" y2="{fixed(initial[1][1])}">'
            + "".join(
                smil_animation(
                    attribute,
                    ";".join(fixed(frame["points"][vertex][axis]) for frame in frames),
                    duration,
                )
                for vertex, axis, attribute in [
                    (vertices[0], 0, "x1"),
                    (vertices[0], 1, "y1"),
                    (vertices[1], 0, "x2"),
                    (vertices[1], 1, "y2"),
                ]
            )
            + "</line>"
        )
        incident_faces = [
            tag for tag, face in face_by_tag.items()
            if all(vertex in face["v"] for vertex in vertices)
        ]
        visibility_values = ";".join(
            "visible" if any(frame["visible"][tag] for tag in incident_faces) else "hidden"
            for frame in frames
        )
        initial_visibility = "visible" if any(frames[0]["visible"][tag] for tag in incident_faces) else "hidden"
        output.append(
            f'<g visibility="{initial_visibility}">'
            f'{smil_animation("visibility", visibility_values, duration, "discrete")}'
            f'<use href="#{edge_id}" stroke="rgb({theme["edgeSoft"]})" '
            f'stroke-opacity="{fixed(core_opacity * 0.32, 2)}" stroke-width="{fixed(core_width * 5)}" '
            f'filter="url(#{name}-edge-blur)"/>'
            f'<use href="#{edge_id}" stroke="{theme["edge"]}" stroke-opacity="{number(core_opacity)}" '
            f'stroke-width="{number(core_width)}"/></g>'
        )
    return f'<g id="{element_id("cube")}"><defs>{"".join(definitions)}</defs>{"".join(output)}</g>'


def heading_svg(theme, name, motion, wakatime):
    """One static heading, or the two carousel headings cross-fading in place."""
    ink = f'fill="rgb({theme["stack"]})" color="rgb({theme["stack"]})" fill-opacity="{number(theme["stackA"])}"'
    carousel = motion is not None and wakatime is not None
    headings = [STACK_HEADING] + ([INSIGHTS_HEADING] if carousel else [])
    output = [f'<g id="{name}-stack-heading" {ink}>']
    for index, text in enumerate(headings):
        visible_first = index == 0
        initial = "1" if visible_first or not carousel else "0"
        output.append(f'<g opacity="{initial}">')
        if carousel:
            values, key_times = carousel_values(visible_first)
            output.append(smil_animation(
                "opacity", values, CAROUSEL_PERIOD_SECONDS, key_times=key_times,
            ))
        output.append(
            f'<text x="{STACK_CENTER_X}" y="{STACK_HEADING_Y}" text-anchor="middle" '
            f'font-family="{MONO_FONT}" font-size="30" font-weight="500" '
            f'letter-spacing="6">{text}</text>'
        )
        if index == 0:
            output.append(
                f'<text x="{STACK_CENTER_X}" y="150" text-anchor="middle" '
                f'font-family="{MONO_FONT}" font-size="13" letter-spacing="3" '
                f'opacity="0.78">{escape(STACK_SUBHEADING)}</text>'
            )
        output.append("</g>")
    output.append("</g>")
    return "".join(output)


def stack_svg(theme, name, stack, carousel):
    """Inline the shared static icon geometry; no labels, scripts or runtime requests."""
    ink = f'fill="rgb({theme["stack"]})" color="rgb({theme["stack"]})" fill-opacity="{number(theme["stackA"])}"'
    output = [f'<g id="{name}-stack" {ink}>']
    if carousel:
        values, key_times = carousel_values(True)
        output.append(f'<g opacity="1">{smil_animation("opacity", values, CAROUSEL_PERIOD_SECONDS, key_times=key_times)}')
    output.append('<!-- Static local technology icons; intentionally outside the animated cube group. -->')
    for placement in stack_layout():
        icon = stack[placement["id"]]
        output.append(
            f'<g id="{name}-stack-{placement["id"]}" '
            f'transform="translate({placement["x"]:g} {placement["y"]:g}) '
            f'scale({placement["size"] / 24:g})">'
            f'<title>{escape(icon["name"])}</title>{icon["geometry"]}</g>'
        )
    if carousel:
        output.append('</g>')
    output.append("</g>")
    return "".join(output)


def format_percent(percent):
    text = f"{percent:.2f}".rstrip("0").rstrip(".")
    return f"{text}%"


def wakatime_svg(theme, name, view):
    """Draw the CODING INSIGHTS carousel page from the bounded snapshot view."""
    ink = f'fill="rgb({theme["stack"]})" color="rgb({theme["stack"]})" fill-opacity="{number(theme["stackA"])}"'
    values, key_times = carousel_values(False)
    output = [
        f'<g id="{name}-insights" {ink}>',
        f'<g opacity="0">{smil_animation("opacity", values, CAROUSEL_PERIOD_SECONDS, key_times=key_times)}',
    ]

    def label(x, y, text, size=13, spacing=2.5):
        return (
            f'<text x="{x}" y="{y}" text-anchor="middle" font-family="{MONO_FONT}" '
            f'font-size="{size}" letter-spacing="{spacing}" opacity="0.78">{text}</text>'
        )

    output.append(label(STACK_CENTER_X, 156,
                        f'{view["range_label"]} · UPDATED {view["updated_label"]}', 13, 3))
    for center_x, text, value in (
        (700, "TOTAL CODING TIME", view["total"]),
        (1260, "DAILY AVERAGE", view["daily_average"]),
    ):
        output.append(label(center_x, 232, text))
        output.append(
            f'<text x="{center_x}" y="276" text-anchor="middle" font-family="{MONO_FONT}" '
            f'font-size="34" font-weight="500" letter-spacing="0.5">{escape(value)}</text>'
        )

    def bars(entries, slots, name_x, bar_x, bar_max, percent_x, first_y, step):
        """Draw a fixed number of rows; empty slots render a low-opacity dash."""
        peak = max(percent for _, percent in entries)
        drawn = []
        for index in range(slots):
            y = first_y + index * step
            if index < len(entries):
                entry, percent = entries[index]
                width = percent / peak * bar_max
                drawn.append(
                    f'<text x="{name_x}" y="{y}" font-family="{MONO_FONT}" '
                    f'font-size="20">{escape(entry)}</text>'
                )
                drawn.append(
                    f'<rect x="{bar_x}" y="{y - 14}" width="{width:.1f}" height="10" rx="5"/>'
                )
                drawn.append(
                    f'<text x="{percent_x}" y="{y}" text-anchor="end" font-family="{MONO_FONT}" '
                    f'font-size="16" opacity="0.92">{format_percent(percent)}</text>'
                )
            else:
                for anchor, x, size in (("start", name_x, 20), ("end", percent_x, 16)):
                    drawn.append(
                        f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{MONO_FONT}" '
                        f'font-size="{size}" opacity="0.3">-</text>'
                    )
        return drawn

    def group_label(x, y, text):
        return (
            f'<text x="{x}" y="{y}" font-family="{MONO_FONT}" font-size="15" '
            f'letter-spacing="3" opacity="0.78">{text}</text>'
        )

    output.append(group_label(420, 352, "LANGUAGES"))
    output += bars(view["languages"], MAX_LANGUAGES, 420, 580, 380, 1040, 400, 66)
    output.append(group_label(1090, 352, "EDITORS"))
    output += bars(view["editors"], MAX_EDITORS, 1090, 1262, 188, 1520, 400, 66)
    output.append(group_label(1090, 600, "OPERATING SYSTEM"))
    output += bars(view["operating_systems"], MAX_OPERATING_SYSTEMS, 1090, 1262, 188, 1520, 648, 66)

    output.append('</g></g>')
    return "".join(output)


def render_svg(scene, theme, name, ground_entries, stack, motion=None, wakatime=None):
    width, height = scene["width"], scene["height"]

    def element_id(suffix):
        return f"{name}-{suffix}"

    metal_gradients = "".join(
        f'<linearGradient id="{element_id("metal-" + kind)}" gradientUnits="userSpaceOnUse" '
        f'x1="0" y1="0" x2="0" y2="{height}">{stops(entries)}</linearGradient>'
        for kind, entries in theme["metal"].items()
    )
    fade_stops = "".join(
        f'<stop offset="{number(offset)}" stop-color="#ffffff" stop-opacity="{number(opacity)}"/>'
        for offset, opacity in scene["grid"]["fade"]
    )
    label = "浅色" if name == "light" else "深色"
    variant = "动态" if motion is not None else ""
    title = escape(f"{label}{variant}主题：斜向俯视网格、左侧超画框金属体与右侧技术栈图标")
    atmosphere = "高强度环形曝光使四缘接近页面背景" if name == "dark" else "高曝光地面接近页面背景"
    movement = "；立方体沿相机空间的三个轴缓慢旋转" if motion is not None else ""
    carousel = motion is not None and wakatime is not None
    technologies = escape("、".join(stack_names()))
    if carousel:
        right_panel = (
            f"右侧面板在 {STACK_HEADING} 技术栈图标（{technologies}）与 {INSIGHTS_HEADING} 编码统计之间"
            f"每 {CAROUSEL_PERIOD_SECONDS:.0f} 秒轮换：旧页淡出后短暂留白，再淡入新页。"
        )
    else:
        right_panel = f"右侧 {STACK_HEADING} 标题与静态技术栈图标：{technologies}。"
    description = (
        f"相机上方的环形光源照亮地面并形成金属环境反射，{atmosphere}；"
        f"无四缘透明淡出{movement}。{right_panel}"
    )
    heading = heading_svg(theme, name, motion, wakatime)
    icons = stack_svg(theme, name, stack, carousel)
    insights = wakatime_svg(theme, name, wakatime_view(wakatime)) if carousel else ""
    cube = motion_cube_svg(scene, theme, name, motion) if motion is not None else cube_svg(scene, theme, name)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="{name}-title {name}-description">
<title id="{name}-title">{title}</title>
<desc id="{name}-description">{description}</desc>
<!-- Generated by scripts/build_hero.py. Do not edit directly. -->
<defs>
<linearGradient id="{element_id("ground")}" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="{height}">{stops(ground_entries)}</linearGradient>
{metal_gradients}
<linearGradient id="{element_id("sheen")}" x1="0" y1="0" x2="1" y2="0.65">
<stop offset="0" stop-color="{theme["sheen"]}" stop-opacity="0"/>
<stop offset="0.42" stop-color="{theme["sheen"]}" stop-opacity="0.22"/>
<stop offset="0.68" stop-color="{theme["sheen"]}" stop-opacity="0"/>
</linearGradient>
<radialGradient id="{element_id("ring-reflection")}" gradientUnits="userSpaceOnUse" cx="{width / 2}" cy="{height / 2}" r="{width * theme["reflectionRadius"]}">
<stop offset="0" stop-color="rgb({theme["horizonRGB"]})" stop-opacity="0"/>
<stop offset="0.54" stop-color="rgb({theme["horizonRGB"]})" stop-opacity="0"/>
<stop offset="0.68" stop-color="rgb({theme["horizonRGB"]})" stop-opacity="{number(theme["reflectionA"])}"/>
<stop offset="0.76" stop-color="rgb({theme["horizonRGB"]})" stop-opacity="{number(theme["reflectionA"] * 0.55)}"/>
<stop offset="0.88" stop-color="rgb({theme["horizonRGB"]})" stop-opacity="0"/>
<stop offset="1" stop-color="rgb({theme["horizonRGB"]})" stop-opacity="0"/>
</radialGradient>
<linearGradient id="{element_id("grid-fade-gradient")}" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="{height}">{fade_stops}</linearGradient>
<mask id="{element_id("grid-fade")}" maskUnits="userSpaceOnUse" x="0" y="0" width="{width}" height="{height}">
<rect width="{width}" height="{height}" fill="url(#{element_id("grid-fade-gradient")})"/>
</mask>
<filter id="{element_id("edge-blur")}" x="-40%" y="-40%" width="180%" height="180%" color-interpolation-filters="sRGB"><feGaussianBlur stdDeviation="4"/></filter>
</defs>
<rect width="{width}" height="{height}" fill="url(#{element_id("ground")})"/>
{grid_svg(scene, theme, name)}
{cube}
{heading}{icons}{insights}
</svg>
'''


def render_hero(scene, themes, stack, wakatime=None):
    """Return static and declarative-motion filename/content pairs without filesystem access."""
    ground = {name: ground_stops(scene, themes[name]) for name in ("light", "dark")}
    motion = sample_motion(scene)
    outputs = {}
    for name in ("light", "dark"):
        outputs[f"hero-{name}.svg"] = render_svg(
            scene, themes[name], name, ground[name], stack, wakatime=wakatime
        )
        outputs[f"hero-{name}-motion.svg"] = render_svg(
            scene, themes[name], name, ground[name], stack, motion, wakatime=wakatime
        )
    return outputs
