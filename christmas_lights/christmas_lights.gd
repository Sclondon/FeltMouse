class_name ChristmasLights
extends Node3D
## A string of Christmas lights hung along any line: a twisted two-strand wire with bulbs on it at uneven,
## hand-hung gaps, each leaning its own way, glowing from inside, with a few real lights for the wall behind.
## (GameCommon godot/christmas-lights.)
##
##   var string := ChristmasLights.new()
##   string.kind = ChristmasLights.Kind.C9
##   string.size = 12.5                      # this game's units per metre (Felt Mouse: 1 unit = 8 cm)
##   add_child(string)
##   string.hang(points)                     # a line of points in this node's own space
##   # or: string.hang_between(a, b, 0.15)   # two ends and a sag
##   # or: string.hang(ChristmasLights.swags(hooks, 0.15))   # dipping from hook to hook
##
## The bulbs are models (models/christmas_lights.glb, built in Blender by tools/build_christmas_lights.py): C9,
## C7, mini, faceted, globe, star and icicle, each with a low twin. All bulbs of one kind in a string are two
## MultiMeshes (glass, sockets), the halos one more, the wire one mesh; three small shader programs in all.
## Settings that change where things are (kind, spacing, lean, size, palette, seed, wire...) take effect at the
## next hang() or rebuild(). Settings of the light (pattern, speed, brightness, core, halo...) take effect at once.

enum Kind { C9, C7, MINI, FACETED, GLOBE, STAR, ICICLE, MIX }
enum Palette { CLASSIC, WARM_WHITE, COOL_WHITE, RED_GREEN, ICE, CANDY, CUSTOM }
enum Order { RANDOM_NO_NEIGHBOURS, PATTERN, RANDOM }
enum Pattern { STEADY, TWINKLE, CHASE, FADE, OFF }

## Each kind's model name and its usual gap along the wire in real metres.
const KINDS := [
	{"name": "c9", "spacing": 0.30},
	{"name": "c7", "spacing": 0.25},
	{"name": "mini", "spacing": 0.10},
	{"name": "faceted", "spacing": 0.12},
	{"name": "globe", "spacing": 0.30},
	{"name": "star", "spacing": 0.15},
	{"name": "icicle", "spacing": 0.15},
]

const PALETTES := {
	Palette.CLASSIC: [Color(1.0, 0.10, 0.06), Color(1.0, 0.50, 0.04), Color(0.08, 0.85, 0.16), Color(0.10, 0.28, 1.0), Color(1.0, 0.22, 0.55)],
	Palette.WARM_WHITE: [Color(1.0, 0.70, 0.36)],
	Palette.COOL_WHITE: [Color(0.72, 0.86, 1.0)],
	Palette.RED_GREEN: [Color(1.0, 0.10, 0.06), Color(0.08, 0.85, 0.16)],
	Palette.ICE: [Color(0.10, 0.30, 1.0), Color(0.80, 0.90, 1.0), Color(0.15, 0.65, 1.0)],
	Palette.CANDY: [Color(1.0, 0.08, 0.08), Color(1.0, 0.88, 0.80)],
}

@export_group("Bulbs")
## Which bulb hangs on the string: C9 (the big outdoor classic, 8 cm), C7 (its slimmer little brother), MINI (the
## small pointed bulb in a push-in base), FACETED (a cut "strawberry" LED cap), GLOBE (a round G40 patio bulb),
## STAR and ICICLE (novelty caps), or MIX (a jumble of the kinds listed in `mix`). Each kind costs two draws.
@export var kind: Kind = Kind.C9
## The kinds jumbled together when `kind` is MIX, picked at random bulb by bulb.
@export var mix: Array[Kind] = [Kind.C9, Kind.C7, Kind.GLOBE]
## Use each bulb's low model (about 50 to 80 triangles in place of 140 to 380) and a single untwisted wire: for
## phones and for strings seen from far off. Close up the low bulbs are plainly angular.
@export var low_detail := false
## The game's units to a real metre: everything (bulbs, wire, gaps, the lights' reach) is made at real size and
## multiplied by this. 1 in a game measured in metres; 12.5 in Felt Mouse, where 1 unit is 8 cm. Make it larger
## for toy-like oversized lights.
@export_range(0.01, 100.0, 0.01, "or_greater") var size := 1.0
## How big the bulbs are against the rest of the string. 1 is true to life; 2 doubles every bulb without moving
## them apart or thickening the wire.
@export_range(0.1, 10.0, 0.01, "or_greater") var bulb_size := 1.0
## How much bulbs differ in size, as a share either way: 0 all alike, 0.08 (the default) a barely seen wobble,
## 0.5 some half as big again as others.
@export_range(0.0, 1.0, 0.01) var size_variation := 0.08
## The usual gap between bulbs along the wire, in real metres (multiplied by `size`). 0 (the default) uses the
## kind's own gap: 30 cm for C9 and globe, 25 for C7, 10 to 15 for the small kinds. 0.05 packs them tight.
@export_range(0.0, 2.0, 0.005, "or_greater") var spacing := 0.0
## How uneven the gaps are: 0 is machine-even, 0.4 (the default) looks hung by hand (some bulbs nearly
## neighbours, some far apart), 1 is very ragged.
@export_range(0.0, 1.5, 0.01) var unevenness := 0.4
## How far a bulb may tip from its hanging line, in degrees either way along the wire (and half as much across
## it): 0 all parallel, 30 (the default) loosely hung, 90 pointing any way along the wire.
@export_range(0.0, 180.0, 0.5) var lean := 30.0
## How much the bulbs hang down under the wire: 1 all straight below it, 0.7 (the default) mostly below with some
## swung out to the side, 0 pointing any way round the wire, up as often as down.
@export_range(0.0, 1.0, 0.01) var droop := 0.7
## If the string hangs against a wall, the direction pointing out of the wall (in this node's space): bulbs that
## would have pointed into the wall are turned to point out of it. Leave at zero for a string in the open.
@export var wall_normal := Vector3.ZERO

@export_group("Colours")
## The bulbs' colours: CLASSIC (red, orange, green, blue, pink), WARM_WHITE, COOL_WHITE, RED_GREEN, ICE (blues
## and white), CANDY (red and white), or CUSTOM (the list in `colours`).
@export var palette: Palette = Palette.CLASSIC
## The colours used when `palette` is CUSTOM, up to eight.
@export var colours: Array[Color] = [Color(1.0, 0.7, 0.36)]
## How colours are dealt along the string: RANDOM_NO_NEIGHBOURS (the default: at random, but never two alike
## side by side), PATTERN (in the palette's order, over and over), or RANDOM (pure chance, repeats allowed).
@export var order: Order = Order.RANDOM_NO_NEIGHBOURS
## How much bulbs of one colour differ, as real ones do: 0 identical, 0.12 (the default) slight differences in
## brightness and tint, 0.5 plainly mismatched.
@export_range(0.0, 1.0, 0.01) var colour_variation := 0.12

@export_group("Wire")
## The colour of the wire and of every plastic socket and base (they are moulded in the same plastic). Dark
## green is the classic; white and black are the other real ones.
@export var wire_colour := Color(0.04, 0.17, 0.07)
## The thickness of one strand of the wire in real metres (multiplied by `size`). 0.0035 is true to life; at
## 0.01 it is a chunky toy cord. 0 leaves the wire out.
@export_range(0.0, 0.05, 0.0005, "or_greater") var wire_thickness := 0.0035
## How many times the two strands wind round each other in a real metre: 0 lays them side by side, 14 (the
## default) is a normal twisted cord, 40 is tightly wound (and costs more triangles).
@export_range(0.0, 80.0, 0.5, "or_greater") var wire_twist := 14.0
## How far the wire strays from the line it was given, in real metres, so it does not hang like a ruled curve:
## 0 follows the line exactly, 0.008 (the default) a slight wobble, 0.05 a tangle.
@export_range(0.0, 0.2, 0.001, "or_greater") var wire_wander := 0.008
## Round the corners of the line given (a curve through the points). Off, the wire runs straight from point to
## point.
@export var smooth := true
## The same settings and seed always make the same string; another seed deals the gaps, leans, sizes and colours
## afresh.
@export var seed := 1

@export_group("Light")
## What the lights do over time: STEADY, TWINKLE (bulbs here and there sink and come back, slowly), CHASE (one
## bulb in every few is lit, running along the string), FADE (all melt from each colour of the palette into the
## next) or OFF (unlit coloured glass).
@export var pattern: Pattern = Pattern.STEADY:
	set(value):
		pattern = value
		_apply_shine()
## How fast the pattern runs: 1 is unhurried, 0.25 very slow, 4 lively. Has no effect on STEADY or OFF.
@export_range(0.0, 10.0, 0.01, "or_greater") var speed := 1.0:
	set(value):
		speed = value
		_apply_shine()
## How bright the bulbs are: 1 normal, 0 dark, 2 glaring (with the environment's glow on they bloom more). The
## real lights' strength follows it.
@export_range(0.0, 5.0, 0.01, "or_greater") var brightness := 1.0:
	set(value):
		brightness = value
		_apply_shine()
## How far a twinkling or chased bulb dims: 1 goes right out, 0.85 (the default) keeps an ember, 0.3 only wavers.
@export_range(0.0, 1.0, 0.01) var twinkle_depth := 0.85:
	set(value):
		twinkle_depth = value
		_apply_shine()
## CHASE: one bulb in this many is lit at a time. 2 alternates, 3 (the default) is the usual running light.
@export_range(2, 8) var chase_every := 3:
	set(value):
		chase_every = value
		_apply_shine()
## How hot the middle of each bulb looks: 0 is a painted bulb glowing evenly in its colour, 0.6 (the default)
## has a pale hot heart, 1 is clear glass with a white-hot filament.
@export_range(0.0, 2.0, 0.01) var core := 0.6:
	set(value):
		core = value
		_apply_shine()
## The soft haze round each bulb, as its radius in bulb radii: 0 none (and one draw fewer), 3.2 (the default) a
## close glow, 8 a wide bloom. It is what reads as "lit" on phones, which have no post-process glow.
@export_range(0.0, 12.0, 0.1, "or_greater") var halo := 3.2:
	set(value):
		halo = value
		_apply_shine()
## How strong that haze is: 0.45 by default, 0 invisible, 1.5 very bright.
@export_range(0.0, 3.0, 0.01, "or_greater") var halo_strength := 0.45:
	set(value):
		halo_strength = value
		_apply_shine()

@export_group("Real lights")
## How many real lights (OmniLight3D) are spread evenly along the string, each in the mixed colour of the bulbs
## near it, so walls and things nearby pick up coloured light. Keep it small: GL Compatibility lights an object
## with only so many lights (8 by default) and every one costs. 0 for none.
@export_range(0, 16) var lights := 2
## The strength of each real light, as it would be in a game measured in metres (multiplied by `brightness`, and
## by `size` so the wall is lit alike at any scale). 0.6 by default; 0.2 is a faint wash, 2 floods the wall.
@export_range(0.0, 8.0, 0.01, "or_greater") var light_energy := 0.6
## How far each real light reaches, in real metres (multiplied by `size`).
@export_range(0.05, 10.0, 0.01, "or_greater") var light_range := 1.2
## Where each real light sits from its place on the wire, in real metres (multiplied by `size`): by default a
## little below. Against a wall, add some of the wall's outward direction so the light is not buried in it.
@export var light_offset := Vector3(0.0, -0.04, 0.0)

## The line the string hangs along, in this node's own space. Set by hang(); if it is filled in before the node
## enters the tree, the string builds itself then.
@export var points := PackedVector3Array()

static var _models := {}
static var _shaders := {}
static var _atlas: Texture2D
static var _card: QuadMesh

var _made: Array[Node] = []
var _materials: Array[ShaderMaterial] = []
var _lamps: Array[OmniLight3D] = []
var _lamp_mix: Array = []       # for each real light, how much of each palette colour is near it
var _lamp_colour: Array[Color] = []
var _halos: MultiMeshInstance3D
var _count := 0
var _bulbs: Array = []
var _triangles := 0


func _ready() -> void:
	if points.size() >= 2 and _made.is_empty():
		rebuild()


## Hangs the string along `line` (a PackedVector3Array or an Array of Vector3, in this node's space).
func hang(line: Variant) -> ChristmasLights:
	points = PackedVector3Array(line)
	rebuild()
	return self


## Hangs the string from `from` to `to`, dipping by `sag` (a share of the distance between them).
func hang_between(from: Vector3, to: Vector3, sag := 0.15) -> ChristmasLights:
	return hang(swag(from, to, sag))


## A hanging curve from `from` to `to` that dips by `sag` times the distance between them, as `steps` + 1 points.
static func swag(from: Vector3, to: Vector3, sag := 0.15, steps := 12) -> PackedVector3Array:
	var line := PackedVector3Array()
	var drop := from.distance_to(to) * sag
	for i in steps + 1:
		var t := float(i) / steps
		line.append(from.lerp(to, t) + Vector3.DOWN * drop * 4.0 * t * (1.0 - t))
	return line


## One line dipping from each hook to the next (a string looped along a row of nails).
static func swags(hooks: Variant, sag := 0.15, steps := 12) -> PackedVector3Array:
	var pegs := PackedVector3Array(hooks)
	var line := PackedVector3Array()
	for i in pegs.size() - 1:
		var part := swag(pegs[i], pegs[i + 1], sag, steps)
		if i > 0:
			part.remove_at(0)
		line.append_array(part)
	return line


## How many bulbs the string has (after hang() or rebuild()).
func bulb_count() -> int:
	return _count


## Every bulb in order along the string, each a Dictionary: "frame" (its Transform3D in this node's space, origin
## on the wire, +Y along the bulb to its tip), "aim" (that direction), "big" (its scale), "kind" (a Kind), "s" (how
## far along the wire), "shade" (its place in the palette) and "colour" (linear). For a game that wants to add
## something at each bulb; changing it does not move anything.
func bulbs() -> Array:
	return _bulbs


## How many triangles the string draws: bulbs, wire and halo cards.
func triangle_count() -> int:
	return _triangles


## Every node the string made: the MultiMeshInstance3Ds, the wire, the real lights.
func parts() -> Array[Node]:
	return _made


## Forgets the loaded models, shaders and picture (they are read once and shared by every string).
static func clear_cache() -> void:
	_models.clear()
	_shaders.clear()
	_atlas = null
	_card = null


## Takes the string down.
func clear() -> void:
	for node in _made:
		if is_instance_valid(node):
			remove_child(node)
			node.queue_free()
	_made.clear()
	_materials.clear()
	_lamps.clear()
	_lamp_mix.clear()
	_lamp_colour.clear()
	_halos = null
	_bulbs = []
	_count = 0
	_triangles = 0
	set_process(false)


## Builds the string afresh from `points` and the settings.
func rebuild() -> void:
	clear()
	if points.size() < 2:
		return
	_load()
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(seed)
	var path := _path(rng)
	var run := _lengths(path)
	var total: float = run[run.size() - 1]
	if total <= 0.0:
		return

	# which kinds, and the gap
	var pool: Array[int] = []
	if kind == Kind.MIX:
		for k in mix:
			if k != Kind.MIX:
				pool.append(k)
		if pool.is_empty():
			pool.append(Kind.C9)
	else:
		pool.append(kind)
	var gap := spacing
	if gap <= 0.0:
		for k in pool:
			gap += float(KINDS[k]["spacing"]) / pool.size()
	gap *= size

	# the bulbs: where, which way, what colour
	var shades := _palette()
	var bulbs: Array = []
	var last_shade := -1
	var s := gap * rng.randf_range(0.25, 0.75)
	if s > total:
		s = total * 0.5
	while s < total - gap * 0.15:
		var at := _at(path, run, s)
		var place: Vector3 = at[0]
		var along: Vector3 = at[1]
		var down := Vector3.DOWN - along * Vector3.DOWN.dot(along)
		if down.length() < 0.05:
			down = along.cross(Vector3.RIGHT)
		down = down.normalized()
		var aim := down.rotated(along, rng.randf_range(-1.0, 1.0) * (1.0 - droop) * PI)
		aim = aim.rotated(along, deg_to_rad(lean) * 0.5 * rng.randf_range(-1.0, 1.0))
		var across := along.cross(aim).normalized()
		aim = aim.rotated(across, deg_to_rad(lean) * rng.randf_range(-1.0, 1.0))
		if wall_normal != Vector3.ZERO:
			var out := wall_normal.normalized()
			if aim.dot(out) < 0.0:
				aim -= out * 2.0 * aim.dot(out)
		var flat := along - aim * along.dot(aim)
		if flat.length() < 0.01:
			flat = aim.cross(Vector3.RIGHT)
		var x := flat.normalized().rotated(aim, rng.randf() * TAU)
		var big := size * bulb_size * maxf(0.05, 1.0 + size_variation * rng.randf_range(-1.0, 1.0))
		var shade := 0
		match order:
			Order.PATTERN:
				shade = bulbs.size() % shades.size()
			Order.RANDOM:
				shade = rng.randi_range(0, shades.size() - 1)
			_:
				shade = rng.randi_range(0, shades.size() - 1)
				if shades.size() > 1 and shade == last_shade:
					shade = (shade + 1 + rng.randi_range(0, shades.size() - 2)) % shades.size()
		last_shade = shade
		var colour: Color = shades[shade]
		var wobble := rng.randf_range(-1.0, 1.0) * colour_variation
		var tilt := rng.randf_range(-1.0, 1.0) * colour_variation
		colour = Color.from_hsv(fposmod(colour.h + tilt * 0.15, 1.0), colour.s, clampf(colour.v * (1.0 + wobble), 0.0, 1.0))
		bulbs.append({
			"kind": pool[rng.randi_range(0, pool.size() - 1)],
			"frame": Transform3D(Basis(x, aim, x.cross(aim)).scaled(Vector3.ONE * big), place),
			"aim": aim, "big": big, "s": s, "shade": shade,
			"colour": colour.srgb_to_linear(),
			"data": Color(rng.randf(), float(bulbs.size() % 840), float(shade), 0.0),
		})
		s += gap * maxf(0.25, 1.0 + unevenness * rng.randf_range(-0.75, 1.0))
	_count = bulbs.size()
	_bulbs = bulbs

	# the three materials (one program each, shared by every string)
	var glass_look := _material("bulb_glass")
	var socket_look := _material("bulb_socket")
	socket_look.set_shader_parameter("socket_atlas", _atlas)
	var halo_look := _material("bulb_halo")

	# the wire
	if wire_thickness > 0.0:
		var cord := MeshInstance3D.new()
		cord.name = "Wire"
		cord.mesh = _wire(path, run)
		cord.material_override = socket_look
		cord.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_keep(cord)
		_triangles += cord.mesh.surface_get_array_index_len(0) / 3

	# the bulbs, a pair of MultiMeshes for each kind in use
	for k in KINDS.size():
		var mine: Array = bulbs.filter(func(b: Dictionary) -> bool: return b["kind"] == k)
		if mine.is_empty():
			continue
		var model: Dictionary = _models[String(KINDS[k]["name"]) + ("_lo" if low_detail else "")]
		for part: String in ["glass", "socket"]:
			var many := MultiMesh.new()
			many.transform_format = MultiMesh.TRANSFORM_3D
			many.use_colors = true
			many.use_custom_data = true
			many.mesh = model[part]
			many.instance_count = mine.size()
			for i in mine.size():
				many.set_instance_transform(i, mine[i]["frame"])
				many.set_instance_color(i, mine[i]["colour"])
				many.set_instance_custom_data(i, mine[i]["data"])
			var node := MultiMeshInstance3D.new()
			node.name = "%s_%s" % [String(KINDS[k]["name"]).capitalize(), part]
			node.multimesh = many
			node.material_override = glass_look if part == "glass" else socket_look
			node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			_keep(node)
			_triangles += mine.size() * (model[part] as ArrayMesh).surface_get_array_index_len(0) / 3

	# the halos: one card a bulb, at the middle of its glass
	if halo > 0.0 and _count > 0:
		var haze := MultiMesh.new()
		haze.transform_format = MultiMesh.TRANSFORM_3D
		haze.use_colors = true
		haze.use_custom_data = true
		haze.mesh = _card
		haze.instance_count = _count
		var widest := 0.0
		for i in _count:
			var b: Dictionary = bulbs[i]
			var model: Dictionary = _models[String(KINDS[b["kind"]]["name"]) + ("_lo" if low_detail else "")]
			var radius: float = float(model["radius"]) * float(b["big"])
			widest = maxf(widest, radius)
			var middle: Vector3 = (b["frame"] as Transform3D).origin + (b["aim"] as Vector3) * float(model["centre"]) * float(b["big"])
			haze.set_instance_transform(i, Transform3D(Basis().scaled(Vector3.ONE * radius), middle))
			haze.set_instance_color(i, b["colour"])
			haze.set_instance_custom_data(i, b["data"])
		_halos = MultiMeshInstance3D.new()
		_halos.name = "Halos"
		_halos.multimesh = haze
		_halos.material_override = halo_look
		_halos.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_halos.extra_cull_margin = widest * maxf(halo, 12.0)
		_keep(_halos)
		_triangles += _count * 2

	# the real lights, each in the mixed colour of the bulbs along its share of the string
	for n in lights:
		var middle_s := total * (n + 0.5) / lights
		var blend := Color(0, 0, 0)
		var share: Array[float] = []
		share.resize(shades.size())
		share.fill(0.0)
		var found := 0
		for b: Dictionary in bulbs:
			if absf(float(b["s"]) - middle_s) <= total * 0.5 / lights:
				blend += b["colour"]
				share[b["shade"]] += 1.0
				found += 1
		if found == 0:
			continue
		for i in share.size():
			share[i] /= found
		var lamp := OmniLight3D.new()
		lamp.name = "Light%d" % n
		lamp.position = _at(path, run, middle_s)[0] + light_offset * size
		lamp.omni_range = light_range * size
		lamp.omni_attenuation = 1.0
		lamp.shadow_enabled = false
		_lamps.append(lamp)
		_lamp_mix.append(share)
		_lamp_colour.append(Color(blend.r / found, blend.g / found, blend.b / found).linear_to_srgb())
		_keep(lamp)
	_apply_shine()


func _process(_delta: float) -> void:
	# FADE only: the real lights follow the bulbs through the palette (the same sum as bulb_shine.gdshaderinc's
	# bulb_colour, on the engine's clock, which is close to the shader's TIME but not locked to it).
	var shades := _palette()
	var beat := Time.get_ticks_msec() / 1000.0 * speed * 0.35
	var step := int(floor(beat))
	var melt := smoothstep(0.6, 1.0, beat - floor(beat))
	for n in _lamps.size():
		var blend := Color(0, 0, 0)
		var share: Array = _lamp_mix[n]
		for i in share.size():
			var first: Color = shades[(i + step) % shades.size()]
			var next: Color = shades[(i + step + 1) % shades.size()]
			blend += first.lerp(next, melt) * float(share[i])
		_lamps[n].light_color = Color(blend.r, blend.g, blend.b)


func _keep(node: Node) -> void:
	add_child(node)
	_made.append(node)


func _material(which: String) -> ShaderMaterial:
	var look := ShaderMaterial.new()
	look.shader = _shaders[which]
	_materials.append(look)
	return look


## The palette in use, never empty and never more than eight (the fade's limit).
func _palette() -> Array[Color]:
	var shades: Array[Color] = []
	if palette == Palette.CUSTOM:
		shades.assign(colours)
	else:
		shades.assign(PALETTES[palette])
	if shades.is_empty():
		shades.append(Color(1.0, 0.7, 0.36))
	if shades.size() > 8:
		shades.resize(8)
	return shades


func _apply_shine() -> void:
	if _materials.is_empty():
		return
	var shades := _palette()
	var linear := PackedVector3Array()
	for i in 8:
		var c := shades[i % shades.size()].srgb_to_linear()
		linear.append(Vector3(c.r, c.g, c.b))
	for look in _materials:
		look.set_shader_parameter("shine_pattern", int(pattern))
		look.set_shader_parameter("shine_speed", speed)
		look.set_shader_parameter("shine_brightness", brightness)
		look.set_shader_parameter("shine_depth", twinkle_depth)
		look.set_shader_parameter("shine_every", chase_every)
		look.set_shader_parameter("shine_colours", shades.size())
		look.set_shader_parameter("shine_palette", linear)
		look.set_shader_parameter("glass_core", core)
		look.set_shader_parameter("plastic_colour", wire_colour)
		look.set_shader_parameter("halo_reach", halo)
		look.set_shader_parameter("halo_light", halo_strength)
	if _halos:
		_halos.visible = halo > 0.0 and pattern != Pattern.OFF
	# The real lights: steady at the mixed colour, a little lower for the patterns that dim bulbs, out when off.
	# (An OmniLight3D's light thins with distance in units, so the strength is scaled with the string to look the
	# same at any `size`.)
	var strength := light_energy * brightness * size
	if pattern == Pattern.TWINKLE:
		strength *= 1.0 - 0.2 * twinkle_depth
	elif pattern == Pattern.CHASE:
		strength *= 1.0 - twinkle_depth * (1.0 - 1.0 / chase_every) * 0.7
	for n in _lamps.size():
		_lamps[n].visible = pattern != Pattern.OFF and strength > 0.0
		_lamps[n].light_energy = strength
		_lamps[n].light_color = _lamp_colour[n]
	set_process(pattern == Pattern.FADE and not _lamps.is_empty() and shades.size() > 1)


# ---------------------------------------------------------------------------------------------- the line

## The line the wire follows: the points given, rounded if `smooth`, cut into short even steps, then nudged
## off the ruled curve by `wire_wander`.
func _path(rng: RandomNumberGenerator) -> PackedVector3Array:
	var rough := 0.0
	for i in points.size() - 1:
		rough += points[i].distance_to(points[i + 1])
	var step := 0.03
	if not low_detail and wire_twist > 0.0:
		step = clampf(1.0 / (wire_twist * 5.0), 0.004, 0.03)
	step = maxf(step * size, rough / 3000.0)
	var path := PackedVector3Array()
	var last := points.size() - 1
	for i in last:
		var a := points[i]
		var b := points[i + 1]
		var cuts := maxi(1, int(ceil(a.distance_to(b) / step)))
		for c in cuts:
			var t := float(c) / cuts
			if smooth and points.size() > 2:
				path.append(a.cubic_interpolate(b, points[maxi(i - 1, 0)], points[mini(i + 2, last)], t))
			else:
				path.append(a.lerp(b, t))
	path.append(points[last])
	if wire_wander > 0.0:
		var run := _lengths(path)
		var total: float = run[run.size() - 1]
		var reach := wire_wander * size
		var phase := [rng.randf() * TAU, rng.randf() * TAU, rng.randf() * TAU, rng.randf() * TAU]
		var slow := TAU / (0.37 * size)
		var quick := TAU / (0.13 * size)
		var moved := PackedVector3Array()
		for i in path.size():
			var along := (path[mini(i + 1, path.size() - 1)] - path[maxi(i - 1, 0)]).normalized()
			var side := along.cross(Vector3.UP)
			if side.length() < 0.05:
				side = along.cross(Vector3.RIGHT)
			side = side.normalized()
			var lift := side.cross(along)
			var d: float = run[i]
			var pinned := smoothstep(0.0, 1.0, minf(d, total - d) / minf(0.25 * size, total * 0.3))   # the ends stay put
			moved.append(path[i] + pinned * reach * (
					side * (0.65 * sin(d * slow + phase[0]) + 0.35 * sin(d * quick + phase[1]))
					+ lift * (0.65 * sin(d * slow * 1.3 + phase[2]) + 0.35 * sin(d * quick * 0.8 + phase[3]))))
		path = moved
	return path


static func _lengths(path: PackedVector3Array) -> PackedFloat32Array:
	var run := PackedFloat32Array()
	run.resize(path.size())
	var d := 0.0
	for i in path.size():
		if i > 0:
			d += path[i].distance_to(path[i - 1])
		run[i] = d
	return run


## The place and direction of the line at distance `s` along it.
static func _at(path: PackedVector3Array, run: PackedFloat32Array, s: float) -> Array:
	var i := clampi(run.bsearch(s) - 1, 0, path.size() - 2)
	var span := run[i + 1] - run[i]
	var t := clampf((s - run[i]) / span, 0.0, 1.0) if span > 0.0 else 0.0
	var before := path[maxi(i - 1, 0)]
	var after := path[mini(i + 2, path.size() - 1)]
	var along := (path[i + 1] - path[i]).normalized().lerp((after - before).normalized(), 0.5).normalized()
	return [path[i].lerp(path[i + 1], t), along]


## The wire: two thin strands twisted round each other along the line (one plain strand when `low_detail`).
func _wire(path: PackedVector3Array, run: PackedFloat32Array) -> ArrayMesh:
	var strands := 1 if low_detail else 2
	var sides := 3
	var radius := wire_thickness * size * (0.7 if low_detail else 0.5)
	var apart := 0.0 if low_detail else radius * 0.9
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var uvs := PackedVector2Array()
	var indices := PackedInt32Array()
	var count := path.size()
	# a frame carried along the line without spinning
	var across := PackedVector3Array()
	var tangents := PackedVector3Array()
	var n := Vector3.ZERO
	for i in count:
		var along := (path[mini(i + 1, count - 1)] - path[maxi(i - 1, 0)]).normalized()
		if i == 0:
			n = along.cross(Vector3.UP)
			if n.length() < 0.05:
				n = along.cross(Vector3.RIGHT)
		n = (n - along * n.dot(along)).normalized()
		across.append(n)
		tangents.append(along)
	for strand in strands:
		var first := verts.size()
		for i in count:
			var along := tangents[i]
			var a := across[i]
			var b := along.cross(a)
			var turn := (TAU * wire_twist * run[i] / size if strands == 2 else 0.0) + PI * strand
			var heart := path[i] + (a * cos(turn) + b * sin(turn)) * apart
			for k in sides:
				var round_it := TAU * k / sides
				var out := a * cos(round_it) + b * sin(round_it)
				verts.append(heart + out * radius)
				normals.append(out)
				uvs.append(Vector2(run[i] / size * 12.0, 0.375))   # the atlas's smooth plastic band
		for i in count - 1:
			for k in sides:
				var k1 := (k + 1) % sides
				var p := first + i * sides + k
				var q := first + i * sides + k1
				var r := first + (i + 1) * sides + k1
				var t := first + (i + 1) * sides + k
				indices.append_array([p, r, q, p, t, r])   # clockwise seen from outside (Godot's front)
		# the cut ends
		for end in 2:
			var ring := first + (count - 1) * sides * end
			var mid := verts.size()
			var facing := tangents[(count - 1) * end] * (1.0 if end == 1 else -1.0)
			var middle := Vector3.ZERO
			for k in sides:
				middle += verts[ring + k] / sides
			verts.append(middle)
			normals.append(facing)
			uvs.append(Vector2(0.0, 0.375))
			for k in sides:
				var k1 := (k + 1) % sides
				if end == 1:
					indices.append_array([mid, ring + k1, ring + k])
				else:
					indices.append_array([mid, ring + k, ring + k1])
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_TEX_UV] = uvs
	arrays[Mesh.ARRAY_INDEX] = indices
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return mesh


# ---------------------------------------------------------------------------------------------- loading

## Reads the bulb models, the shaders and the sockets' picture once, from the folder this script is in.
func _load() -> void:
	if not _models.is_empty():
		return
	var home := (get_script() as Script).resource_path.get_base_dir()
	for which: String in ["bulb_glass", "bulb_socket", "bulb_halo"]:
		_shaders[which] = load("%s/shaders/%s.gdshader" % [home, which])
	# The picture with mipmaps, whatever the import settings were, so far ribs do not sparkle.
	_atlas = load(home + "/textures/socket_atlas.png")
	var picture := _atlas.get_image()
	if picture and not picture.has_mipmaps():
		if picture.is_compressed():
			picture.decompress()
		picture.generate_mipmaps()
		_atlas = ImageTexture.create_from_image(picture)
	_card = QuadMesh.new()
	_card.size = Vector2(2.0, 2.0)
	var scene := load(home + "/models/christmas_lights.glb") as PackedScene
	var root := scene.instantiate()
	for found in root.find_children("*", "MeshInstance3D", true, false):
		var holder := found as MeshInstance3D
		var entry := {}
		for surface in holder.mesh.get_surface_count():
			var look := holder.mesh.surface_get_material(surface)
			var what := String(look.resource_name) if look else ""
			if what != "glass" and what != "socket":
				continue
			# only what the shaders read, and none of the importer's thinned far versions
			var got := holder.mesh.surface_get_arrays(surface)
			var arrays := []
			arrays.resize(Mesh.ARRAY_MAX)
			for channel: int in [Mesh.ARRAY_VERTEX, Mesh.ARRAY_NORMAL, Mesh.ARRAY_TEX_UV, Mesh.ARRAY_TEX_UV2, Mesh.ARRAY_INDEX]:
				arrays[channel] = got[channel]
			var mesh := ArrayMesh.new()
			mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
			entry[what] = mesh
		if entry.has("glass") and entry.has("socket"):
			var box := (entry["glass"] as ArrayMesh).get_aabb()
			entry["centre"] = box.get_center().y
			entry["radius"] = (box.size.y * 0.5 + maxf(box.size.x, box.size.z) * 0.5) * 0.5
			_models[String(holder.name).trim_prefix("bulb_")] = entry
	root.free()
