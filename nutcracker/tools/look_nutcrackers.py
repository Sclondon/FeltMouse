# Pictures of every nutcracker from four sides and from above, to look at before shipping a change:
#
#   blender -b nutcracker/tools/nutcrackers.blend --python nutcracker/tools/look_nutcrackers.py -- <out dir>
#
# Writes <out dir>/full_front.png, _right, _back, _left and _top (the five figures in a row, in the
# classic colours), the same for the low models as low_*, and the full models in two poses at the ends
# of their travel as pose_a_* (jaw wide open, saluting, left arm forward) and pose_b_* (jaw half open,
# arms back, the moustache crooked). Also walnuts.png. Nothing is saved to the .blend.
import math
import os
import sys

import bpy
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_nutcrackers as build  # noqa: E402  (its numbers for the poses; it builds nothing when imported)

out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else os.path.join(HERE, "look")
os.makedirs(out, exist_ok=True)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.view_settings.view_transform = 'Standard'
world = bpy.data.worlds.new("look")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.22, 0.23, 0.26, 1.0)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
scene.world = world
sun = bpy.data.objects.new("look_sun", bpy.data.lights.new("look_sun", 'SUN'))
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(52), 0.0, math.radians(28))
scene.collection.objects.link(sun)
camera = bpy.data.objects.new("look_camera", bpy.data.cameras.new("look_camera"))
camera.data.type = 'ORTHO'
scene.collection.objects.link(camera)
scene.camera = camera

KINDS = ["soldier", "king", "drummer", "guard", "baker"]
parents = {o.name: o for o in scene.objects if o.type == 'EMPTY' and o.parent is None}
rest = {}
for name, parent in parents.items():
    for child in parent.children:
        if child.type == 'MESH':
            rest[name] = [v.co.copy() for v in child.data.vertices]


def mesh_of(name):
    return next(c for c in parents[name].children if c.type == 'MESH')


def mark(name, which):
    return next(c for c in parents[name].children if c.name == "%s_%s" % (name, which)).location.copy()


def pose(name, kind, jaw, right, left, tash):
    """Turn the parts as the game does (build_nutcrackers.posed)."""
    obj = mesh_of(name)

    class Stand:        # what build.posed reads
        marks = {k: mark(name, k) for k in ("jaw", "jawtop", "armr", "arml", "tash")}

    turns = {
        "jaw": build.posed(Stand, build.JAW, jaw=jaw),
        "beard": build.posed(Stand, build.BEARD, jaw=jaw),
        "arm_r": build.posed(Stand, build.ARM_R, arm=right),
        "arm_l": build.posed(Stand, build.ARM_L, arm=left),
        "moustache": build.posed(Stand, build.TASH, tash=tash),
    }
    names = {g.index: g.name for g in obj.vertex_groups}
    for v, at in zip(obj.data.vertices, rest[name]):
        m = Matrix.Identity(4)
        for g in v.groups:
            if names[g.group] in turns:
                m = turns[names[g.group]]
        v.co = m @ at
    obj.data.update()


def show(names, gap):
    for name, parent in parents.items():
        shown = name in names
        if shown:
            parent.location = (names.index(name) * gap, 0.0, 0.0)
        for o in [parent] + list(parent.children):
            o.hide_render = not shown


def shoot(tag, names, gap, tall, pixels):
    show(names, gap)
    middle = (len(names) - 1) * gap * 0.5
    wide = len(names) * gap
    camera.data.ortho_scale = wide
    scene.render.resolution_x = pixels
    scene.render.resolution_y = int(pixels * tall / wide)
    tilt = math.radians(80)
    for view, turn in (("front", 0), ("right", 90), ("back", 180), ("left", 270)):
        for name in names:
            parents[name].rotation_euler = (0.0, 0.0, math.radians(-turn))
        camera.location = (middle, -3.0 * math.sin(tilt), tall * 0.5 + 3.0 * math.cos(tilt))
        camera.rotation_euler = (tilt, 0.0, 0.0)
        scene.render.filepath = os.path.join(out, "%s_%s.png" % (tag, view))
        bpy.ops.render.render(write_still=True)
    for name in names:
        parents[name].rotation_euler = (0.0, 0.0, 0.0)
    scene.render.resolution_y = int(pixels * 0.2 / wide)
    camera.location = (middle, 0.0, 3.0)
    camera.rotation_euler = (0.0, 0.0, 0.0)
    scene.render.filepath = os.path.join(out, "%s_top.png" % tag)
    bpy.ops.render.render(write_still=True)


shoot("full", KINDS, 0.2, 0.56, 1500)
shoot("low", [k + "_lo" for k in KINDS], 0.2, 0.56, 1500)
for kind in KINDS:
    r0, r1, l0, l1 = build.ARM_RANGE[kind]
    pose(kind, kind, build.JAW_MAX, build.SALUTE[kind], (l0 * 0.6, 0.0), 0.0)
shoot("pose_a", KINDS, 0.2, 0.56, 1500)
for kind in KINDS:
    r0, r1, l0, l1 = build.ARM_RANGE[kind]
    pose(kind, kind, build.JAW_MAX * 0.5, (r1, 0.0), (l1, 0.0), build.TASH_TILT)
shoot("pose_b", KINDS, 0.2, 0.56, 1500)
for kind in KINDS:
    pose(kind, kind, 0.0, (0.0, 0.0), (0.0, 0.0), 0.0)
nuts = ["walnut_whole", "walnut_half_a", "walnut_half_b", "walnut_whole_lo", "walnut_half_a_lo", "walnut_half_b_lo"]
show(nuts, 0.04)
camera.data.ortho_scale = 0.26
scene.render.resolution_x = 1600
scene.render.resolution_y = 300
camera.location = (0.1, -3.0 * math.sin(math.radians(65)), 0.013 + 3.0 * math.cos(math.radians(65)))
camera.rotation_euler = (math.radians(65), 0.0, 0.0)
for name in nuts:
    parents[name].rotation_euler = (0.0, 0.0, math.radians(-60))
scene.render.filepath = os.path.join(out, "walnuts.png")
bpy.ops.render.render(write_still=True)
print("LOOKED", out)
