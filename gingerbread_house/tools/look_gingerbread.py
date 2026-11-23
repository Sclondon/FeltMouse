# Pictures of every house and every piece from four sides and from above, to look at before shipping:
#
#   blender -b gingerbread_house/tools/gingerbread.blend --python gingerbread_house/tools/look_gingerbread.py -- <out dir> [what]
#
# Writes one sheet for each house, full and low (houses_<name>.png): across it the front, right, back, left
# and top, then a mouse's eye view of the front, then two from inside (looking at the door, looking at
# the back wall); and sheets of four pieces each (pieces_1.png ..., low_pieces_1.png ...).
# `what` picks some: "full", "low", "houses", "pieces", or names of houses. Nothing is saved to the .blend.
# Faces are drawn from their front only, so one wound backwards shows as a hole.
import bpy
import json
import math
import os
import sys

import numpy as np
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = args[0] if args else os.path.join(os.path.dirname(os.path.abspath(__file__)), "look")
picks = args[1:]
os.makedirs(out, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(os.path.dirname(HERE), "models", "gingerbread_houses.json"), encoding="utf-8") as handle:
    MANIFEST = json.load(handle)
CELL = 440
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = CELL
scene.render.resolution_y = CELL
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'Standard'
world = bpy.data.worlds.new("look")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.3, 0.33, 0.4, 1.0)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
scene.world = world
sun = bpy.data.objects.new("look_sun", bpy.data.lights.new("look_sun", 'SUN'))
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(50), 0.0, math.radians(30))
scene.collection.objects.link(sun)
camera = bpy.data.objects.new("look_camera", bpy.data.cameras.new("look_camera"))
scene.collection.objects.link(camera)
scene.camera = camera
camera.data.clip_start = 0.002
camera.data.clip_end = 20.0
parents = [o for o in scene.objects if o.type == 'EMPTY' and o.parent is None]
houses = list(MANIFEST["houses"].keys())
pieces = list(MANIFEST["pieces"].keys())
for o in parents:
    o.location = (0.0, 0.0, 0.0)
bpy.context.view_layer.update()


def kids(parent):
    return [o for o in scene.objects if o.parent == parent and o.type == 'MESH']


def show(parent):
    for p in parents:
        for o in kids(p):
            o.hide_render = p != parent


def frame(parent):
    lo = [1e9] * 3
    hi = [-1e9] * 3
    for o in kids(parent):
        for v in o.data.vertices:
            p = o.matrix_world @ v.co
            for i in range(3):
                lo[i] = min(lo[i], p[i])
                hi[i] = max(hi[i], p[i])
    mid = [(a + b) / 2 for a, b in zip(lo, hi)]
    reach = max(math.hypot(hi[0] - lo[0], hi[1] - lo[1]), hi[2] - lo[2]) * 1.06
    return mid, reach


def read(path):
    image = bpy.data.images.load(path, check_existing=False)
    data = np.array(image.pixels[:], dtype=np.float32).reshape((image.size[1], image.size[0], 4)).copy()
    bpy.data.images.remove(image)
    return data


def save(path, rgba):
    h, w, _ = rgba.shape
    image = bpy.data.images.new("sheet", w, h, alpha=True)
    image.pixels.foreach_set(rgba.ravel())
    image.filepath_raw = path
    image.file_format = 'PNG'
    image.save()
    bpy.data.images.remove(image)


scratch = os.path.join(out, "_cell.png")


def snap():
    scene.render.filepath = scratch
    bpy.ops.render.render(write_still=True)
    return read(scratch)


def aim(eye, at, lens=None):
    eye, at = Vector(eye), Vector(at)
    camera.location = eye
    camera.rotation_euler = (at - eye).to_track_quat('-Z', 'Y').to_euler()
    if lens:
        camera.data.type = 'PERSP'
        camera.data.lens = lens


def shoot(parent, house=None):
    mid, reach = frame(parent)
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = reach
    cells = []
    tilt = math.radians(74)
    for turn in (0, 90, 180, 270):
        a = math.radians(turn)
        back = (math.sin(tilt) * math.sin(a), -math.sin(tilt) * math.cos(a), math.cos(tilt))
        camera.location = (mid[0] + back[0] * 2.0, mid[1] + back[1] * 2.0, mid[2] + back[2] * 2.0)
        camera.rotation_euler = (tilt, 0.0, a)
        cells.append(snap())
    camera.location = (mid[0], mid[1], mid[2] + 2.0)
    camera.rotation_euler = (0.0, 0.0, 0.0)
    cells.append(snap())
    if house:
        slots = MANIFEST["houses"][house]
        door = slots["doors"][0]
        c = Vector((door["c"][0], -door["c"][2], door["c"][1]))
        n = Vector((door["n"][0], -door["n"][2], door["n"][1]))
        light = Vector((slots["light"][0], -slots["light"][2], slots["light"][1]))
        side = n.cross(Vector((0.0, 0.0, 1.0)))
        aim(c + n * 0.15 + side * 0.035 + Vector((0.0, 0.0, 0.022)), c + Vector((0.0, 0.0, 0.06)), 22.0)
        cells.append(snap())
        aim(light - n * 0.03 + Vector((0.0, 0.0, 0.005)), c + Vector((0.0, 0.0, 0.03)), 12.0)
        cells.append(snap())
        aim(light + n * 0.03 + Vector((0.0, 0.0, 0.005)), light - n * 0.3 + Vector((0.0, 0.0, 0.03)), 12.0)
        cells.append(snap())
    return np.concatenate(cells, axis=1)


for low in (False, True):
    tag = "low" if low else "full"
    if ("low" in picks or "full" in picks) and tag not in picks:
        continue
    if "pieces" not in picks or "houses" in picks:
        for name in houses:
            if any(p in houses for p in picks) and name not in picks:
                continue
            parent = bpy.data.objects.get(name + ("_lo" if low else ""))
            show(parent)
            save(os.path.join(out, "houses_%s%s.png" % (name, "_lo" if low else "")), shoot(parent, name))
    if ("houses" not in picks or "pieces" in picks) and not any(p in houses for p in picks):
        rows = []
        for name in pieces:
            parent = bpy.data.objects.get(name + ("_lo" if low else ""))
            show(parent)
            rows.append(shoot(parent))
        for n in range(0, len(rows), 4):
            save(os.path.join(out, "%spieces_%d.png" % ("low_" if low else "", n // 4 + 1)), np.concatenate(list(reversed(rows[n:n + 4])), axis=0))
print("LOOKED", out)
