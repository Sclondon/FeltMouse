# Builds the gingerbread house component's models, its manifest and its one picture.
#
#   blender -b --factory-startup --python gingerbread_house/tools/build_gingerbread.py [-- <folder for a preview of the sheet>]
#
# Writes, beside this folder:
#   tools/gingerbread.blend                every house and every piece, full and low, to open and edit
#   models/gingerbread.glb                 the same for Godot (no pictures inside: the script lays the material on)
#   models/gingerbread_houses.json         the manifest: for each house its footprint, doorway, windows, the
#                                          light inside, and every place a decoration may go (Godot's axes, metres)
#   textures/gingerbread_sheet.png         twenty squares of masks (see paint_gingerbread.py)
#
# Each house is an empty named after it (cottage, townhouse, chalet, church, shop, wonky; the low ones end
# in _lo) with these under it:
#   <name>_shell   the slabs, the piped icing along every join, the sugar-glass panes, the floor inside
#   <name>_board   the cake board it stands on
#   <name>_spill   the light from its doorway lying on the board (a fan a hair above it)
#   <name>_door    the door slab, its hinge edge on its own origin (the game hangs it from the manifest)
# Each piece (card, gumdrop, disc, cane, allsort, wafer, stick, icicle, roof_snow, blob, snowman, person, fir,
# village_board) is an empty with <name>_body under it. Faces are told apart by material name; the game gives
# each its square of the picture and its colours. Every point's colour is (tone, glow): how dark the bread is
# baked there, and how much of the light inside reaches it.
#
# Every mesh is checked: faces that share an edge must be wound alike, and every closed piece must face
# outwards (its signed volume). The build stops otherwise.
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MODELS = os.path.join(ROOT, "models")
TEXTURES = os.path.join(ROOT, "textures")
sys.path.insert(0, HERE)
import paint_gingerbread as paint  # noqa: E402
import gingerbread_gen as gen  # noqa: E402

# which square each material wears in the .blend, and in which sample colours (the game picks its own)
RED, GREEN, WHITE = (0.78, 0.08, 0.1), (0.14, 0.5, 0.2), (0.97, 0.95, 0.9)
WEARS = {
    "bread": ("bread", None), "inside": ("bread", ((0.6, 0.35, 0.17), (0.4, 0.2, 0.09), (0.93, 0.87, 0.76))),
    "icing": ("icing", None), "glass": ("glass", None), "floor": ("plain", ((0.86, 0.8, 0.68), WHITE, WHITE)),
    "awning": ("stripes", None), "biscuit": ("cookie", None), "snow_flat": ("snow", None), "foil": ("foil", None),
    "sugar": ("sugar", None), "disc": ("sweets", None), "disc_rim": ("plain", (RED, RED, RED)), "stripes": ("stripes", None),
    "allsort": ("parts", ((0.97, 0.95, 0.9), (0.1, 0.08, 0.08), (0.95, 0.5, 0.6))), "allsort_top": ("plain", (WHITE, WHITE, WHITE)),
    "wafer": ("wafer", None), "pretzel": ("bread", ((0.5, 0.27, 0.1), (0.34, 0.16, 0.06), (0.97, 0.95, 0.9))),
    "snow": ("snow", None), "blob": ("icing", None), "marsh": ("plain", ((0.97, 0.96, 0.94), WHITE, WHITE)),
    "face": ("parts", None), "buttons": ("parts", None), "person": ("cookie", None), "fir": ("tree", None),
    "card": ("motifs_a", None),
}
SHARP = 50.0
# round things of few sides are shaded round: the angle past which an edge of theirs is left sharp
SHARP_OF = {"cane": 100.0, "stick": 80.0, "gumdrop": 80.0, "icicle": 130.0, "blob": 80.0, "disc": 60.0, "snowman": 60.0, "fir": 60.0}


def check(part, name):
    """Every piece of a mesh must be wound one way, and a closed piece outwards. Returns (closed, open)."""
    place = {}
    weld = []
    for p in part.v:
        key = (round(p.x * 2e4), round(p.y * 2e4), round(p.z * 2e4))
        weld.append(place.setdefault(key, len(place)))
    edges = {}
    for fi, (idx, _uv, _mat) in enumerate(part.faces):
        w = [weld[i] for i in idx]
        for a, b in zip(w, w[1:] + w[:1]):
            edges.setdefault((min(a, b), max(a, b)), []).append((fi, a < b))
    seen = set()
    closed = opened = 0
    for start in range(len(part.faces)):
        if start in seen:
            continue
        seen.add(start)
        piece, stack, shut = [start], [start], True
        while stack:
            f = stack.pop()
            w = [weld[i] for i in part.faces[f][0]]
            for a, b in zip(w, w[1:] + w[:1]):
                users = edges[(min(a, b), max(a, b))]
                if len(users) != 2:
                    shut = False
                    if len(users) > 2:
                        continue
                if len(users) == 2 and users[0][1] == users[1][1]:
                    p = part.v[part.faces[f][0][0]]
                    raise SystemExit("INSIDE OUT: %s has two faces wound against each other near (%.4f, %.4f, %.4f), material %s"
                                     % (name, p.x, p.y, p.z, part.faces[f][2]))
                if len(users) == 2:
                    for (g, _d) in users:
                        if g not in seen:
                            seen.add(g)
                            piece.append(g)
                            stack.append(g)
        if shut:
            volume = 0.0
            for f in piece:
                vs = [part.v[i] for i in part.faces[f][0]]
                for i in range(1, len(vs) - 1):
                    volume += vs[0].dot(vs[i].cross(vs[i + 1])) / 6.0
            if volume <= 0.0:
                p = part.v[part.faces[piece[0]][0][0]]
                raise SystemExit("INSIDE OUT: %s has a closed piece facing inwards (volume %.3g) near (%.4f, %.4f, %.4f)"
                                 % (name, volume, p.x, p.y, p.z))
            closed += 1
        else:
            opened += 1
    return closed, opened


def make_object(name, part, mats, parent, sharp=SHARP):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(p) for p in part.v], [], [f[0] for f in part.faces])
    layer = mesh.uv_layers.new(name="UVMap")
    colour = mesh.color_attributes.new("Col", 'FLOAT_COLOR', 'POINT')
    layer = mesh.uv_layers["UVMap"]
    colour = mesh.color_attributes["Col"]
    loop = 0
    for (_idx, uvs, _mat) in part.faces:
        for uv in uvs:
            layer.data[loop].uv = uv
            loop += 1
    for i in range(len(part.v)):
        colour.data[i].color = (part.tone[i], part.glow[i], 0.0, 1.0)
    mesh.color_attributes.active_color = mesh.color_attributes["Col"]
    mesh.color_attributes.render_color_index = 0
    used = []
    for (_idx, _uvs, mat) in part.faces:
        if mat not in used:
            used.append(mat)
    for mat in used:
        mesh.materials.append(mats[mat])
    for poly, (_idx, _uvs, mat) in zip(mesh.polygons, part.faces):
        poly.material_index = used.index(mat)
        poly.use_smooth = True
    mesh.update()
    mesh.set_sharp_from_angle(angle=math.radians(sharp))
    if any(n is not None for n in part.n):
        # piped icing is drawn round though it is two flat strips: its points carry their own normals
        normals = []
        for corner in mesh.loops:
            n = part.n[corner.vertex_index]
            normals.append((n.x, n.y, n.z) if n is not None else (0.0, 0.0, 0.0))
        mesh.normals_split_custom_set(normals)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    return obj


def preview_material(name, picture, shiny, cut, glows):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    shader.inputs["Roughness"].default_value = 0.35 if shiny else 0.85
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = picture
    tone = nodes.new("ShaderNodeVertexColor")
    tone.layer_name = "Col"
    split = nodes.new("ShaderNodeSeparateColor")
    links.new(tone.outputs["Color"], split.inputs["Color"])
    mix = nodes.new("ShaderNodeMix")
    mix.data_type = 'RGBA'
    mix.blend_type = 'MULTIPLY'
    mix.inputs[0].default_value = 1.0
    links.new(tex.outputs["Color"], mix.inputs[6])
    links.new(split.outputs[0], mix.inputs[7])
    links.new(mix.outputs[2], shader.inputs["Base Color"])
    if cut:
        links.new(tex.outputs["Alpha"], shader.inputs["Alpha"])
    if glows:
        links.new(tex.outputs["Color"], shader.inputs["Emission Color"])
        shader.inputs["Emission Strength"].default_value = 1.2
    mat.use_backface_culling = True
    return mat


def save_png(path, rgba):
    h, w, _ = rgba.shape
    image = bpy.data.images.new(os.path.basename(path), w, h, alpha=True)
    image.alpha_mode = 'STRAIGHT'
    image.pixels.foreach_set(np.clip(rgba, 0.0, 1.0).astype(np.float32).ravel())
    image.filepath_raw = path
    image.file_format = 'PNG'
    image.save()
    bpy.data.images.remove(image)


def main():
    out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv and len(sys.argv) > sys.argv.index("--") + 1 else ""
    os.makedirs(MODELS, exist_ok=True)
    os.makedirs(TEXTURES, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    layers = paint.paint_all()
    save_png(os.path.join(TEXTURES, "gingerbread_sheet.png"), paint.sheet(layers))
    if out:
        os.makedirs(out, exist_ok=True)
        save_png(os.path.join(out, "sheet_preview.png"), paint.preview_sheet(layers))
    mats = {}
    for name, (square, colours) in WEARS.items():
        picture = paint.tinted(layers[square], *(colours or paint.PREVIEW[square]), cut=square in paint.DECALS)
        image = bpy.data.images.new("preview_" + name, paint.N, paint.N, alpha=True)
        image.pixels.foreach_set(picture.astype(np.float32).ravel())
        image.pack()
        mats[name] = preview_material(name, image, name in ("glass", "stripes", "disc", "sugar", "foil", "awning"), square in paint.DECALS,
                                      name == "glass")
    manifest = {"about": "Gingerbread houses: where things are on each, in Godot's axes (y up, a house's front to +z), metres. "
                         "Written by tools/build_gingerbread.py; read by gingerbread_house.gd.",
                "layers": paint.LAYERS, "tile": paint.TILE, "bands": paint.BANDS, "motifs_a": paint.MOTIFS_A, "motifs_b": paint.MOTIFS_B, "motifs_c": paint.MOTIFS_C, "sheet": [paint.COLS, paint.ROWS],
                "discs": paint.DISCS, "region": paint.REGION, "board_thick": gen.G, "slab_thick": gen.T, "houses": {}, "pieces": {}}
    report = []
    for n, kind in enumerate(gen.KINDS):
        counts = []
        for lo in (False, True):
            name = kind + ("_lo" if lo else "")
            made = gen.house(kind, lo)
            parent = bpy.data.objects.new(name, None)
            parent.empty_display_size = 0.02
            bpy.context.scene.collection.objects.link(parent)
            parent.location = (n * 0.42, 0.55 if lo else 0.0, 0.0)
            total = 0
            for piece_name, part in (("shell", made.shell), ("board", made.board), ("spill", made.spill), ("door", made.door)):
                if not part.faces:
                    continue
                closed, opened = check(part, "%s_%s" % (name, piece_name))
                obj = make_object("%s_%s" % (name, piece_name), part, mats, parent)
                total += part.triangles()
                print("  %-22s %5d triangles, %3d closed pieces outward, %3d open sheets" % (obj.name, part.triangles(), closed, opened))
                if piece_name == "door":
                    # stood ajar in the .blend, as the game hangs it
                    door = made.slots["doors"][0]
                    u = (made.m.to_3x3() @ door["u"][1]).normalized()
                    out_way = (made.m.to_3x3() @ door["n"][1]).normalized()
                    swing = Matrix.Rotation(math.radians(-38.0), 4, "Z")
                    basis = Matrix((u, -out_way, Vector((0.0, 0.0, 1.0)))).transposed().to_4x4()
                    obj.matrix_local = Matrix.Translation(made.m @ door["hinge"][1]) @ basis @ swing
            slots = gen.export_slots(made)
            counts.append(total)
            if not lo:
                manifest["houses"][kind] = slots
            else:
                manifest["houses"][kind]["triangles_lo"] = slots["triangles"]
        report.append((kind, counts))
    for n, title in enumerate(gen.PIECES):
        counts = []
        for lo in (False, True):
            name = title + ("_lo" if lo else "")
            part = gen.piece(title, lo)
            closed, opened = check(part, name)
            parent = bpy.data.objects.new(name, None)
            parent.empty_display_size = 0.01
            bpy.context.scene.collection.objects.link(parent)
            parent.location = (n * 0.09, -0.4 - (0.12 if lo else 0.0), 0.0)
            make_object(name + "_body", part, mats, parent, SHARP_OF.get(title, SHARP))
            counts.append(part.triangles())
            print("  %-22s %5d triangles, %3d closed pieces outward, %3d open sheets" % (name, part.triangles(), closed, opened))
        manifest["pieces"][title] = {"triangles": counts[0], "triangles_lo": counts[1]}
        report.append((title, counts))
    with open(os.path.join(MODELS, "gingerbread_houses.json"), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, indent=1)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "gingerbread.blend"))
    bpy.ops.export_scene.gltf(filepath=os.path.join(MODELS, "gingerbread.glb"), export_format='GLB', export_yup=True, export_apply=False,
                              export_image_format='NONE', export_animations=False, export_vertex_color='ACTIVE',
                              export_all_vertex_colors=False, export_normals=True)
    print("BUILT gingerbread (triangles full / low):")
    for title, counts in report:
        print("  %-14s %5d / %d" % (title, counts[0], counts[1]))


main()
