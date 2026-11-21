"""Camera, cube, and ground-grid geometry shared by scene tools and SVG output."""

import math


def add(a, b):
    return [x + y for x, y in zip(a, b)]


def subtract(a, b):
    return [x - y for x, y in zip(a, b)]


def mat_vec(matrix, vector):
    return [sum(value * vector[column] for column, value in enumerate(row)) for row in matrix]


def mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def rotation_x(angle):
    c, s = math.cos(angle), math.sin(angle)
    return [[1, 0, 0], [0, c, -s], [0, s, c]]


def rotation_y(angle):
    c, s = math.cos(angle), math.sin(angle)
    return [[c, 0, s], [0, 1, 0], [-s, 0, c]]


def rotation_z(angle):
    c, s = math.cos(angle), math.sin(angle)
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def cube_rotation(rotation_degrees):
    rx, ry, rz = [math.radians(value) for value in rotation_degrees]
    return mat_mul(rotation_z(rz), mat_mul(rotation_y(ry), rotation_x(rx)))


def rotation_to_euler(matrix):
    """Return the rx, ry, rz angles for the shared Rz @ Ry @ Rx convention."""
    if abs(abs(matrix[2][0]) - 1) < 1e-10:
        raise ValueError("Gimbal lock is not supported by this parameter writer")
    rx = math.atan2(matrix[2][1], matrix[2][2])
    ry = math.asin(-matrix[2][0])
    rz = math.atan2(matrix[1][0], matrix[0][0])
    return [math.degrees(value) for value in (rx, ry, rz)]


def camera_position(scene):
    camera = scene["camera"]
    return [camera["x"], camera["height"], camera["z"]]


def rot3(point, ax, ay, az):
    x, y, z = point
    c, s = math.cos(ax), math.sin(ax)
    y, z = y * c - z * s, y * s + z * c
    c, s = math.cos(ay), math.sin(ay)
    x, z = x * c + z * s, -x * s + z * c
    c, s = math.cos(az), math.sin(az)
    x, y = x * c - y * s, x * s + y * c
    return [x, y, z]


def cube_vertices(scene):
    cube = scene["cube"]
    half = cube["size"] / 2
    rotation = cube_rotation(cube["rotation_degrees"])
    local = [
        [x * half, y * half, z * half]
        for x, y, z in [
            (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
            (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),
        ]
    ]
    return [add(cube["center"], mat_vec(rotation, point)) for point in local]


def make_cube(cube, rotation=None):
    rx, ry, rz = [math.radians(value) for value in cube["rotation_degrees"]]
    half = cube["size"] / 2
    local = [
        [-half, -half, -half], [half, -half, -half], [half, half, -half], [-half, half, -half],
        [-half, -half, half], [half, -half, half], [half, half, half], [-half, half, half],
    ]
    if rotation is None:
        world = [add(cube["center"], rot3(point, rx, ry, rz)) for point in local]
    else:
        world = [add(cube["center"], mat_vec(rotation, point)) for point in local]
    definitions = [
        {"n": [0, 0, -1], "v": [0, 3, 2, 1], "tag": "back"},
        {"n": [0, 0, 1], "v": [4, 5, 6, 7], "tag": "main"},
        {"n": [-1, 0, 0], "v": [0, 4, 7, 3], "tag": "left"},
        {"n": [1, 0, 0], "v": [1, 2, 6, 5], "tag": "right"},
        {"n": [0, -1, 0], "v": [0, 1, 5, 4], "tag": "bottom"},
        {"n": [0, 1, 0], "v": [3, 7, 6, 2], "tag": "top"},
    ]
    if rotation is None:
        faces = [{**face, "n": rot3(face["n"], rx, ry, rz)} for face in definitions]
    else:
        faces = [{**face, "n": mat_vec(rotation, face["n"])} for face in definitions]
    return world, faces


def face_visible(face, world, camera):
    center = [sum(world[index][axis] for index in face["v"]) / 4 for axis in range(3)]
    view = [camera[axis] - center[axis] for axis in range(3)]
    return sum(face["n"][axis] * view[axis] for axis in range(3)) > 0


def _project(point, scene):
    camera = scene["camera"]
    pitch = -math.radians(camera["pitch_degrees"])
    yaw = math.radians(camera["yaw_degrees"])
    cp, sp = math.cos(pitch), math.sin(pitch)
    cyaw, syaw = math.cos(yaw), math.sin(yaw)
    x, y, z = point
    x -= camera["x"]
    y -= camera["height"]
    z -= camera["z"]
    x, z = x * cyaw - z * syaw, x * syaw + z * cyaw
    yv = y * cp + z * sp
    zv = -y * sp + z * cp
    depth = -zv
    focal = scene["width"] * camera["lens_mm"] / camera["sensor_width"]
    cx = scene["width"] / 2
    cy = scene["height"] / 2 + camera["shift_y"] * scene["width"]
    return [cx + focal * x / depth, cy - focal * yv / depth, depth]


def project(point, scene):
    projected = _project(point, scene)
    if projected[2] <= 0:
        raise ValueError("Cube vertex is behind the camera")
    return projected


def project_svg(point, scene):
    projected = _project(point, scene)
    return projected if projected[2] > 0.1 else None


def horizon_y(scene):
    camera = scene["camera"]
    focal = scene["width"] * camera["lens_mm"] / camera["sensor_width"]
    cy = scene["height"] / 2 + camera["shift_y"] * scene["width"]
    return cy - focal * math.tan(math.radians(camera["pitch_degrees"]))


def grid_project(x, z, scene):
    angle = math.radians(scene["grid"]["yaw_degrees"])
    c, s = math.cos(angle), math.sin(angle)
    return project_svg([x * c + z * s, 0, -x * s + z * c], scene)


def ground_from_screen(sx, sy, scene):
    camera = scene["camera"]
    pitch = -math.radians(camera["pitch_degrees"])
    cp, sp = math.cos(pitch), math.sin(pitch)
    focal = scene["width"] * camera["lens_mm"] / camera["sensor_width"]
    cx = scene["width"] / 2
    cy = scene["height"] / 2 + camera["shift_y"] * scene["width"]
    u = (sx - cx) / focal
    v = (cy - sy) / focal
    depth = -camera["height"] / (cp * v + sp)
    if depth <= 0:
        return None
    x0 = u * depth
    z0 = (sp * v - cp) * depth
    yaw = math.radians(camera["yaw_degrees"])
    cyaw, syaw = math.cos(yaw), math.sin(yaw)
    x = camera["x"] + x0 * cyaw + z0 * syaw
    z = camera["z"] - x0 * syaw + z0 * cyaw
    angle = math.radians(scene["grid"]["yaw_degrees"])
    c, s = math.cos(angle), math.sin(angle)
    return [x * c - z * s, x * s + z * c]


def projection_error(before, after):
    old_points = [project(point, before) for point in cube_vertices(before)]
    new_points = [project(point, after) for point in cube_vertices(after)]
    return max(
        abs(a - b)
        for old, new in zip(old_points, new_points)
        for a, b in zip(old[:2], new[:2])
    )
