# Pictures of every present, bow and the tag from four sides and from above, to look at before shipping:
#
#   blender -b presents/tools/presents.blend --python presents/tools/look_presents.py -- <out dir> [what]
#
# Writes sheets of four models each: a row for a model, across it the front, right, back, left and top.
#   full_cross_1.png ...   every present tied crosswise (the bag and bows as they are)
#   full_band_1.png ...    the presents with one band, full_diag_1.png the boxes tied across their corners
#   low_...                the same for the low models
# `what` picks some: "full", "low", "cross", "band", "diag" (any of them, space apart). Nothing is saved
# to the .blend.
import bpy
import math
import os
import sys

import numpy as np

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = args[0] if args else os.path.join(os.path.dirname(__file__), "look")
picks = args[1:]
os.makedirs(out, exist_ok=True)
CELL = 480
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = CELL
scene.render.resolution_y = CELL
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'Standard'
world = bpy.data.worlds.new("look")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.32, 0.34, 0.38, 1.0)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
scene.world = world
sun = bpy.data.objects.new("look_sun", bpy.data.lights.new("look_sun", 'SUN'))
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(50), 0.0, math.radians(30))
scene.collection.objects.link(sun)
camera = bpy.data.objects.new("look_camera", bpy.data.cameras.new("look_camera"))
camera.data.type = 'ORTHO'
scene.collection.objects.link(camera)
scene.camera = camera
parents = [o for o in scene.objects if o.type == 'EMPTY' and o.parent is None]
order = ["cube", "shirt_box", "tall_box", "long_box", "drum", "bag", "hat_box", "parcel", "bow_classic", "bow_pompom",
         "bow_rosette", "bow_string", "tag"]
for o in parents:
    o.location = (0.0, 0.0, 0.0)


def kids(parent):
    return [o for o in scene.objects if o.parent == parent]


def show(parent, tie):
    """Only this model, tied this way. False if it has no such tie."""
    found = False
    for p in parents:
        for o in kids(p):
            o.hide_render = True
    for o in kids(parent):
        piece = o.name[len(parent.name) + 1:]
        if o.type != 'MESH':
            continue
        if piece.startswith("ribbon_"):
            o.hide_render = piece != "ribbon_" + tie
            found = found or not o.hide_render
        else:
            o.hide_render = False
    return found


def frame(parent):
    lo = [1e9] * 3
    hi = [-1e9] * 3
    for o in kids(parent):
        if o.type == 'MESH' and not o.hide_render:
            for v in o.data.vertices:
                for i in range(3):
                    lo[i] = min(lo[i], v.co[i])
                    hi[i] = max(hi[i], v.co[i])
    mid = [(a + b) / 2 for a, b in zip(lo, hi)]
    reach = max(math.hypot(hi[0] - lo[0], hi[1] - lo[1]), hi[2] - lo[2]) * 1.08
    return mid, reach


def shoot(parent, path):
    mid, reach = frame(parent)
    camera.data.ortho_scale = reach
    cells = []
    tilt = math.radians(72)
    for turn in (0, 90, 180, 270):
        a = math.radians(turn)
        back = (math.sin(tilt) * math.sin(a), -math.sin(tilt) * math.cos(a), math.cos(tilt))
        camera.location = (mid[0] + back[0] * 2.0, mid[1] + back[1] * 2.0, mid[2] + back[2] * 2.0)
        camera.rotation_euler = (tilt, 0.0, a)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        cells.append(read(path))
    camera.location = (mid[0], mid[1], mid[2] + 2.0)
    camera.rotation_euler = (0.0, 0.0, 0.0)
    bpy.ops.render.render(write_still=True)
    cells.append(read(path))
    return np.concatenate(cells, axis=1)


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
for low in (False, True):
    if picks and ("low" if low else "full") not in picks and ("low" in picks or "full" in picks):
        continue
    for tie in ("cross", "band", "diag"):
        if picks and tie not in picks and any(t in picks for t in ("cross", "band", "diag")):
            continue
        rows = []
        for name in order:
            parent = bpy.data.objects.get(name + ("_lo" if low else ""))
            if parent is None:
                continue
            tied = show(parent, tie)
            if tie != "cross" and not tied:
                continue
            rows.append(shoot(parent, scratch))
        for n in range(0, len(rows), 4):
            sheet = np.concatenate(list(reversed(rows[n:n + 4])), axis=0)
            save(os.path.join(out, "%s_%s_%d.png" % ("low" if low else "full", tie, n // 4 + 1)), sheet)
print("LOOKED", out)
