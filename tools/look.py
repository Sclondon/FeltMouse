# Renders tools/mouse.blend from front, back, both sides and above, to check it.
#   blender -b tools/mouse.blend --python tools/look.py -- <out dir>
import bpy, math, os, sys
from mathutils import Vector

out = sys.argv[sys.argv.index("--") + 1]
os.makedirs(out, exist_ok=True)
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "MATERIAL"
sc.display.shading.show_backface_culling = True
sc.display.shading.show_cavity = True
sc.view_settings.view_transform = "Standard"
sc.render.resolution_x = 520
sc.render.resolution_y = 640
cam_d = bpy.data.cameras.new("look")
cam_d.lens = 70
cam = bpy.data.objects.new("look", cam_d)
sc.collection.objects.link(cam)
sc.camera = cam
target = Vector((0, 0, 0.8))
VIEWS = {"front": (0, -1, 0.25), "left": (-1, 0, 0.25), "back": (0, 1, 0.25), "right": (1, 0, 0.25),
         "top": (0, -0.35, 1), "face": (0.35, -1, 0.5)}
for name, d in VIEWS.items():
    v = Vector(d).normalized()
    cam.location = target + v * 4.6
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(out, name + ".png")
    bpy.ops.render.render(write_still=True)
