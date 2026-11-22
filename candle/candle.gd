class_name Candle
extends Node3D
## A candle: one of seven Blender models (wax with a melted well, runs of wax and a charred wick; some in
## a holder), a small steady flame that flickers, leans and now and then gutters, the wax glowing warm
## under it, and a light that breathes with the flame. This node is at the candle's foot, on the table.
##
##     var candle := Candle.new()
##     candle.kind = Candle.Kind.TAPER
##     candle.wax = Candle.Wax.RED
##     candle.size = 12.5            # the models are in metres: 12.5 for a game whose unit is 8 cm
##     add_child(candle)
##     candle.snuff()                # a thread of smoke; candle.relight() lights it again
##
## A candle is two to four draws (wax; holder; glass; flame) and, if `light` is on, one OmniLight3D.
## All flames share one shader program and all wax one picture; candles of one colour share a material.

enum Kind {
	PILLAR,      ## fat and short, standing by itself
	TAPER,       ## tall and thin, in a brass chamberstick with a drip pan and a finger loop
	TEALIGHT,    ## a tea light in its tin cup
	VOTIVE,      ## a short candle in a glass jar
	STUB,        ## a half-burnt stub leaning in a puddle of wax on a saucer
	HOLLY,       ## a pillar with a ring of holly leaves and berries round its foot
	THREE_WICK,  ## a wide candle with three wicks and three flames
}

enum Wax { CREAM, RED, GREEN, WHITE, CUSTOM }

const NAMES: Array[String] = ["pillar", "taper", "tealight", "votive", "stub", "holly", "three_wick"]
## How tall each kind's flame is, in metres, before `flame_size`.
const FLAME_TALL: Array[float] = [0.03, 0.03, 0.02, 0.024, 0.028, 0.03, 0.026]
const WAX_COLOURS: Array[Color] = [Color(0.96, 0.89, 0.74), Color(0.7, 0.09, 0.08), Color(0.15, 0.36, 0.17),
		Color(0.97, 0.97, 0.94)]
const MODELS := preload("models/candles.glb")
const WAX_PICTURE := preload("textures/candle_wax.png")
const GLOW_PICTURE := preload("textures/candle_glow.png")
const PARTS_PICTURE := preload("textures/candle_parts.png")
const FLAME_SHADER := preload("candle_flame.gdshader")

## Which candle it is (see Kind): a pillar by default.
@export var kind := Kind.PILLAR: set = _set_kind
## The colour of the wax: cream (the default), red, green, white, or CUSTOM to use `wax_colour`.
@export var wax := Wax.CREAM: set = _set_wax
## The wax colour when `wax` is CUSTOM. The wax picture's mottling is multiplied by it, so pale colours
## show the most texture and very dark ones go flat.
@export var wax_colour := Color(0.85, 0.6, 0.75): set = _set_wax_colour
## How far it has burnt down: 0 a new candle at full height with short beads of wax under the rim, 1 nearly
## gone, a low stump with a deep well, a slumped rim and long runs of wax down to its foot. Default 0.2.
@export_range(0.0, 1.0) var burnt := 0.2: set = _set_burnt
## How big it is. The models are made in metres (the pillar is 7.5 cm across and 10 cm tall), so 1 suits
## a game counted in metres and 12.5 a game whose unit is 8 cm. The flame grows with it; the light's
## reach does too unless `light_range` is set. Default 1.
@export_range(0.01, 100.0, 0.01, "or_greater") var size := 1.0: set = _set_size
## Draw the low model (about 100 to 180 triangles in place of 320 to 600: fewer sides, one or two runs
## of wax). For candles that are small on screen, or many at once on a phone. Default off.
@export var low_detail := false: set = _set_low_detail
## Burning or out. Turning it off in a running game snuffs it (the flame shrinks away, then smoke if
## `smoke` is on); turning it on lights it again over about half a second. Default on.
@export var lit := true: set = _set_lit
## A number that sets this candle's own rhythm, so a row of them do not flicker in step. 0 (the
## default) gives every candle a different one; any other number always gives the same rhythm.
@export var seed := 0: set = _set_seed

@export_group("Flame")
## The flame's height as a multiple of what suits the candle (about 3 cm on a pillar). 0.5 is a low
## bead of flame, 2 a tall one that looks like an oil lamp's. Default 1.
@export_range(0.0, 6.0, 0.01, "or_greater") var flame_size := 1.0: set = _set_flame_size
## How bright the flame is painted. 1 is plain; over 1 its heart goes white and, where the game has
## glow (bloom) on, blooms; under 1 it is a dull orange. Default 1.25.
@export_range(0.0, 6.0, 0.01, "or_greater") var flame_brightness := 1.25: set = _set_flame_brightness
## The soft warm glow drawn round the flame, which is what makes it read as a light on phones with no
## bloom. 0 is a bare flame with a hard edge, 1 a wide strong haze. Default 0.4.
@export_range(0.0, 3.0, 0.01, "or_greater") var halo := 0.4: set = _set_halo
## How much the flame's height and the light waver. 0 is dead still, 1 a candle in a quiet room, 3 one
## in a draughty hall. Default 1.
@export_range(0.0, 6.0, 0.01, "or_greater") var flicker := 1.0
## How often the flame gutters (dips and stutters for under a second). 0 never, 1 about every seven
## seconds, 4 nearly all the time. A draught makes it more often. Default 1.
@export_range(0.0, 10.0, 0.01, "or_greater") var gutter := 1.0
## A draught on the flame, in metres a second in the world's directions (the size setting is taken out,
## so the same number does the same to a candle of any size). 0.3 leans it, 1 lays it well over and
## stretches it, more than 2 flattens it. The light leans with it. Default none.
@export var wind := Vector3.ZERO
## How much carrying the candle about leans the flame back (it trails behind the way a real one does).
## 0 it ignores being moved, 1 as a real flame, 3 it streams out at a walk. Default 1.
@export_range(0.0, 6.0, 0.01, "or_greater") var motion_lean := 1.0
## How strongly the wax under the flame glows (light coming through it: brightest in the well and at the
## rim, fading down the side). 0 none, 1 as a real candle in the dark, 3 a lantern. Default 1.
@export_range(0.0, 6.0, 0.01, "or_greater") var wax_glow := 1.0: set = _set_wax_glow
## A thread of smoke rises from the wick for about two and a half seconds when it is snuffed. Default on.
@export var smoke := true

@export_group("Light")
## Give the candle a real light (an OmniLight3D at the flame). Turn it off on candles that stand by
## another: GL Compatibility lights each object with only so many lights (8 by default), and phones
## pay for every one. The flame, its halo and the wax still glow without it. Default on.
@export var light := true: set = _set_light
## The light's colour. Default a warm candle orange.
@export var light_colour := Color(1.0, 0.76, 0.5): set = _set_light_colour
## How strong the light is: how brightly it lights something 30 cm from the flame (times `size`), so
## the same number looks the same at any size. 0.1 a faint glow on the table, 0.4 a candle lighting what
## stands round it, 1 a bright lamp, 4 glaring. Nearer the flame it is brighter. Three wicks give half
## as much again. Default 0.4.
@export_range(0.0, 16.0, 0.01, "or_greater") var light_energy := 0.4
## How far the light reaches, in the game's own units. 0 (the default) means 2.5 metres times `size`.
@export_range(0.0, 200.0, 0.01, "or_greater") var light_range := 0.0: set = _set_light_range
## How much the light's strength follows the flame's flicker and guttering. 0 a steady light, 0.35
## breathing gently, 1 strongly, 2 nearly going out in a gutter. Default 0.35.
@export_range(0.0, 4.0, 0.01, "or_greater") var light_flicker := 0.35
## How far the light itself wanders as the flame wavers, so the shadows it throws breathe: a multiple
## of the flame's height. 0 still shadows, 0.15 a slight tremble, 1 shadows that swing. Default 0.15.
@export_range(0.0, 3.0, 0.01, "or_greater") var light_wobble := 0.15
## The light throws shadows. Each shadowed light draws the things round it again, so on phones keep
## it to one or two candles. Default off.
@export var light_shadows := false: set = _set_light_shadows

static var _library: Dictionary = {}
static var _baked: Dictionary = {}
static var _materials: Dictionary = {}
static var _card: QuadMesh

var _body: Node3D
var _wax_mesh: MeshInstance3D
var _flames: Array[MeshInstance3D] = []
var _lamp: OmniLight3D
var _lamp_at := Vector3.ZERO
var _queued := false
var _amount := 1.0          # how lit: 0 out .. 1 burning
var _smoke_age := -1.0      # 0 just snuffed .. 1 gone; under 0: no smoke
var _glowing := false
var _time := 0.0
var _phase := 0.0
var _lean := Vector3.ZERO
var _lean_speed := Vector3.ZERO
var _last := Vector3.ZERO
var _have_last := false
var _gutter_in := 3.0
var _gutter_left := 0.0
var _gutter_long := 0.5
var _rng := RandomNumberGenerator.new()


## A candle ready to add: Candle.make(Candle.Kind.TAPER, Candle.Wax.RED, 12.5).
static func make(of_kind: Kind, of_wax := Wax.CREAM, of_size := 1.0) -> Candle:
	var candle := Candle.new()
	candle.kind = of_kind
	candle.wax = of_wax
	candle.size = of_size
	return candle


## Put it out (the same as `lit = false`).
func snuff() -> void:
	lit = false


## Light it again (the same as `lit = true`).
func relight() -> void:
	lit = true


## Where the flame is in the world (the first, on a three-wick candle): for a spark, a sound, a moth.
func flame_position() -> Vector3:
	if _flames.is_empty():
		return global_position
	return _flames[0].global_position


## How many triangles this candle's models have (not counting the flame's card).
func triangles() -> int:
	var total := 0
	if _body != null:
		for child in _body.get_children():
			var part := child as MeshInstance3D
			if part != null and part.mesh != null and not _flames.has(part):
				for s in part.mesh.get_surface_count():
					total += part.mesh.surface_get_array_index_len(s) / 3
	return total


func _ready() -> void:
	_amount = 1.0 if lit else 0.0
	_build()


func _process(delta: float) -> void:
	delta = minf(delta, 0.05)
	_time += delta
	var target := 1.0 if lit else 0.0
	if _amount != target:
		_amount = move_toward(_amount, target, delta / (0.55 if lit else 0.14))
	if (_amount > 0.5) != _glowing:
		_glowing = _amount > 0.5
		_lay_wax()
	if _smoke_age >= 0.0 and _amount <= 0.0:
		_smoke_age += delta / 2.6
		if _smoke_age >= 1.0:
			_smoke_age = -1.0
	var here := global_position
	var unit := maxf(size * global_basis.get_scale().y, 0.0001)
	var carried := (here - _last) / maxf(delta, 0.0001) / unit if _have_last else Vector3.ZERO
	_last = here
	_have_last = true
	var showing := _amount > 0.0 or _smoke_age >= 0.0
	for flame in _flames:
		flame.visible = showing
	if _lamp != null:
		_lamp.visible = _amount > 0.0
	if not showing:
		_lean = Vector3.ZERO
		_lean_speed = Vector3.ZERO
		return
	# The flame trails behind a candle that is carried, and leans with a draught: a soft spring, so it
	# swings a little past and settles.
	var air := wind - carried * motion_lean
	var want := Vector3(air.x, 0.0, air.z) * 1.1
	want = want.limit_length(1.7)
	_lean_speed += ((want - _lean) * 60.0 - _lean_speed * 9.0) * delta
	_lean += _lean_speed * delta
	var over := Vector2(_lean.x, _lean.z).length()
	# Its height: three slow sines that never line up, and now and then a gutter.
	var f := 1.0 + flicker * (0.05 * sin(_time * 6.3 + _phase) + 0.035 * sin(_time * 10.7 + _phase * 1.7)
			+ 0.02 * sin(_time * 17.3 + _phase * 2.3))
	if _gutter_left > 0.0:
		_gutter_left -= delta
		var swell := sin(PI * clampf(1.0 - _gutter_left / _gutter_long, 0.0, 1.0))
		f *= 1.0 - minf(flicker, 2.0) * 0.36 * swell * (0.62 + 0.38 * sin(_time * 38.0 + _phase))
	elif gutter > 0.0:
		_gutter_in -= delta * gutter * (1.0 + 2.0 * air.length())
		if _gutter_in <= 0.0:
			_gutter_long = _rng.randf_range(0.35, 0.9)
			_gutter_left = _gutter_long
			_gutter_in = _rng.randf_range(3.5, 10.5)
	f = maxf(f, 0.2)
	var stretch := 0.22 * minf(over, 1.0) - 0.3 * maxf(over - 1.0, 0.0)
	for i in _flames.size():
		var flame := _flames[i]
		flame.set_instance_shader_parameter(&"flame_lean", Vector3(_lean.x, stretch, _lean.z))
		flame.set_instance_shader_parameter(&"flame_now",
				Vector4(_amount, f, fmod(_phase * 0.159 + i * 0.37, 1.0), _smoke_age if _amount <= 0.0 else -1.0))
	if _lamp != null and _amount > 0.0:
		var tall := FLAME_TALL[kind] * flame_size * size
		# Godot divides an omni light by the distance (in world units), so the strength is set for 30 cm
		var strength := light_energy * 0.3 * unit * (1.5 if _flames.size() > 1 else 1.0)
		_lamp.light_energy = maxf(strength * _amount * (1.0 + light_flicker * (f - 1.0) * 3.0), 0.0)
		var wander := Vector3(sin(_time * 5.3 + _phase * 6.0), 0.6 * sin(_time * 7.9 + _phase), sin(_time * 6.7 + _phase * 3.0))
		_lamp.position = _lamp_at + (Vector3(_lean.x, 0.0, _lean.z) * 0.35 + wander * light_wobble * (0.4 + (f - 1.0) * 2.0)) * tall


# ------------------------------------------------------------------ building it
func _build() -> void:
	_queued = false
	if not is_inside_tree():
		return
	if _body != null:
		_body.queue_free()
		remove_child(_body)
	if _lamp != null:
		_lamp.queue_free()
		remove_child(_lamp)
		_lamp = null
	_flames.clear()
	_rng.seed = seed if seed != 0 else int(get_instance_id()) * 7919 + 13
	_phase = _rng.randf_range(0.0, TAU * 8.0)
	_gutter_in = _rng.randf_range(1.5, 9.0)
	var models := _models()
	var entry: Dictionary = models[NAMES[kind] + ("_lo" if low_detail else "")]
	_body = Node3D.new()
	_body.name = "Body"
	_body.scale = Vector3.ONE * size
	add_child(_body)
	_wax_mesh = MeshInstance3D.new()
	_wax_mesh.name = "Wax"
	_wax_mesh.mesh = _burnt_mesh(NAMES[kind] + ("_lo" if low_detail else ""), entry["wax"])
	_body.add_child(_wax_mesh)
	_glowing = _amount > 0.5
	_lay_wax()
	if entry.has("parts"):
		var parts := MeshInstance3D.new()
		parts.name = "Parts"
		parts.mesh = entry["parts"]
		parts.material_override = _parts_material()
		_body.add_child(parts)
	if entry.has("glass"):
		var glass := MeshInstance3D.new()
		glass.name = "Glass"
		glass.mesh = entry["glass"]
		glass.material_override = _glass_material()
		glass.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_body.add_child(glass)
	var middle := Vector3.ZERO
	var wicks: Array = entry["wicks"]
	for pair: Array in wicks:
		var at: Vector3 = (pair[0] as Vector3).lerp(pair[1], burnt)
		var flame := MeshInstance3D.new()
		flame.name = "Flame"
		flame.mesh = _flame_card()
		flame.material_override = _flame_material()
		flame.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		flame.position = at
		flame.scale = Vector3.ONE * maxf(FLAME_TALL[kind] * flame_size, 0.0001)
		flame.set_instance_shader_parameter(&"flame_now", Vector4(_amount, 1.0, 0.0, -1.0))
		flame.visible = _amount > 0.0
		_body.add_child(flame)
		_flames.append(flame)
		middle += at / wicks.size()
	if light:
		_lamp = OmniLight3D.new()
		_lamp.name = "Light"
		_lamp_at = (middle + Vector3(0.0, FLAME_TALL[kind] * flame_size * 0.6 + 0.02, 0.0)) * size
		_lamp.position = _lamp_at
		_lamp.omni_attenuation = 1.0
		_lamp.light_energy = 0.0
		_lamp.visible = _amount > 0.0
		add_child(_lamp)
		_light_look()


func _light_look() -> void:
	if _lamp == null:
		return
	_lamp.light_color = light_colour
	_lamp.omni_range = light_range if light_range > 0.0 else 2.5 * size
	_lamp.shadow_enabled = light_shadows
	# the bias is a length in the world: Godot's default (0.1) is wider than a candle a metre scale
	_lamp.shadow_bias = 0.012 * size * global_basis.get_scale().y
	_lamp.shadow_normal_bias = 0.6


func _lay_wax() -> void:
	if _wax_mesh == null:
		return
	var colour := wax_colour if wax == Wax.CUSTOM else WAX_COLOURS[wax]
	_wax_mesh.material_override = _wax_material(colour, wax_glow if _glowing else 0.0)


func _rebuild() -> void:
	if is_inside_tree() and not _queued:
		_queued = true
		_build.call_deferred()


# ------------------------------------------------------------------ what candles share
## Every model in the .glb by name: {"wax": Mesh, "parts": Mesh, "glass": Mesh, "wicks": [[new, burnt], ...]}.
static func _models() -> Dictionary:
	if not _library.is_empty():
		return _library
	var scene: Node = (MODELS as PackedScene).instantiate()
	for top in scene.get_children():
		var title := String(top.name)
		var entry := {"wicks": []}
		var marks := {}
		for child in top.get_children():
			var what := String(child.name).trim_prefix(title + "_")
			if child is MeshInstance3D:
				entry[what] = (child as MeshInstance3D).mesh
			elif child is Node3D:
				marks[what] = (child as Node3D).position
		var n := 0
		while marks.has("wick%d_new" % n):
			(entry["wicks"] as Array).append([marks["wick%d_new" % n], marks["wick%d_burnt" % n]])
			n += 1
		_library[title] = entry
	scene.free()
	return _library


## The wax at this candle's `burnt` (in twentieths, so candles share meshes): the model's shape key
## worked into a plain mesh once, so nothing is blended while the game runs.
func _burnt_mesh(title: String, source: Mesh) -> Mesh:
	var step := roundi(burnt * 20.0)
	var key := "%s %d" % [title, step]
	if _baked.has(key):
		return _baked[key]
	var made: Mesh = source
	if source is ArrayMesh and (source as ArrayMesh).get_blend_shape_count() > 0:
		var holder := MeshInstance3D.new()
		holder.mesh = source
		holder.set_blend_shape_value(0, step / 20.0)
		made = holder.bake_mesh_from_current_blend_shape_mix()
		holder.free()
	_baked[key] = made
	return made


static func _wax_material(colour: Color, glow: float) -> StandardMaterial3D:
	var key := "wax %s %.2f" % [colour.to_html(false), glow]
	if _materials.has(key):
		return _materials[key]
	var material := StandardMaterial3D.new()
	material.albedo_texture = WAX_PICTURE
	material.albedo_color = colour
	material.vertex_color_use_as_albedo = true
	material.roughness = 0.5
	material.metallic_specular = 0.35
	material.diffuse_mode = BaseMaterial3D.DIFFUSE_LAMBERT_WRAP
	# wax takes no shadows: its own light, just over its rim, would draw a jagged line down its side
	material.disable_receive_shadows = true
	if glow > 0.0:
		# light through the wax: the glow picture on the second UV set, its top row at the flame
		material.emission_enabled = true
		material.emission_texture = GLOW_PICTURE
		material.emission_on_uv2 = true
		material.emission_operator = BaseMaterial3D.EMISSION_OP_MULTIPLY
		var through := Color.WHITE.lerp(colour, 0.65)
		material.emission = Color(through.r, through.g, through.b)
		material.emission_energy_multiplier = glow * 1.15
	_materials[key] = material
	return material


static func _parts_material() -> StandardMaterial3D:
	if _materials.has("parts"):
		return _materials["parts"]
	var material := StandardMaterial3D.new()
	material.albedo_texture = PARTS_PICTURE
	material.roughness = 0.42
	material.metallic_specular = 0.6
	_materials["parts"] = material
	return material


static func _glass_material() -> StandardMaterial3D:
	if _materials.has("glass"):
		return _materials["glass"]
	var material := StandardMaterial3D.new()
	material.albedo_texture = PARTS_PICTURE
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.roughness = 0.12
	material.metallic_specular = 0.9
	_materials["glass"] = material
	return material


func _flame_material() -> ShaderMaterial:
	var key := "flame %.2f %.2f" % [flame_brightness, halo]
	if _materials.has(key):
		return _materials[key]
	var material := ShaderMaterial.new()
	material.shader = FLAME_SHADER
	material.set_shader_parameter(&"brightness", flame_brightness)
	material.set_shader_parameter(&"halo_strength", halo)
	material.render_priority = 1
	_materials[key] = material
	return material


static func _flame_card() -> QuadMesh:
	if _card == null:
		_card = QuadMesh.new()
		# the shader lays the card out itself (in flame heights about the wick): this is only its reach
		_card.custom_aabb = AABB(Vector3(-2.2, -1.0, -2.2), Vector3(4.4, 6.5, 4.4))
	return _card


# ------------------------------------------------------------------ settings
func _set_kind(value: Kind) -> void:
	kind = value
	_rebuild()


func _set_wax(value: Wax) -> void:
	wax = value
	_lay_wax()


func _set_wax_colour(value: Color) -> void:
	wax_colour = value
	_lay_wax()


func _set_burnt(value: float) -> void:
	burnt = clampf(value, 0.0, 1.0)
	_rebuild()


func _set_size(value: float) -> void:
	size = maxf(value, 0.0001)
	_rebuild()


func _set_low_detail(value: bool) -> void:
	low_detail = value
	_rebuild()


func _set_lit(value: bool) -> void:
	if value == lit:
		return
	lit = value
	if not is_inside_tree():
		return
	if lit:
		_smoke_age = -1.0
	elif smoke:
		_smoke_age = 0.0


func _set_seed(value: int) -> void:
	seed = value
	_rebuild()


func _set_flame_size(value: float) -> void:
	flame_size = maxf(value, 0.0)
	_rebuild()


func _set_flame_brightness(value: float) -> void:
	flame_brightness = maxf(value, 0.0)
	_lay_flames()


func _set_halo(value: float) -> void:
	halo = maxf(value, 0.0)
	_lay_flames()


func _lay_flames() -> void:
	for flame in _flames:
		flame.material_override = _flame_material()


func _set_wax_glow(value: float) -> void:
	wax_glow = maxf(value, 0.0)
	_lay_wax()


func _set_light(value: bool) -> void:
	light = value
	_rebuild()


func _set_light_colour(value: Color) -> void:
	light_colour = value
	_light_look()


func _set_light_range(value: float) -> void:
	light_range = maxf(value, 0.0)
	_light_look()


func _set_light_shadows(value: bool) -> void:
	light_shadows = value
	_light_look()
