"""Color operations shared by theme generation and SVG rendering."""


def channels(color):
    if color.startswith("#") and len(color) == 7:
        return tuple(int(color[index:index + 2], 16) for index in (1, 3, 5))
    parts = color.split(",")
    if len(parts) == 3 and all(part.isdigit() for part in parts):
        return tuple(int(part) for part in parts)
    raise ValueError(f"Unsupported color: {color}")


def color_string(values, template):
    if template.startswith("#"):
        return "#" + "".join(f"{value:02x}" for value in values)
    return ",".join(str(value) for value in values)


def invert_color(color):
    return color_string([255 - value for value in channels(color)], color)


def mix_color(start, end, amount):
    mixed = [round(a + (b - a) * amount) for a, b in zip(channels(start), channels(end))]
    return color_string(mixed, start)
