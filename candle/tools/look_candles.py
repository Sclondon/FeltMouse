# Pictures of every candle from four sides and from above, to look at before shipping a change:
#
#   blender -b candle/tools/candles.blend --python candle/tools/look_candles.py -- <out dir>
#
# Writes <out dir>/full_new_front.png, _right, _back, _left and _top, the same as full_burnt_* (the shape
# key at 1), and both again for the low models as low_*. Nothing is saved to the .blend.
import bpy
import math
import os
import sys

out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else os.path.join(os.path.dirname(__file__), "look")
os.makedirs(out, exist_ok=True)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 2400
scene.view_settings.view_transform = 'Standard'
world = bpy.data.worlds.new("look")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.2, 0.21, 0.24, 1.0)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
scene.world = world
sun = bpy.data.objects.new("look_sun", bpy.data.lights.new("look_sun", 'SUN'))
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(50), 0.0, math.radians(30))
scene.collection.objects.link(sun)
camera = bpy.data.objects.new("look_camera", bpy.data.cameras.new("look_camera"))
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 1.22
scene.collection.objects.link(camera)
scene.camera = camera
parents = [o for o in scene.objects if o.type == 'EMPTY' and o.parent is None]
middle = (max(o.location.x for o in parents) + min(o.location.x for o in parents)) * 0.5
for o in parents:
    o.location.y = 0.0


def show(low):
    for o in scene.objects:
        top = o if o.parent is None else o.parent
        if top in parents:
            o.hide_render = top.name.endswith("_lo") != low


for low in (False, True):
    show(low)
    for burnt in (0.0, 1.0):
        for o in scene.objects:
            if o.type == 'MESH' and o.data.shape_keys:
                o.data.shape_keys.key_blocks["burnt"].value = burnt
        tag = ("low_" if low else "full_") + ("burnt" if burnt else "new")
        scene.render.resolution_y = 640
        tilt = math.radians(70)
        for view, turn in (("front", 0), ("right", 90), ("back", 180), ("left", 270)):
            for o in parents:
                o.rotation_euler = (0.0, 0.0, math.radians(-turn))
            # looking at a point 0.13 m up the row, from in front and a little above
            camera.location = (middle, -2.0 * math.sin(tilt), 0.13 + 2.0 * math.cos(tilt))
            camera.rotation_euler = (tilt, 0.0, 0.0)
            scene.render.filepath = os.path.join(out, "%s_%s.png" % (tag, view))
            bpy.ops.render.render(write_still=True)
        for o in parents:
            o.rotation_euler = (0.0, 0.0, 0.0)
        scene.render.resolution_y = 300
        camera.location = (middle, 0.0, 2.0)
        camera.rotation_euler = (0.0, 0.0, 0.0)
        scene.render.filepath = os.path.join(out, "%s_top.png" % tag)
        bpy.ops.render.render(write_still=True)
print("LOOKED", out)
