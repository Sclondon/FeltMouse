extends Node3D
## Felt Mouse: a little felt mouse who lives in a mug of cocoa on a kitchen counter decorated for Christmas.
## He pops out of the foam, hops down, and then the player walks him about the counter (the stick), has him
## toss his candy (the candy button) or sends him home to the mug (the mug button), where he sits down into
## the foam, ducks under and pops out again.
## Models: models/mouse.glb (tools/build_mouse.py) and models/kitchen.glb (tools/build_kitchen.py), with
## data/kitchen.json saying where he can walk. The mouse's material names say how each part is dressed:
## felt_* and fleece_* get the felt shader and shells of fuzz, fibre_* are the loose strings and loops (the
## same shader, no shells), bead_* is shiny plastic, thread_* plain thread.

const FELT: Shader = preload("res://shaders/felt.gdshader")
const MODEL: PackedScene = preload("res://models/mouse.glb")
const KITCHEN: PackedScene = preload("res://models/kitchen.glb")
const Hud := preload("res://scripts/hud.gd")
const SHELLS := 14  ## layers of fuzz on a computer
const SHELLS_PHONE := 8  ## fewer on a phone in a browser, where every layer is drawn over the last

## Fuzz by material name: length off the skin (model units; the mug is 1 wide), fibres per unit,
## how tall the ordinary fuzz stands (0..1 of the length), the share of long loose fibres.
const LOOKS := {
	"felt_white": {"fuzz_length": 0.016, "fibre_density": 420.0, "fuzz_fill": 0.6, "stray": 0.03},
	"felt_brown": {"fuzz_length": 0.034, "fibre_density": 340.0, "fuzz_fill": 0.45, "stray": 0.10},
	"felt_red": {"fuzz_length": 0.014, "fibre_density": 420.0, "fuzz_fill": 0.6, "stray": 0.03},
	"felt_pink": {"fuzz_length": 0.006, "fibre_density": 520.0, "fuzz_fill": 0.7, "stray": 0.0},
	"felt_candy_red": {"fuzz_length": 0.005, "fibre_density": 520.0, "fuzz_fill": 0.7, "stray": 0.0},
	"felt_candy_white": {"fuzz_length": 0.005, "fibre_density": 520.0, "fuzz_fill": 0.7, "stray": 0.0},
	"felt_wafer": {"fuzz_length": 0.012, "fibre_density": 420.0, "fuzz_fill": 0.5, "stray": 0.05},
	"felt_black": {"fuzz_length": 0.010, "fibre_density": 520.0, "fuzz_fill": 0.8, "stray": 0.0},
	"fleece_white": {"fuzz_length": 0.020, "fibre_density": 300.0, "fuzz_fill": 0.8, "stray": 0.01},
}

## What he is doing.
enum Act { POP, HOP_DOWN, FREE, TOSS, HOP_UP, SIT }

## The times of his set pieces, in seconds on one clock: under the foam, burst out, fall, land (POP runs
## 0 .. T_READY); lift and toss the candy (TOSS runs T_TOSS .. T_SINK); sit down into the foam, sit, duck
## under (SIT runs T_SINK .. T_END).
const T_POP := 1.6
const T_PEAK := 2.0
const T_LAND := 2.35
const T_READY := 2.95
const T_TOSS := 6.35    ## arms start up
const T_THROW := 6.8    ## the candy leaves his hands
const T_CATCH := 7.6
const T_LOWER := 7.85   ## arms start down
const T_SINK := 8.6
const T_SAT := 9.4
const T_DUCK := 10.5
const T_GONE := 11.0
const T_END := 11.6
const FEET := 0.38        ## how far his soles are below... above MouseRoot: he stands on y when MouseRoot is at y - FEET
const FOAM_TOP := 0.80    ## the top of the cocoa's foam
const SEATED := 0.0       ## MouseRoot's height sitting waist-deep in the foam, as in the photo
const PEAK := 0.8         ## the top of his jump out of the foam
const UNDER := -0.04      ## under the foam, shrunk to SMALL so that he fits inside the mug
const SMALL := 0.45
const ARMS_UP := 1.6      ## how far the arms swing to hold the candy over his head, radians
const TOSS_HEIGHT := 0.5  ## how high the candy flies above his raised hands
const ARMS_STRETCH := 0.45  ## how much longer the arms get as they straighten upward
const ARMS_HANG := 0.75     ## how far down and back the arms hang when his hands are empty, radians
const WALK_SPEED := 2.3   ## counter units a second (the mug is 1 wide)
const STEP := 0.3         ## the length of one of his steps
const BODY := 0.3        ## how much room he needs round him
const HOP_SPOT := Vector3(0.0, 0.0, 1.9)  ## where he lands on the counter, in front of the mug

## How he is posed at one moment.
class Pose:
	var pos := Vector3.ZERO  # MouseRoot
	var size := 1.0
	var squash := 1.0   # under 1 is squashed flat, over 1 stretched tall
	var kick := 0.0     # both legs swung forward (+) or trailing back (-), radians
	var stride := 0.0   # legs scissored for walking: left forward (+), right forward (-)
	var face := 0.0     # which way he faces: 0 toward the room
	var roll := 0.0     # the waddle
	var raise := 0.0    # arms: 0 down holding the candy in front, 1 up over his head
	var flight := -1.0  # the candy in the air: 0 thrown .. 1 caught (-1 it is in his hands)
	var seen := true
	var stir := 0.22    # the foam is never quite still
	var swell := 0.0    # the middle of the foam heaved up or pressed down
	var ring := 0.0     # a splash ring's height
	var ring_at := 0.0  # and how far out it has run

var yaw := 0.2
var pitch := 0.36
var distance := 13.0
var playing := true  ## false: a test steps the game itself (step)
var act := Act.POP
var clock := 0.0     ## the set pieces' clock
var stick := Vector2.ZERO  ## the walking stick, x right, y up the screen
var autopilot: Array[Vector2] = []  ## places (x, z) to walk to by himself, for films and tests
var _spot := Vector3.ZERO  ## where his feet are on the counter (FREE, TOSS), or the hop's ends
var _hop_from := Vector3.ZERO
var _hop_to := Vector3.ZERO
var _hop := 0.0
var _face := 0.0
var _phase := 0.0   # walking: half a turn of this is one step
var _moving := 0.0  # 0 standing .. 1 walking, eased
var _time := 0.0
var _focus := Vector3(0.0, 1.1, 0.0)
var _walk := {"left": -10.0, "right": 10.0, "front": 2.9, "back": -2.7, "obstacles": []}
var _materials := {}
var _foam: Array[ShaderMaterial] = []
var _shells := SHELLS
var _camera: Camera3D
var _hud: Control
var _mouse: Node3D
var _legs: Array[Node3D] = []
var _tail: Node3D
var _tail_rest: Basis
var _arms: Array[Node3D] = []  # left, right
var _arms_rest: Vector3
var _hold := 1.0  # 1 the candy is in his hands, 0 it is tucked away and his arms hang free
var _candy: Node3D
var _candy_rest: Vector3
var _stick_touch := -1
var _look_touches := {}
var _pinch := 0.0


func _ready() -> void:
	if OS.has_feature("web_android") or OS.has_feature("web_ios"):
		_shells = SHELLS_PHONE
	_build_stage()
	var model := MODEL.instantiate()
	add_child(model)
	for mi: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
		_dress(mi)
	_mouse = model.find_child("MouseRoot", true, false)
	_legs = [model.find_child("LegPivotL", true, false), model.find_child("LegPivotR", true, false)]
	_tail = model.find_child("TailPivot", true, false)
	_tail_rest = _tail.basis
	_arms = [model.find_child("ArmPivotL", true, false), model.find_child("ArmPivotR", true, false)]
	_arms_rest = _arms[0].position
	_candy = model.find_child("CandyPivot", true, false)
	_candy_rest = _candy.position
	_hud = Hud.new()
	_hud.game = self
	var layer := CanvasLayer.new()
	add_child(layer)
	layer.add_child(_hud)
	step(0.0)


# ---------------------------------------------------------------------------------------------- dressing
func _dress(mi: MeshInstance3D) -> void:
	var src := mi.mesh.surface_get_material(0) as BaseMaterial3D
	if src == null:
		return
	var kind := String(src.resource_name)
	var foam := mi.name.begins_with("Cream") or mi.name == "FibresCream"
	if kind.begins_with("fibre"):
		# the loose strings and loops: hair-thin, so they throw no shadow
		mi.set_surface_override_material(0, _felt(kind, src.albedo_color, 0, foam))
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		return
	if not LOOKS.has(kind):
		if kind.begins_with("bead"):
			src.roughness = 0.12
			src.metallic_specular = 0.8
		else:
			src.roughness = 1.0
		return
	mi.set_surface_override_material(0, _felt(kind, src.albedo_color, 0, foam))
	for i in range(1, _shells + 1):
		var shell := MeshInstance3D.new()
		shell.mesh = mi.mesh
		shell.material_override = _felt(kind, src.albedo_color, i, foam)
		shell.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mi.add_child(shell)


func _felt(kind: String, colour: Color, shell: int, foam: bool) -> ShaderMaterial:
	var key := "%s/%d/%s" % [kind, shell, foam]
	if _materials.has(key):
		return _materials[key]
	var m := ShaderMaterial.new()
	m.shader = FELT
	m.set_shader_parameter("tint", colour)
	m.set_shader_parameter("layer", float(shell) / _shells)
	if LOOKS.has(kind):
		var look: Dictionary = LOOKS[kind]
		for k: String in look:
			m.set_shader_parameter(k, look[k])
	else:
		m.set_shader_parameter("fuzz_length", 0.0)
		m.set_shader_parameter("mottle", 0.0)
	_materials[key] = m
	if foam:
		_foam.append(m)
	return m


## Detail pictures laid over the kitchen's plain-coloured materials, so nothing is flat (a storybook made of
## paper, felt and glazed clay). Material name starts with -> [picture, repeats to a unit, bump picture, bump].
## Anything not listed is painted paper. The pictures are textures/*.png, made by tools/build_kitchen.py.
const DETAIL := {
	"pine": ["felt", 0.8, "felt_n", 1.0], "berry": ["felt", 1.4, "felt_n", 0.5], "soil": ["felt", 1.0, "felt_n", 1.0],
	"orange": ["felt", 1.6, "felt_n", 0.35], "wire": ["felt", 1.0, "felt_n", 0.5],
	"trunk": ["grain", 1.0, "felt_n", 0.6], "pin_wood": ["grain", 0.5, "paper_n", 0.4],
	"ceramic": ["glaze", 0.4, "paper_n", 0.12], "kettle": ["glaze", 0.4, "paper_n", 0.12],
	"plate": ["glaze", 0.4, "paper_n", 0.12], "steel": ["glaze", 0.4, "paper_n", 0.1], "glow_": ["glaze", 0.9, "paper_n", 0.0],
	"icing": ["sugar", 1.1, "felt_n", 0.45], "gumdrop": ["sugar", 2.2, "felt_n", 0.6], "flour": ["sugar", 1.0, "felt_n", 0.5],
	"cookie": ["sugar", 1.6, "felt_n", 0.8], "gingerbread": ["felt", 0.9, "felt_n", 0.7], "choc": ["glaze", 1.0, "paper_n", 0.2],
	"wrap_red": ["dots", 1.3, "paper_n", 0.3], "wrap_green": ["stripes", 1.0, "paper_n", 0.3],
	"wrap_gold": ["dots", 2.4, "paper_n", 0.3], "wax": ["glaze", 0.8, "paper_n", 0.25],
}
const DETAIL_PLAIN := ["paper", 0.3, "paper_n", 0.8]

var _pictures := {}


func _picture(nm: String) -> Texture2D:
	if not _pictures.has(nm):
		# (through an Image, to give it mipmaps: seen small, a fine picture would otherwise crawl)
		var img := (load("res://textures/%s.png" % nm) as Texture2D).get_image()
		if img.is_compressed():
			img.decompress()
		img.generate_mipmaps()
		_pictures[nm] = ImageTexture.create_from_image(img)
	return _pictures[nm]


func _texture_kitchen(kitchen: Node) -> void:
	var done := {}
	for mi: MeshInstance3D in kitchen.find_children("*", "MeshInstance3D", true, false):
		var m := mi.mesh.surface_get_material(0) as BaseMaterial3D
		if m == null or done.has(m):
			continue
		done[m] = true
		var nm := String(m.resource_name)
		if nm == "glass":
			# the candy cane jar is clear glass
			m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
			m.albedo_color = Color(0.85, 0.95, 1.0, 0.22)
			m.roughness = 0.04
			m.metallic_specular = 0.9
			m.cull_mode = BaseMaterial3D.CULL_DISABLED
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			continue
		if nm == "night_outside":
			m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED  # the night lights itself
			m.albedo_color = Color(0.8, 0.8, 0.8)
			continue
		if nm == "window_frost":
			# ice where textures/frost_cover.png is white, clear glass where it is black
			var cover := (load("res://textures/frost_cover.png") as Texture2D).get_image()
			if cover.is_compressed():
				cover.decompress()
			var ice := Image.create(cover.get_width(), cover.get_height(), false, Image.FORMAT_RGBA8)
			for py in cover.get_height():
				for px in cover.get_width():
					var c := cover.get_pixel(px, py).r
					ice.set_pixel(px, py, Color(0.74 + 0.2 * c, 0.84 + 0.12 * c, 0.97, c))
			ice.generate_mipmaps()
			m.albedo_texture = ImageTexture.create_from_image(ice)
			m.albedo_color = Color.WHITE
			m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			m.emission_enabled = true  # the ice catches the room's light
			m.emission = Color(0.10, 0.13, 0.20)
			continue
		if m.albedo_texture != null:
			continue  # wood, tiles, candy canes: they have pictures of their own
		var look: Array = DETAIL_PLAIN
		for key: String in DETAIL:
			if nm.begins_with(key):
				look = DETAIL[key]
				break
		m.albedo_texture = _picture(look[0])
		m.uv1_triplanar = true
		m.uv1_world_triplanar = true
		m.uv1_scale = Vector3.ONE * float(look[1])
		if float(look[3]) > 0.0:
			m.normal_enabled = true
			m.normal_texture = _picture(look[2])
			m.normal_scale = float(look[3])
		if not nm.begins_with("glow_"):
			m.albedo_color = m.albedo_color.lightened(0.12)  # (the picture is greys under white: make up some of it)


func _build_stage() -> void:
	var phone := OS.has_feature("web_android") or OS.has_feature("web_ios")
	var file := FileAccess.open("res://data/kitchen.json", FileAccess.READ)
	if file:
		_walk = JSON.parse_string(file.get_as_text())

	# A cosy Christmas night ("needs to feel more cozy Christmas night rather than bright blast", the user): the room
	# itself is nearly dark; the light is the string of bulbs, the candle, the tree's star and a low warm glow.
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.012, 0.012, 0.025)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.50, 0.55, 0.85)
	env.ambient_light_energy = 0.11
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	if not phone:
		env.glow_enabled = true
		env.glow_intensity = 0.55
		env.glow_bloom = 0.04
		env.glow_hdr_threshold = 0.95
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	# one faint warm lamp from over the player's shoulder, for the shadows that sit things on the counter
	var lamp := DirectionalLight3D.new()
	lamp.light_color = Color(1.0, 0.80, 0.58)
	lamp.light_energy = 0.2
	lamp.shadow_enabled = true
	lamp.directional_shadow_max_distance = 34.0
	lamp.rotation = Vector3(deg_to_rad(-52.0), deg_to_rad(28.0), 0.0)
	add_child(lamp)

	var kitchen := KITCHEN.instantiate()
	add_child(kitchen)
	_texture_kitchen(kitchen)
	# a real light at each lamp the model marks (Lamp_glow_<colour>_...), in the colour of its bulb
	var glows := {}
	for mi: MeshInstance3D in kitchen.find_children("*", "MeshInstance3D", true, false):
		var mat := mi.mesh.surface_get_material(0) as BaseMaterial3D
		if mat and String(mat.resource_name).begins_with("glow_"):
			glows[String(mat.resource_name)] = mat.albedo_color
	for mark: Node3D in kitchen.find_children("Lamp_*", "Node3D", true, false):
		var colour := Color(1.0, 0.8, 0.5)
		for nm: String in glows:
			if String(mark.name).contains(nm):
				colour = glows[nm]
		var flame := String(mark.name).contains("flame")
		var light := OmniLight3D.new()
		light.light_color = colour.lerp(Color(1.0, 0.85, 0.6), 0.25)
		light.light_energy = 2.1 if flame else 1.15
		light.omni_range = 11.0 if flame else 7.5
		light.omni_attenuation = 1.4
		light.position = mark.position
		kitchen.add_child(light)
	# the low warm glow of the room behind the player, along the counter
	for x: float in [-5.0, 3.0, 10.5]:
		var glow := OmniLight3D.new()
		glow.light_color = Color(1.0, 0.66, 0.36)
		glow.light_energy = 0.5
		glow.omni_range = 10.0
		glow.omni_attenuation = 1.2
		glow.position = Vector3(x, 3.4, 2.4)
		add_child(glow)

	# the garland's needles: GameCommon's pine tree fronds grown along each swag of its rope
	if _walk.has("garland"):
		var pine := PineTree.new()
		pine.fullness = 0.6
		pine.sprigs = 2
		pine.droop = 0.5
		pine.needles_inner = Color(0.14, 0.38, 0.22)  # (lighter than a tree out of doors: the room is dark)
		pine.needles_outer = Color(0.30, 0.62, 0.34)
		pine.tips = Color(0.55, 0.80, 0.45)
		var swag := 0
		for points: Array in _walk["garland"]:
			var line: Array[Vector3] = []
			for p: Array in points:
				line.append(Vector3(p[0], p[1], p[2]))
			pine.seed = 11 + swag
			var boughs := pine.garland_instance(line, 0.66, 12.0, 0.7)
			(boughs.material_override as ShaderMaterial).set_shader_parameter("sway", 0.006)  # indoors: barely a stir
			add_child(boughs)
			swag += 1

	# a snow storm blowing past outside the window, between the glass and the painted night
	if _walk.has("window"):
		var w: Dictionary = _walk["window"]
		var snow := CPUParticles3D.new()
		snow.amount = 140 if phone else 340
		snow.lifetime = 2.4
		snow.preprocess = 3.0
		snow.local_coords = true
		snow.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
		snow.emission_box_extents = Vector3(w["wide"] * 0.5 + 3.0, 0.3, (w["glass"] - w["night"]) * 0.2)
		snow.position = Vector3(w["x"] + 2.6, w["y"] + w["tall"] * 0.5 + 1.2, w["glass"] * 0.42 + w["night"] * 0.58)
		snow.direction = Vector3(-0.6, -1.0, 0.0)
		snow.spread = 3.0  # (kept narrow: a wide cone sends flakes through the wall into the room)
		snow.initial_velocity_min = 2.6
		snow.initial_velocity_max = 4.4
		snow.gravity = Vector3(-1.8, -1.2, 0.0)
		snow.scale_amount_min = 0.5
		snow.scale_amount_max = 1.5
		var flake := QuadMesh.new()
		flake.size = Vector2(0.085, 0.085)
		var white := StandardMaterial3D.new()
		white.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		white.albedo_color = Color(0.86, 0.90, 1.0)
		white.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
		white.billboard_keep_scale = true
		flake.material = white
		snow.mesh = flake
		add_child(snow)

	_camera = Camera3D.new()
	_camera.fov = 36.0
	add_child(_camera)


# ---------------------------------------------------------------------------------------------- the game
func _process(delta: float) -> void:
	if playing:
		step(delta)


## One frame of the game.
func step(delta: float) -> void:
	_time += delta
	var p := Pose.new()
	match act:
		Act.POP:
			clock += delta
			_show_pose(p, clock)
			if clock >= T_READY:
				_start_hop(Vector3(0.0, FOAM_TOP, 0.0), HOP_SPOT, Act.HOP_DOWN)
		Act.HOP_DOWN, Act.HOP_UP:
			_hop = minf(_hop + delta / (0.6 if act == Act.HOP_DOWN else 0.8), 1.0)
			var at := _hop_from.lerp(_hop_to, _hop)
			at.y += (0.9 if act == Act.HOP_DOWN else 1.6) * 4.0 * _hop * (1.0 - _hop)
			p.pos = at - Vector3(0.0, FEET, 0.0)
			p.kick = 0.6 * sin(_hop * PI)
			p.squash = 1.0 + 0.1 * sin(_hop * PI)
			_face = lerp_angle(_face, 0.0, minf(delta * 8.0, 1.0))
			p.face = _face
			if _hop >= 1.0:
				_spot = _hop_to
				if act == Act.HOP_DOWN:
					act = Act.FREE
				else:
					act = Act.SIT
					clock = T_SINK
		Act.FREE:
			_walk_about(p, delta)
		Act.TOSS:
			if _hold >= 0.99:  # (first he brings the candy out)
				clock += delta
			p.pos = _spot - Vector3(0.0, FEET, 0.0)
			p.face = _face
			_toss_pose(p, clock)
			if clock >= T_SINK:
				act = Act.FREE
		Act.SIT:
			clock += delta
			_show_pose(p, clock)
			if clock >= T_END:
				act = Act.POP
				clock = 0.0
	# the candy is in his hands in the mug, when he tosses it and on the way home; walking about, it is tucked away
	# ("The mouse shouldnt carry the candy around all the time", the user)
	var holding := act != Act.FREE and act != Act.HOP_DOWN
	_hold = move_toward(_hold, 1.0 if holding else 0.0, delta * 3.5)
	_apply(p)
	_focus = _focus.lerp(_mouse.position + Vector3(0.0, 2.1, 0.0), minf(delta * 5.0, 1.0) if delta > 0.0 else 1.0)
	_place_camera()
	_hud.queue_redraw()


func _start_hop(from: Vector3, to: Vector3, next: Act) -> void:
	_hop_from = from
	_hop_to = to
	_hop = 0.0
	act = next


## The candy button: lift it, toss it, catch it.
func toss() -> void:
	if act == Act.FREE:
		act = Act.TOSS
		clock = T_TOSS
		_moving = 0.0


## The mug button: one long hop back onto the foam, then down into it.
func go_home() -> void:
	if act == Act.FREE:
		autopilot.clear()
		_start_hop(_spot, Vector3(0.0, FOAM_TOP, 0.0), Act.HOP_UP)


func can_act() -> bool:
	return act == Act.FREE


func _walk_about(p: Pose, delta: float) -> void:
	var want := Vector2.ZERO  # x right, y away from the camera
	if not autopilot.is_empty():
		var to := autopilot[0] - Vector2(_spot.x, _spot.z)
		if to.length() < 0.15:
			autopilot.pop_front()
		else:
			want = to.normalized()
	else:
		want = stick
		want.x += float(Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT)) - float(Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT))
		want.y += float(Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP)) - float(Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN))
		want = want.limit_length(1.0)
		# the stick is as the camera sees it: up the screen is away from the camera
		want = Vector2(want.x * cos(yaw) - want.y * sin(yaw), -want.x * sin(yaw) - want.y * cos(yaw))
	var speed := want.length()
	if speed > 0.08:
		_spot.x += want.x * WALK_SPEED * delta
		_spot.z += want.y * WALK_SPEED * delta
		_keep_on_counter()
		_face = lerp_angle(_face, atan2(want.x, want.y), minf(delta * 10.0, 1.0))
		_phase += speed * WALK_SPEED * delta * PI / STEP
		_moving = minf(_moving + delta * 8.0, 1.0)
	else:
		_moving = maxf(_moving - delta * 6.0, 0.0)
	p.pos = _spot - Vector3(0.0, FEET, 0.0)
	p.pos.y += 0.035 * absf(sin(_phase)) * _moving + 0.008 * sin(_time * 3.0) * (1.0 - _moving)
	p.stride = 0.5 * sin(_phase) * _moving
	p.roll = 0.08 * sin(_phase) * _moving
	p.raise = 0.04 * sin(_phase * 2.0) * _moving
	p.face = _face


## Keeps him on the counter top and out of the things standing on it.
func _keep_on_counter() -> void:
	for round in 2:
		for o: Array in _walk["obstacles"]:
			var away := Vector2(_spot.x - o[0], _spot.z - o[1])
			var room: float = o[2] + BODY
			if away.length() < room:
				away = away.normalized() * room if away.length() > 0.001 else Vector2(0.0, room)
				_spot.x = o[0] + away.x
				_spot.z = o[1] + away.y
		for b: Array in _walk.get("boxes", []):
			# a rectangle (the sink): out by the nearest side
			var x0: float = b[0] - BODY
			var z0: float = b[1] - BODY
			var x1: float = b[2] + BODY
			var z1: float = b[3] + BODY
			if _spot.x > x0 and _spot.x < x1 and _spot.z > z0 and _spot.z < z1:
				var outs := [_spot.x - x0, x1 - _spot.x, _spot.z - z0, z1 - _spot.z]
				match outs.find(outs.min()):
					0: _spot.x = x0
					1: _spot.x = x1
					2: _spot.z = z0
					3: _spot.z = z1
		_spot.x = clampf(_spot.x, _walk["left"], _walk["right"])
		_spot.z = clampf(_spot.z, _walk["back"], _walk["front"])


## The set pieces in the mug: popping out (0 .. T_READY) and sitting back in (T_SINK .. T_END).
func _show_pose(p: Pose, t: float) -> void:
	var lift := UNDER
	var stand := FOAM_TOP - FEET
	p.size = SMALL
	if t < T_POP:
		# under the foam: it bubbles harder and heaves up in the middle
		p.seen = false
		var u := t / T_POP
		p.stir += 0.8 * smoothstep(0.1, 1.0, u)
		p.swell = 0.09 * u * u * u
	elif t < T_PEAK:
		var u := (t - T_POP) / (T_PEAK - T_POP)
		lift = lerpf(UNDER, PEAK, 1.0 - (1.0 - u) * (1.0 - u))
		p.size = lerpf(SMALL, 1.0, smoothstep(0.0, 0.5, u))
		p.squash = 1.0 + 0.16 * sin(u * PI)
		p.kick = -0.5 * sin(u * PI)
		p.stir = 1.0
		p.swell = 0.09 * (1.0 - u)
	elif t < T_LAND:
		var u := (t - T_PEAK) / (T_LAND - T_PEAK)
		lift = lerpf(PEAK, stand, u * u)
		p.size = 1.0
		p.kick = 0.7 * sin(u * PI)
		p.stir = 0.8
	elif t < T_READY:
		var u := (t - T_LAND) / (T_READY - T_LAND)
		lift = stand
		p.size = 1.0
		p.squash = 1.0 - 0.2 * sin(u * PI) * (1.0 - u) + 0.05 * sin(u * TAU) * u
		p.stir = lerpf(0.8, 0.3, u)
		p.swell = -0.05 * (1.0 - 0.5 * u)
	elif t < T_SAT:
		var u := smoothstep(0.0, 1.0, (t - T_SINK) / (T_SAT - T_SINK))
		lift = lerpf(stand, SEATED, u)
		p.size = 1.0
		p.stir = 0.22 + 0.4 * sin(u * PI)
		p.swell = -0.025 * (1.0 - u)
	elif t < T_DUCK:
		# sitting waist-deep in the foam, as in the photo
		lift = SEATED + 0.008 * sin((t - T_SAT) * 4.0)
		p.size = 1.0
	elif t < T_GONE:
		var u := (t - T_DUCK) / (T_GONE - T_DUCK)
		lift = lerpf(SEATED, UNDER, u * u)
		p.size = lerpf(1.0, SMALL, u * u)
		p.stir = 0.5
	else:
		p.seen = false
		p.stir = 0.5 - 0.28 * (t - T_GONE) / (T_END - T_GONE)
	p.pos = Vector3(0.0, lift, 0.0)
	# splash rings run outward from where he bursts out, where he lands and where he ducks under
	for burst: Array in [[T_POP + 0.05, 0.07], [T_LAND, 0.04], [T_GONE - 0.1, 0.035]]:
		var age: float = t - burst[0]
		if age > 0.0 and age < 0.9:
			p.ring = burst[1] * (1.0 - age / 0.9)
			p.ring_at = 0.12 + age * 0.62


## The candy: up over his head, thrown, turning over once in the air, caught, brought down (T_TOSS .. T_SINK).
func _toss_pose(p: Pose, t: float) -> void:
	if t < T_THROW:
		var u := (t - T_TOSS) / (T_THROW - T_TOSS)
		p.raise = lerpf(-0.07 * sin(u * PI), 1.0, u * u * (3.0 - 2.0 * u))
		p.squash = 1.0 - 0.05 * sin(u * PI) + 0.06 * u
	elif t < T_CATCH:
		p.flight = (t - T_THROW) / (T_CATCH - T_THROW)
		p.raise = 1.0 - 0.14 * sin(p.flight * PI)
		p.squash = 1.06 - 0.06 * smoothstep(0.0, 0.3, p.flight)
	elif t < T_LOWER:
		var u := (t - T_CATCH) / (T_LOWER - T_CATCH)
		p.raise = 1.0 - 0.12 * sin(u * PI)
		p.squash = 1.0 - 0.07 * sin(u * PI)
	else:
		var u := clampf((t - T_LOWER) / 0.5, 0.0, 1.0)
		p.raise = 1.0 - smoothstep(0.0, 1.0, u)


func _apply(p: Pose) -> void:
	_mouse.visible = p.seen
	_mouse.position = p.pos
	var wide := p.size / sqrt(p.squash)
	_mouse.basis = (Basis(Vector3.UP, p.face) * Basis(Vector3.BACK, p.roll)).scaled_local(Vector3(wide, p.size * p.squash, wide))
	_legs[0].rotation = Vector3(p.kick - p.stride, 0.0, 0.0)
	_legs[1].rotation = Vector3(p.kick + p.stride, 0.0, 0.0)
	_tail.basis = Basis(Vector3.UP, 0.3 * sin(_time * 6.0)) * Basis(Vector3.RIGHT, -0.5 * p.kick) * _tail_rest

	# his arms swing up as one from the shoulders, and the candy goes with his hands until it is thrown
	# (the bowed wire straightens as it goes up, and his shoulders shrug: that is what gets the candy clear of his nose
	# and above his head on such short arms)
	var lift_angle := -p.raise * ARMS_UP
	var swing := Basis(Vector3.RIGHT, lift_angle)
	var reach := 1.0 + ARMS_STRETCH * smoothstep(0.0, 0.45, p.raise)
	var stretch := Basis.from_scale(Vector3(1.0, reach, reach))
	var shrug := Vector3.UP * (0.08 * clampf(p.raise, 0.0, 1.0))
	var ease := smoothstep(0.0, 1.0, _hold)
	for i in 2:
		# without the candy each arm hangs lower and swings against the leg on its side
		var hang := ARMS_HANG + (0.9 if i == 0 else -0.9) * p.stride
		_arms[i].position = _arms_rest + shrug
		_arms[i].basis = Basis(Vector3.RIGHT, lerpf(hang, lift_angle, ease)) * stretch
	var held := _arms_rest + shrug + swing * stretch * (_candy_rest - _arms_rest)
	var grown := Vector3.ONE * maxf(ease, 0.001)  # it pops out as he brings it round, and away again
	_candy.visible = _hold > 0.02
	if p.flight < 0.0:
		_candy.position = held
		_candy.basis = swing.scaled_local(grown)
	else:
		_candy.position = held + Vector3.UP * (4.0 * TOSS_HEIGHT * p.flight * (1.0 - p.flight))
		_candy.basis = (swing * Basis(Vector3.RIGHT, -TAU * p.flight)).scaled_local(grown)

	for m in _foam:
		m.set_shader_parameter("foam_clock", _time)
		m.set_shader_parameter("foam_stir", p.stir)
		m.set_shader_parameter("foam_swell", p.swell)
		m.set_shader_parameter("foam_ring", p.ring)
		m.set_shader_parameter("foam_ring_at", p.ring_at)


func _place_camera() -> void:
	var dir := Vector3(sin(yaw) * cos(pitch), sin(pitch), cos(yaw) * cos(pitch))
	_camera.position = _focus + dir * distance
	_camera.look_at(_focus)


# ---------------------------------------------------------------------------------------------- touch and keys
## Every touch is sorted here by where it starts: on a button, on the stick, or anywhere else to look about.
func _input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		if event.pressed:
			var button: String = _hud.button_at(event.position)
			if button == "toss":
				toss()
			elif button == "home":
				go_home()
			elif _stick_touch < 0 and _hud.on_stick(event.position):
				_stick_touch = event.index
				stick = _hud.stick_from(event.position)
			else:
				_look_touches[event.index] = event.position
		else:
			if event.index == _stick_touch:
				_stick_touch = -1
				stick = Vector2.ZERO
			_look_touches.erase(event.index)
		_pinch = 0.0
	elif event is InputEventScreenDrag:
		if event.index == _stick_touch:
			stick = _hud.stick_from(event.position)
		elif _look_touches.has(event.index):
			_look_touches[event.index] = event.position
			if _look_touches.size() >= 2:
				var pts: Array = _look_touches.values()
				var gap: float = (pts[0] as Vector2).distance_to(pts[1])
				if _pinch > 0.0 and gap > 0.0:
					distance = clampf(distance * _pinch / gap, 4.0, 20.0)
				_pinch = gap
			else:
				yaw = clampf(yaw - event.relative.x * 0.006, -1.15, 1.15)
				pitch = clampf(pitch + event.relative.y * 0.005, 0.12, 1.2)
	elif event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			distance = clampf(distance * 0.92, 4.0, 20.0)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			distance = clampf(distance / 0.92, 4.0, 20.0)
	elif event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_SPACE or event.keycode == KEY_E:
			toss()
		elif event.keycode == KEY_H or event.keycode == KEY_Q:
			go_home()
