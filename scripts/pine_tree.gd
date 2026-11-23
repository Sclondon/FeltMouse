@tool
class_name PineTree
extends Resource
## A pine (fir, spruce, lodgepole...) built from code, as a mesh: a tapering trunk with a flare at
## its foot, whorls of drooping branch fronds that shorten towards a spire, each frond fat in the
## middle and turned up a little at its tip, drawn as crossed cards of needles (see NEEDLES), darker
## within and lighter at the tips, and snow on the upper faces if asked. Every setting below can be
## changed; the same settings and seed always make the same tree.
##
## One tree:   var made := PineTree.new(); made.height = 12.0; add_child(made.instance())
## A forest:   PineTree.forest(parent, points, made, 6)   (a MultiMesh per variant: a few draws)
##
## The mesh carries vertex colours (sRGB) and normals bent outward from the trunk, so the whole
## crown shades as one soft shape. It is drawn with `material` if set, or else the needle shader.

## Overall height, metres, and the trunk's radius at its foot.
@export var height := 10.0
@export var trunk_radius := 0.22
## How far up the trunk the lowest branches start (0..1 of the height).
@export_range(0.0, 0.8) var crown_base := 0.14
## Whorls (rings of branches) and branches in each.
@export_range(3, 30) var whorls := 12
@export_range(3, 14) var branches := 9
## How wide the crown is, against its height (0.3 slim spire, 0.6 broad fir).
@export_range(0.15, 1.0) var spread := 0.42
## How much the branches hang (0 straight out, 1 hanging down like a spruce's).
@export_range(0.0, 1.0) var droop := 0.45
## How the branch length falls off up the tree: 1 a straight cone, more a rounder shoulder.
@export_range(0.4, 2.5) var taper := 1.05
## How thick a frond is, against its length.
@export_range(0.1, 0.8) var fullness := 0.5
## More cards crossed about each frond (two at 0, three at 1 or 2...): more body, more triangles.
@export_range(0, 4) var sprigs := 2
## Unevenness: branch lengths and angles, and the lean of the whole tree.
@export_range(0.0, 1.0) var wildness := 0.35
@export_range(0.0, 0.3) var lean := 0.04
## Colours.
@export var bark := Color(0.36, 0.25, 0.18)
@export var needles_inner := Color(0.10, 0.22, 0.16)
@export var needles_outer := Color(0.24, 0.42, 0.26)
@export var tips := Color(0.40, 0.56, 0.32)
## Snow on the upper faces, 0..1.
@export_range(0.0, 1.0) var snow := 0.0
@export var snow_colour := Color(0.94, 0.96, 1.0)
@export var seed := 1
## --- Added 2026-11-22 for the Christmas tree component; each leaves an existing tree exactly as it was at its default. ---
## How big the needles are drawn against the tree: the needle shader counts in metres (a needle 7 cm, branchlets
## 13 cm apart, right for a 10 m pine), so a 2 m room tree wants about 0.4 and a 45 cm tabletop one about 0.25.
## 1 (the default) as before; smaller, finer needles and more of them; larger, coarser.
@export_range(0.05, 4.0, 0.01, "or_greater") var needle_scale := 1.0
## How much the branches rise from the trunk towards their tips, as a fir's do (more so up the tree): 0 (the
## default) straight out before they droop, 0.4 swept up like a Christmas tree, 1 steeply up.
@export_range(0.0, 1.5) var lift := 0.0
## How big the dark mass of needles inside the crown is: 1 (the default) as before, 0 none at all (a sparse tree
## whose trunk and branches show), more for a tree clipped solid.
@export_range(0.0, 1.6) var inner := 1.0
## Wood showing down the middle of every frond: the radius of a solid branch at the trunk, metres, thinning to its
## tip. 0 (the default) none, only the twig drawn on the needle cards.
@export_range(0.0, 0.1, 0.001, "or_greater") var branch_wood := 0.0
## Bends the top of the tree over towards +x, as a sapling bows under a weight: the tip ends this share of the
## height to the side (and a little lower). 0 (the default) straight.
@export_range(-0.8, 0.8) var bend := 0.0
## What to draw it with. Empty: the needle shader (see NEEDLES), which takes the vertex colours.
@export var material: Material

static var _cache := {}


## Forgets every built mesh (a tool that rebuilds a tree at each change would otherwise keep them all).
static func clear_cache() -> void:
	_cache.clear()
	_frond_lists.clear()


## The settings as a key (for sharing built meshes).
func _key(variant: int) -> String:
	return "%s|%d" % [var_to_str([_steps, height, trunk_radius, crown_base, whorls, branches, spread, droop, taper, fullness, sprigs, wildness, lean,
		bark, needles_inner, needles_outer, tips, snow, snow_colour, seed,
		needle_scale, lift, inner, branch_wood, bend]).hash(), variant]


## The tree's mesh, built once for each variant and kept.
func mesh(variant := 0) -> ArrayMesh:
	var key := _key(variant)
	if _cache.has(key):
		return _cache[key]
	var built := _build(seed * 7919 + variant * 104729)
	_cache[key] = built
	return built


## A MeshInstance3D of it.
func instance(variant := 0) -> MeshInstance3D:
	var made := MeshInstance3D.new()
	made.mesh = mesh(variant)
	made.material_override = _material()
	return made


## Plants trees at `points` (Vector3s on the ground), `variants` different ones turned and sized at
## random, under `parent`. They are drawn as MultiMeshes, one per variant in each square of `chunk`
## metres (so trees off screen are not drawn); beyond `near` metres each square changes over to a
## plain version of the same tree (see `simple`) with no shadow. `sizes` scales them (min, max).
## `near` 0 keeps the full tree at every distance.
static func forest(parent: Node3D, points: Array, shape: PineTree, variants := 4, sizes := Vector2(0.8, 1.25), chunk := 64.0, near := 70.0) -> Array[MultiMeshInstance3D]:
	var rng := RandomNumberGenerator.new()
	rng.seed = shape.seed
	var plain := shape.simple() if near > 0.0 else null
	var groups := {}
	for p: Vector3 in points:
		var size := rng.randf_range(sizes.x, sizes.y)
		var cell := Vector2i(floori(p.x / chunk), floori(p.z / chunk))
		var key := [cell, rng.randi() % variants]
		if not groups.has(key):
			groups[key] = []
		groups[key].append(Transform3D(Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3.ONE * size), p))
	var made: Array[MultiMeshInstance3D] = []
	for key: Array in groups:
		var trees: Array = groups[key]
		for detailed: bool in ([true, false] if plain else [true]):
			var multi := MultiMesh.new()
			multi.transform_format = MultiMesh.TRANSFORM_3D
			multi.mesh = shape.mesh(key[1]) if detailed else plain.mesh(key[1])
			multi.instance_count = trees.size()
			for i in trees.size():
				multi.set_instance_transform(i, trees[i])
			var node := MultiMeshInstance3D.new()
			node.multimesh = multi
			node.material_override = shape._material()
			if plain:
				node.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
				if detailed:
					node.visibility_range_end = near
					node.visibility_range_end_margin = 10.0
				else:
					node.visibility_range_begin = near
					node.visibility_range_begin_margin = 10.0
					node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			parent.add_child(node)
			made.append(node)
	return made


## A plainer version of this tree, for far off: the same height, shape and colours, with fewer and
## fuller whorls, fewer branches, and fewer cards to a frond (about a sixth of the triangles).
func simple() -> PineTree:
	var plain: PineTree = duplicate()
	plain.whorls = maxi(int(whorls / 2.5), 4)
	plain.branches = mini(branches, 6)
	plain.sprigs = 0
	plain.fullness = minf(fullness * 1.4, 0.8)
	plain._steps = 2
	return plain


## Segments along each frond (fewer for a plain tree).
var _steps := 4


## What the tree is drawn with, unless `material` is set: the vertex colours, and on the fronds'
## cards, needles. A frond's card has a twig down its middle; off the twig both ways, slanted
## towards the tip, run short branchlets, and off each branchlet both ways run needles, slanted
## out, short and thin, lighter at their tips; all of it cut out of the card (alpha scissor), so
## what is not needle is not drawn. Far off, where a needle would be smaller than a pixel, the
## branchlets are drawn filled in instead, and further still the frond's whole outline, so that it
## neither shimmers nor thins away. The cards sway a little in the wind, more towards their tips.
## The trunk and the mass inside the crown are drawn plain, one-sided.
##
## A card's vertices carry: UV, metres along the frond and across it (-1..1 of its widest half);
## UV2, 1 for a card (0 for the solid parts) and the frond's length; and the colour's alpha, half
## that widest half-width in metres.
const NEEDLES := """
shader_type spatial;
render_mode cull_disabled, specular_disabled;

// Metres between branchlets along a frond, between needles along a branchlet, and how long a
// needle is at its longest.
const float BRANCH = 0.13;
const float SPACING = 0.017;
const float NEEDLE = 0.07;

uniform float sway : hint_range(0.0, 0.3) = 0.04;
// A push on every frond, more towards its tip and a little different for each (metres at the tip of a frond a
// metre long): for a game to bob the boughs when the tree is bumped. Zero (the default) does nothing.
uniform vec3 bob = vec3(0.0);

varying float card;
varying float half_width;

vec3 to_linear(vec3 c) {
	return mix(pow((c + vec3(0.055)) / 1.055, vec3(2.4)), c / 12.92, lessThan(c, vec3(0.04045)));
}

// How far the needles reach out from the twig, 0..1 of the widest, `s` of the way along the
// frond: narrow at its foot, widest nearly half way, to a point at its tip.
float outline(float s) {
	return max(sin(PI * (0.1 + 0.9 * clamp(s, 0.0, 1.0))), 0.0);
}

float hash(float n) {
	return fract(sin(n * 12.9898) * 43758.5453);
}

void vertex() {
	card = UV2.x;
	half_width = COLOR.a * 2.0;
	COLOR.rgb = to_linear(COLOR.rgb);
	if (card > 0.5) {
		vec3 here = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
		float s = UV.x / max(UV2.y, 0.01);
		float bend = s * s * UV2.y * sway;
		float t = TIME * 1.1 + dot(here.xz, vec2(0.13, 0.11)) + here.y * 0.05;
		VERTEX += vec3(sin(t) * 0.6, sin(t * 1.7 + 0.8), cos(t * 0.8) * 0.6) * bend;
		VERTEX += bob * (s * s * UV2.y * (0.7 + 0.6 * hash(floor(UV2.y * 977.0))));
	}
}

void fragment() {
	vec3 colour = COLOR.rgb;
	if (card > 0.5) {
		float x = UV.x;
		float s = x / max(UV2.y, 0.01);
		float hw = max(half_width, 0.05);
		// (metres out from the twig, and which side of it)
		float out_m = abs(UV.y) * hw;
		float side = UV.y < 0.0 ? 1.0 : 0.0;
		float edge = outline(s) * hw;

		// The branchlet this is by: they leave the twig slanted towards the tip, the two sides
		// staggered. (`across` is metres from its stem; `into` how far out along it, 0..1.)
		float u = x - out_m * 0.85 + side * BRANCH * 0.5;
		float index = floor(u / BRANCH) + side * 101.0;
		float r = hash(index);
		float across = (fract(u / BRANCH) - 0.5) * BRANCH / 1.31;
		float reach = edge * mix(0.75, 1.05, r);
		float into = clamp(out_m / max(reach, 0.01), 0.0, 1.0);
		float a = abs(across);

		// Its needles: off its stem both ways, slanted outwards, shorter towards its end.
		float length_here = NEEDLE * (1.0 - 0.5 * into) * mix(0.8, 1.15, r) * step(out_m, reach);
		float q = (out_m * 1.31 - a * 0.9) / SPACING + r * 7.0;
		float nf = abs(fract(q) - 0.5);
		float thin = 0.24 * (1.0 - 0.75 * a / max(length_here, 0.001));
		float px = fwidth(x / SPACING);
		float needle = (1.0 - smoothstep(thin - px, thin + px, nf)) * step(a, length_here);
		float stem = (1.0 - smoothstep(0.004, 0.004 + fwidth(across), a)) * step(out_m, reach);
		float twig = (1.0 - smoothstep(0.012, 0.012 + fwidth(out_m), out_m)) * step(s, 0.97);
		float near_cover = max(max(needle, stem), twig);

		// Far off: the branchlets filled in, then the whole frond.
		float fine = clamp(px * 1.6 - 0.6, 0.0, 1.0);
		float coarse = clamp(fwidth(x / BRANCH) * 1.6 - 0.5, 0.0, 1.0);
		float tuft = step(a, length_here * 0.85) + twig;
		float cover = mix(mix(near_cover, tuft, fine), step(out_m, edge * 0.9), coarse);
		ALPHA = clamp(cover, 0.0, 1.0);
		ALPHA_SCISSOR_THRESHOLD = 0.5;

		// Darker in at the stems and the twig, lighter out at the needles' tips; each needle a
		// shade of its own; the twig and stems brown.
		float tip = clamp(a / max(length_here, 0.001), 0.0, 1.0);
		colour *= mix(mix(0.72, 1.2, tip), 0.95, fine) * mix(0.8, 1.0, into);
		colour *= 0.88 + 0.24 * hash(index * 3.1 + floor(q)) * (1.0 - fine);
		colour = mix(colour, vec3(0.06, 0.045, 0.03), max(stem, twig) * (1.0 - fine) * 0.8);
		// (a card is lit the same from both sides: its normal is bent out from the trunk)
		if (!FRONT_FACING) {
			NORMAL = -NORMAL;
		}
	} else if (!FRONT_FACING) {
		discard;
	}
	ALBEDO = colour;
	ROUGHNESS = 1.0;
}
"""

static var _needles: ShaderMaterial


func _material() -> Material:
	if material:
		return material
	return _shared_needles()


static func _shared_needles() -> ShaderMaterial:
	if _needles == null:
		var shader := Shader.new()
		shader.code = NEEDLES
		_needles = ShaderMaterial.new()
		_needles.shader = shader
	return _needles


## A material of the needle shader with settings of its own (`sway`, `bob`), for a tree that should not share
## them with every other pine: set it as a tree's `material`. It is the same shader, so no new program is compiled.
static func needle_material() -> ShaderMaterial:
	var own := ShaderMaterial.new()
	own.shader = _shared_needles().shader
	return own


## Every frond of the tree as built (variant as for `mesh`), for hanging things on it or winding things round it:
## for each {"base": where it leaves the trunk, "tip", "line": its points from base to tip, "length", "out": the
## level direction it grows in, "up_tree": 0 at the lowest whorl .. 1 at the top, "half": how far its needles reach
## to each side at its widest, "leader": true for the one upright frond at the very top}. In the mesh's own space.
func fronds(variant := 0) -> Array[Dictionary]:
	var key := _key(variant)
	if not _frond_lists.has(key):
		_log = []
		_logging = true
		_cache[key] = _build(seed * 7919 + variant * 104729)
		_logging = false
		_frond_lists[key] = _log
		_log = []
	return _frond_lists[key]


static var _frond_lists := {}
var _logging := false
var _log: Array[Dictionary] = []


## A point of the straight tree put where it is in the leaning, bent one.
func _place(tilt: Basis, p: Vector3, top: float) -> Vector3:
	if bend != 0.0:
		var share := clampf(p.y / top, 0.0, 1.3)
		p.x += bend * top * share * share * share
		p.y -= absf(bend) * top * 0.45 * share * share * share * share
	return tilt * p


func _build(variant_seed: int) -> ArrayMesh:
	var rng := RandomNumberGenerator.new()
	rng.seed = variant_seed
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var tilt := Basis(Vector3(rng.randf_range(-1, 1), 0, rng.randf_range(-1, 1)).normalized(), rng.randf_range(0.0, lean)) if lean > 0.0 else Basis.IDENTITY
	var top := height * rng.randf_range(0.94, 1.06)
	_trunk(st, top, tilt)
	var crown := top * (1.0 - crown_base)
	var first := top * crown_base
	var turn := rng.randf() * TAU
	_fill(st, tilt, first + crown / whorls * 0.4, top, rng)
	for w in whorls:
		var t := (w + 0.5) / whorls
		var y := first + crown * pow(t, 0.92)
		# (shorter towards the top, by `taper`; a little uneven)
		var reach := spread * top * 0.5 * pow(1.0 - t, taper) + top * 0.035
		turn += 2.39996  # (the golden angle, so no branch sits right over the one below)
		var count := maxi(branches - int(t * 2.5), 3)
		for b in count:
			var angle := turn + b * TAU / count + rng.randf_range(-0.35, 0.35) * wildness
			var length := reach * rng.randf_range(1.0 - 0.35 * wildness, 1.0 + 0.2 * wildness)
			var hang := droop * rng.randf_range(0.8, 1.2) * lerpf(1.0, 0.55, t)
			var base := Vector3(0, y + rng.randf_range(-0.3, 0.3) * crown / whorls, 0)
			_frond(st, tilt, base, angle, length, hang, t, top)
	# The leader at the very top.
	_frond(st, tilt, Vector3(0, top * 0.97, 0), 0.0, top * 0.09, -1.0, 1.0, top)
	return st.commit()


## The dark mass of needles inside the crown, round the trunk: a ragged cone, so the tree reads as
## solid between its fronds, as a real one does from any way off.
func _fill(st: SurfaceTool, tilt: Basis, first: float, top: float, rng: RandomNumberGenerator) -> void:
	var sides := 11
	var rings := maxi(whorls, 4)
	var base_r := spread * top * 0.5 * 0.62 * inner
	var radii: Array = []
	for r in rings + 1:
		var t := float(r) / rings
		var row: Array[float] = []
		for s in sides:
			# (ragged: in and out between the fronds, more so lower down)
			row.append(base_r * pow(1.0 - t, taper) * rng.randf_range(0.78, 1.12) + top * 0.012)
		radii.append(row)
	if inner <= 0.0:
		return
	for r in rings:
		var t0 := float(r) / rings
		var t1 := float(r + 1) / rings
		var y0 := first + (top * 0.985 - first) * t0
		var y1 := first + (top * 0.985 - first) * t1
		for s in sides:
			var u0 := s * TAU / sides
			var u1 := (s + 1) * TAU / sides
			var a := _place(tilt, Vector3(cos(u0) * radii[r][s], y0, sin(u0) * radii[r][s]), top)
			var b := _place(tilt, Vector3(cos(u1) * radii[r][(s + 1) % sides], y0, sin(u1) * radii[r][(s + 1) % sides]), top)
			var c := _place(tilt, Vector3(cos(u0) * radii[r + 1][s], y1, sin(u0) * radii[r + 1][s]), top)
			var d := _place(tilt, Vector3(cos(u1) * radii[r + 1][(s + 1) % sides], y1, sin(u1) * radii[r + 1][(s + 1) % sides]), top)
			var n0 := tilt * Vector3(cos(u0), 0.55, sin(u0)).normalized()
			var n1 := tilt * Vector3(cos(u1), 0.55, sin(u1)).normalized()
			var inner := needles_inner.lerp(needles_outer, 0.25)
			var snowy0 := inner.lerp(snow_colour, snow * 0.5) if snow > 0.0 else inner
			_tri(st, [a, b, c], [n0, n1, n0], [inner, inner, snowy0])
			_tri(st, [b, d, c], [n1, n1, n0], [inner, snowy0, snowy0])
	# (and its underside, so it does not show hollow from below)
	var y := first
	for s in sides:
		var u0 := s * TAU / sides
		var u1 := (s + 1) * TAU / sides
		var a := _place(tilt, Vector3(cos(u0) * radii[0][s], y, sin(u0) * radii[0][s]), top)
		var b := _place(tilt, Vector3(cos(u1) * radii[0][(s + 1) % sides], y, sin(u1) * radii[0][(s + 1) % sides]), top)
		var dark := needles_inner.darkened(0.2)
		_tri(st, [a, _place(tilt, Vector3(0, y + 0.3, 0), top), b], [Vector3.DOWN, Vector3.DOWN, Vector3.DOWN], [dark, dark, dark])


func _trunk(st: SurfaceTool, top: float, tilt: Basis) -> void:
	var sides := 7
	var rings := 4 if bend == 0.0 else 12  # (a bent trunk needs the rings to curve with)
	for r in rings:
		var a := float(r) / rings
		var b := float(r + 1) / rings
		var ya := top * a
		var yb := top * b
		# (a flare at the foot, tapering to a point)
		var ra := trunk_radius * (1.0 - a * 0.92) * (1.0 + 0.6 * pow(1.0 - a, 6.0))
		var rb := trunk_radius * (1.0 - b * 0.92) * (1.0 + 0.6 * pow(1.0 - b, 6.0))
		for s in sides:
			var u0 := s * TAU / sides
			var u1 := (s + 1) * TAU / sides
			var p00 := _place(tilt, Vector3(cos(u0) * ra, ya, sin(u0) * ra), top)
			var p01 := _place(tilt, Vector3(cos(u1) * ra, ya, sin(u1) * ra), top)
			var p10 := _place(tilt, Vector3(cos(u0) * rb, yb, sin(u0) * rb), top)
			var p11 := _place(tilt, Vector3(cos(u1) * rb, yb, sin(u1) * rb), top)
			var n0 := tilt * Vector3(cos(u0), 0.2, sin(u0)).normalized()
			var n1 := tilt * Vector3(cos(u1), 0.2, sin(u1)).normalized()
			var shade := bark.darkened(0.15 * float(s % 2))
			# (wound clockwise seen from outside, which Godot takes for the front)
			_tri(st, [p00, p01, p10], [n0, n1, n0], [shade, shade, shade])
			_tri(st, [p01, p11, p10], [n1, n1, n0], [shade, shade, shade])


## One frond: out from the trunk along `angle`, `length` long, hanging by `hang` (or, for the
## leader, with `hang` below 0, straight up): needle cards along its line, crossed about it so it
## has body from any side.
func _frond(st: SurfaceTool, tilt: Basis, base: Vector3, angle: float, length: float, hang: float, up_tree: float, top: float) -> void:
	var out := Vector3(cos(angle), 0, sin(angle))
	var points: Array[Vector3] = []
	var steps := _steps
	for k in steps + 1:
		var s := float(k) / steps
		var p := base + out * length * s
		if hang >= 0.0:
			# (droops through its middle and lifts a little at the tip)
			p.y -= hang * length * (0.55 * s * s - 0.12 * pow(s, 4.0) * 3.0) + 0.02 * length
		else:
			p = base + Vector3.UP * length * s
		if lift != 0.0 and hang >= 0.0:
			p.y += lift * length * s * (0.5 + up_tree)
		points.append(_place(tilt, p, top))
	var axis_up := tilt * (Vector3.UP if hang >= 0.0 else out)
	var half := length * fullness * 0.62
	var cards := 2 + maxi(sprigs - 1, 0)
	for c in cards:
		_card(st, points, half * (1.0 if c == 0 else 0.65), c * PI / cards, axis_up, up_tree, top)
	if branch_wood > 0.0:
		_wood(st, points, branch_wood * lerpf(1.0, 0.5, up_tree))
	if _logging:
		_log.append({"base": points[0], "tip": points[steps], "line": points.duplicate(), "length": length, "out": tilt * out,
			"up_tree": up_tree, "half": half, "leader": hang < 0.0})


## The wood of a frond: a thin three-sided branch along its line, thinning to the tip.
func _wood(st: SurfaceTool, line: Array[Vector3], radius: float) -> void:
	var count := line.size()
	var dark := bark.darkened(0.25)
	for k in count - 1:
		var ahead := (line[k + 1] - line[k]).normalized()
		var any := Vector3.UP if absf(ahead.y) < 0.9 else Vector3.RIGHT
		var x := ahead.cross(any).normalized()
		var y := x.cross(ahead)
		var r0 := radius * lerpf(1.0, 0.2, float(k) / (count - 1))
		var r1 := radius * lerpf(1.0, 0.2, float(k + 1) / (count - 1))
		for s in 3:
			var n0 := x * cos(s * TAU / 3.0) + y * sin(s * TAU / 3.0)
			var n1 := x * cos((s + 1) * TAU / 3.0) + y * sin((s + 1) * TAU / 3.0)
			var a := line[k] + n0 * r0
			var b := line[k] + n1 * r0
			var c := line[k + 1] + n0 * r1
			var d := line[k + 1] + n1 * r1
			# (wound from each face's own outward side: clockwise as seen is Godot's front)
			var face := (n0 + n1).normalized()
			if (c - a).cross(b - a).dot(face) >= 0.0:
				_tri(st, [a, b, c], [n0, n1, n0], [dark, dark, bark])
				_tri(st, [b, d, c], [n1, n1, n0], [dark, bark, bark])
			else:
				_tri(st, [a, c, b], [n0, n0, n1], [dark, bark, dark])
				_tri(st, [b, c, d], [n1, n0, n1], [dark, bark, bark])


## A garland, bough or wreath of this pine: the same needle fronds, sprouting all along `line` (any curve, as
## points; close it for a wreath), each about `frond` long, `per_metre` of them to a metre of the line. They
## lie along the line both ways and stand out from it all round, more so with `bushy` (0 sleek .. 1 shaggy),
## and hang a little by `droop`. The needle shader counts in metres (a needle is 7 cm), so in a small-scale
## game make `frond` about 0.4 to 0.8 of its units for a sprig that reads as pine. Same settings and `seed`,
## same garland. Colours, `fullness` and `sprigs` are the tree's.
func garland(line: Array[Vector3], frond := 0.6, per_metre := 14.0, bushy := 0.6) -> ArrayMesh:
	var rng := RandomNumberGenerator.new()
	rng.seed = seed * 7919 + line.size()
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var along: Array[float] = [0.0]
	for k in range(1, line.size()):
		along.append(along[k - 1] + line[k].distance_to(line[k - 1]))
	var total: float = along[line.size() - 1]
	var count := maxi(int(total * per_metre), 1)
	for i in count:
		# (spread evenly with a jitter, so no bare stretch and no row of soldiers)
		var d := clampf((i + rng.randf()) / count, 0.0, 1.0) * total
		var k := 0
		while k < line.size() - 2 and along[k + 1] < d:
			k += 1
		var span := maxf(along[k + 1] - along[k], 0.0001)
		var root := line[k].lerp(line[k + 1], (d - along[k]) / span)
		var ahead := (line[k + 1] - line[k]).normalized()
		var any := Vector3.UP if absf(ahead.y) < 0.9 else Vector3.RIGHT
		var out := ahead.cross(any).normalized().rotated(ahead, rng.randf() * TAU)
		var way := (ahead * (1.0 if rng.randf() < 0.5 else -1.0) * rng.randf_range(0.35, 1.0) + out * rng.randf_range(0.25, 0.4 + bushy)).normalized()
		var length := frond * rng.randf_range(0.65, 1.25)
		var points: Array[Vector3] = []
		for step in _steps + 1:
			var s := float(step) / _steps
			points.append(root + way * length * s + Vector3.DOWN * (droop * 0.3 * length * s * s))
		var up := Vector3.UP if absf(way.y) < 0.9 else Vector3.RIGHT
		var half := length * fullness * 0.62
		var cards := 2 + maxi(sprigs - 1, 0)
		var roll := rng.randf() * PI
		for c in cards:
			_card(st, points, half * (1.0 if c == 0 else 0.65), roll + c * PI / cards, up, rng.randf(), 1.0, root)
	return st.commit()


## The garland as a node, drawn with the tree's material (the needle shader unless `material` is set).
func garland_instance(line: Array[Vector3], frond := 0.6, per_metre := 14.0, bushy := 0.6) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = garland(line, frond, per_metre, bushy)
	mi.material_override = _material()
	return mi


## How far the needles reach out from a frond's twig, `s` of the way along it (the shader's
## `outline`, which the card must cover).
static func _outline(s: float) -> float:
	return maxf(sin(PI * (0.1 + 0.9 * clampf(s, 0.0, 1.0))), 0.0)


## One needle card along a frond's `line`: a ribbon out to `half` metres each side of it at its
## widest, turned `roll` about the line from lying flat. (See NEEDLES for what it carries.)
## (`heart`, if given, is the point the card's normals bend out from, in place of the tree's trunk: a garland's rope.)
func _card(st: SurfaceTool, line: Array[Vector3], half: float, roll: float, up: Vector3, up_tree: float, top: float, heart: Variant = null) -> void:
	var count := line.size()
	var along: Array[float] = [0.0]
	for k in range(1, count):
		along.append(along[k - 1] + line[k].distance_to(line[k - 1]))
	var total: float = along[count - 1]
	var edges: Array = []
	for k in count:
		var s := float(k) / (count - 1)
		var ahead := (line[mini(k + 1, count - 1)] - line[maxi(k - 1, 0)]).normalized()
		var across := ahead.cross(up).normalized()
		var above := across.cross(ahead).normalized()
		var side := across * cos(roll) + above * sin(roll)
		# (as wide as the needles reach there, and a little more: straight edges between the
		# points cut inside the curve, the more so the fewer the points)
		var wide := minf(_outline(s) + 0.6 / (count - 1), 1.0)
		var p: Vector3 = line[k]
		# Bent outward from the trunk, so the crown shades as one shape.
		var round_ := Vector3(p.x, (p.y - top * 0.45) * 0.45 + top * 0.08, p.z).normalized()
		var normal := (round_ + Vector3.UP * 0.2).normalized()
		if heart is Vector3:
			var away: Vector3 = p - (heart as Vector3)
			normal = (away.normalized() + Vector3.UP * 0.25).normalized() if away.length() > 0.001 else Vector3.UP
		var colour := needles_inner.lerp(needles_outer, smoothstep(0.0, 0.7, s)).lerp(tips, smoothstep(0.65, 1.0, s) * 0.8)
		colour = colour.lightened(up_tree * 0.06)
		if snow > 0.0 and roll == 0.0:
			colour = colour.lerp(snow_colour, snow * 0.6 * smoothstep(0.2, 0.7, normal.y))
		colour.a = clampf(half * 0.5 / needle_scale, 0.0, 1.0)
		# (the shader counts needles in metres along the card: a smaller `needle_scale` tells it a longer card)
		edges.append([p - side * half * wide, p + side * half * wide, Vector2(along[k] / needle_scale, -wide), Vector2(along[k] / needle_scale, wide), normal, colour])
	for k in count - 1:
		var e0: Array = edges[k]
		var e1: Array = edges[k + 1]
		for corner: Array in [[e0, 0], [e1, 0], [e0, 1], [e0, 1], [e1, 0], [e1, 1]]:
			var e: Array = corner[0]
			var i: int = corner[1]
			st.set_color(e[5])
			st.set_normal(e[4])
			st.set_uv(e[2 + i])
			st.set_uv2(Vector2(1.0, total / needle_scale))
			st.add_vertex(e[i])


func _tri(st: SurfaceTool, points: Array, normals: Array, colours: Array) -> void:
	for i in 3:
		st.set_color(colours[i])
		st.set_normal(normals[i])
		st.set_uv(Vector2.ZERO)
		st.set_uv2(Vector2.ZERO)
		st.add_vertex(points[i])
