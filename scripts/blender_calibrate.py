import bpy
import math
from pathlib import Path
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]

# Minimal calibration scene: perspective, ground grid, and the cube's frame crop.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1600
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = str(ROOT / 'design' / 'references' / '_blender_reference.png')

world = bpy.data.worlds.new('Calibration World')
scene.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.12, 0.12, 0.12, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6


def material(name, color, roughness=0.7, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metallic
    return mat


floor_mat = material('Ground', (0.18, 0.19, 0.20))
grid_mat = material('Grid', (0.42, 0.44, 0.46))
cube_mat = material('Cube', (0.36, 0.39, 0.42), roughness=0.42, metallic=0.55)

bpy.ops.mesh.primitive_plane_add(size=20000, location=(0, 0, -0.02))
floor = bpy.context.object
floor.data.materials.append(floor_mat)

# BEGIN GENERATED CUBE
bpy.ops.mesh.primitive_cube_add(size=4.24, location=(33.172317955, -75.409745754, 46.274368262))
cube = bpy.context.object
cube.rotation_euler = Matrix((
    (0.804133984, 0.142649415, 0.577078574),
    (-0.146934229, -0.892960038, 0.425479379),
    (0.57600249, -0.426935023, -0.697099431)
)).to_euler()
# END GENERATED CUBE
cube.data.materials.append(cube_mat)

curve = bpy.data.curves.new('Ground Grid', 'CURVE')
curve.dimensions = '3D'
curve.resolution_u = 1
curve.bevel_depth = 0.009
curve.bevel_resolution = 0
angle = math.radians(30)
c, s = math.cos(angle), math.sin(angle)

def add_grid_line(points):
    spline = curve.splines.new('POLY')
    spline.points.add(len(points) - 1)
    for point, (x, y) in zip(spline.points, points):
        point.co = (x * c + y * s, x * s - y * c, 0.008, 1)

for i in range(-250, 251):
    v = i * 2.0
    add_grid_line([(-5000, v), (5000, v)])
    add_grid_line([(v, -5000), (v, 5000)])

grid = bpy.data.objects.new('Ground Grid', curve)
scene.collection.objects.link(grid)
grid.data.materials.append(grid_mat)

# BEGIN GENERATED CAMERA
bpy.ops.object.camera_add(location=(42.458938117, -83.279365396, 48.7862838))
camera = bpy.context.object
pitch = math.radians(15)
direction = Vector((-0.33036609, 0.907673371, -math.sin(pitch)))
camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
camera.data.lens = 50
camera.data.sensor_width = 36
camera.data.shift_y = 0
camera.data.clip_end = 500
scene.camera = camera
# END GENERATED CAMERA

bpy.ops.object.light_add(type='AREA', location=(2, -4, 16))
light = bpy.context.object
light.data.energy = 1800
light.data.shape = 'DISK'
light.data.size = 9
light.rotation_euler = (Vector((-3, 2, 4)) - light.location).to_track_quat('-Z', 'Y').to_euler()

scene.view_settings.view_transform = 'AgX'
bpy.ops.render.render(write_still=True)

# Print the projected cube bounds for transferring composition back to SVG.
from bpy_extras.object_utils import world_to_camera_view
points = [world_to_camera_view(scene, camera, cube.matrix_world @ Vector(corner)) for corner in cube.bound_box]
print('CAMERA_PITCH_DEGREES=', math.degrees(pitch))
print('CAMERA_LENS_MM=', camera.data.lens)
print('CUBE_NDC_BOUNDS=', min(p.x for p in points), max(p.x for p in points), min(p.y for p in points), max(p.y for p in points))
horizon = world_to_camera_view(
    scene,
    camera,
    camera.location + Vector((direction.x, direction.y, 0)) * 10000000
)
print('HORIZON_NDC=', horizon.x, horizon.y, 'SCREEN_Y=', (1 - horizon.y) * scene.render.resolution_y)
