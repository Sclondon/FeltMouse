extends Node3D
## The felt mouse on a turntable: drag to turn, pinch or wheel to come closer.
## He hides under the cocoa's foam, pops out of it, stands on it, sits back down into it (the pose of
## the photo) and ducks under again, on a loop (LOOP seconds, see _pose).
## The model is models/mouse.glb (built by tools/build_mouse.py). Its material names say how each
## part is dressed: felt_* and fleece_* get the felt shader and shells of fuzz, fibre_* are the loose
## strings and loops (the same shader, no shells), bead_* is shiny plastic, thread_* plain thread.

const FELT: Shader = preload("res://shaders/felt.gdshader")
const MODEL: PackedScene = preload("res://models/mouse.glb")
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

## The loop, in seconds: under the foam, burst out, fall, land, pace across the foam and back, lift and
## toss the candy, sit down into the foam, sit, duck under.
const LOOP := 12.2
const T_POP := 1.6
const T_PEAK := 2.0
const T_LAND := 2.35
const T_WALK := 2.95
const T_TOSS := 6.35    ## arms start up
const T_THROW := 6.8    ## the candy leaves his hands
const T_CATCH := 7.6
const T_LOWER := 7.85   ## arms start down
const T_SINK := 8.6
const T_SAT := 9.4
const T_DUCK := 10.5
const T_GONE := 11.0
const STAND := 0.42   ## how far he is lifted to stand on the foam (seated, as in the photo, is 0)
const PEAK := 0.8     ## the top of his jump
const UNDER := -0.04  ## under the foam, shrunk to SMALL so that he fits inside the mug
const SMALL := 0.45
const STEP := 0.08        ## the length of one of his steps
const ARMS_UP := 1.6      ## how far the arms swing to hold the candy over his head, radians
const TOSS_HEIGHT := 0.5  ## how high the candy flies above his raised hands
const ARMS_STRETCH := 0.45  ## how much longer the arms get as they straighten upward
const SIDE := PI / 2.0
## The pacing between T_WALK and T_TOSS. A walk: [from s, to s, true, from where, to where, facing].
## A turn on the spot: [from s, to s, false, where, facing from, facing to].
const WALK := [
	[2.95, 3.25, false, 0.0, 0.0, -SIDE],
	[3.25, 3.75, true, 0.0, -0.16, -SIDE],
	[3.75, 4.15, false, -0.16, -SIDE, SIDE],
	[4.15, 5.15, true, -0.16, 0.16, SIDE],
	[5.15, 5.55, false, 0.16, SIDE, -SIDE],
	[5.55, 6.05, true, 0.16, 0.0, -SIDE],
	[6.05, 6.35, false, 0.0, -SIDE, 0.0],
]

var yaw := 0.35
var pitch := 0.22
var distance := 5.6
var idle := true  ## turns slowly by itself until touched
var playing := true
var clock := 0.0  ## where in the loop he is
var _touches := {}
var _pinch := 0.0
var _materials := {}
var _foam: Array[ShaderMaterial] = []
var _camera: Camera3D
var _mouse: Node3D
var _legs: Array[Node3D] = []
var _tail: Node3D
var _tail_rest: Basis
var _arms: Node3D
var _candy: Node3D
var _candy_rest: Vector3
var _arms_rest: Vector3
var _shells := SHELLS


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
	_arms = model.find_child("ArmsPivot", true, false)
	_candy = model.find_child("CandyPivot", true, false)
	_candy_rest = _candy.position
	_arms_rest = _arms.position
	_pose(clock)
	_place_camera()


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


func _build_stage() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.62, 0.72, 0.82)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.88, 0.88, 0.92)
	env.ambient_light_energy = 0.7
	env.fog_enabled = true
	env.fog_mode = Environment.FOG_MODE_DEPTH
	env.fog_light_color = env.background_color
	env.fog_depth_begin = 8.0
	env.fog_depth_end = 28.0
	env.fog_sun_scatter = 0.0
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	var sun := DirectionalLight3D.new()
	sun.light_color = Color(1.0, 0.95, 0.86)
	sun.light_energy = 0.8
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 14.0
	sun.rotation = Vector3(deg_to_rad(-42.0), deg_to_rad(-140.0), 0.0)
	add_child(sun)

	var ground := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(200.0, 200.0)
	ground.mesh = plane
	var gm := StandardMaterial3D.new()
	gm.albedo_color = Color(0.16, 0.15, 0.15)
	gm.roughness = 0.85
	ground.material_override = gm
	add_child(ground)

	_camera = Camera3D.new()
	_camera.fov = 32.0
	add_child(_camera)


func _process(delta: float) -> void:
	if idle:
		yaw += delta * 0.25
	if playing:
		clock = fmod(clock + delta, LOOP)
		_pose(clock)
	_place_camera()


## Puts the mouse and the foam where they are at t seconds into the loop.
func _pose(t: float) -> void:
	var lift := UNDER   # how high MouseRoot is
	var size := SMALL
	var squash := 1.0   # under 1 is squashed flat, over 1 stretched tall
	var kick := 0.0     # both legs swung forward (+) or trailing back (-), radians
	var stride := 0.0   # legs scissored for walking: left forward (+), right forward (-)
	var across := 0.0   # where he is on the foam, left (-) to right (+)
	var face := 0.0     # which way he faces: 0 the front, a quarter turn either way to walk
	var roll := 0.0     # the waddle
	var raise := 0.0    # arms: 0 down holding the candy in front, 1 up over his head
	var flight := -1.0  # the candy in the air: 0 thrown .. 1 caught (-1 it is in his hands)
	var seen := true
	var stir := 0.22    # the foam is never quite still
	var swell := 0.0
	if t < T_POP:
		# under the foam: it bubbles harder and heaves up in the middle
		seen = false
		var u := t / T_POP
		stir += 0.8 * smoothstep(0.1, 1.0, u)
		swell = 0.09 * u * u * u
	elif t < T_PEAK:
		var u := (t - T_POP) / (T_PEAK - T_POP)
		lift = lerpf(UNDER, PEAK, 1.0 - (1.0 - u) * (1.0 - u))
		size = lerpf(SMALL, 1.0, smoothstep(0.0, 0.5, u))
		squash = 1.0 + 0.16 * sin(u * PI)
		kick = -0.5 * sin(u * PI)
		stir = 1.0
		swell = 0.09 * (1.0 - u)
	elif t < T_LAND:
		var u := (t - T_PEAK) / (T_LAND - T_PEAK)
		lift = lerpf(PEAK, STAND, u * u)
		size = 1.0
		kick = 0.7 * sin(u * PI)
		stir = 0.8
	elif t < T_WALK:
		var u := (t - T_LAND) / (T_WALK - T_LAND)
		lift = STAND
		size = 1.0
		squash = 1.0 - 0.2 * sin(u * PI) * (1.0 - u) + 0.05 * sin(u * TAU) * u
		stir = lerpf(0.8, 0.3, u)
		swell = -0.05 * (1.0 - 0.5 * u)
	elif t < T_TOSS:
		# pacing across the foam and back: turn, walk, turn about, walk, turn about, walk, face front
		lift = STAND
		size = 1.0
		swell = -0.025
		stir = 0.3
		for leg: Array in WALK:
			if t >= leg[0] and t < leg[1]:
				var u: float = (t - leg[0]) / (leg[1] - leg[0])
				var step := 0.0  # half a turn of this is one step
				if leg[2]:
					across = lerpf(leg[3], leg[4], u)
					face = leg[5]
					step = PI * u * absf(leg[4] - leg[3]) / STEP
					stride = 0.34 * sin(step)
				else:
					across = leg[3]
					face = lerpf(leg[4], leg[5], smoothstep(0.0, 1.0, u))
					step = TAU * u
					stride = 0.16 * sin(step)
				lift += 0.016 * absf(sin(step))
				roll = 0.07 * sin(step)
				raise = 0.03 * sin(step * 2.0)
	elif t < T_SINK:
		# the candy: up over his head, thrown, turning over once in the air, caught, brought down
		lift = STAND
		size = 1.0
		swell = -0.025
		if t < T_THROW:
			var u := (t - T_TOSS) / (T_THROW - T_TOSS)
			raise = lerpf(-0.07 * sin(u * PI), 1.0, u * u * (3.0 - 2.0 * u))
			squash = 1.0 - 0.05 * sin(u * PI) + 0.06 * u
		elif t < T_CATCH:
			flight = (t - T_THROW) / (T_CATCH - T_THROW)
			raise = 1.0 - 0.14 * sin(flight * PI)
			squash = 1.06 - 0.06 * smoothstep(0.0, 0.3, flight)
		elif t < T_LOWER:
			var u := (t - T_CATCH) / (T_LOWER - T_CATCH)
			raise = 1.0 - 0.12 * sin(u * PI)
			squash = 1.0 - 0.07 * sin(u * PI)
		else:
			var u := clampf((t - T_LOWER) / 0.5, 0.0, 1.0)
			raise = 1.0 - smoothstep(0.0, 1.0, u)
			lift += 0.012 * sin((t - T_LOWER) * 5.0) * u
	elif t < T_SAT:
		var u := smoothstep(0.0, 1.0, (t - T_SINK) / (T_SAT - T_SINK))
		lift = lerpf(STAND, 0.0, u)
		size = 1.0
		stir = 0.22 + 0.4 * sin(u * PI)
		swell = -0.025 * (1.0 - u)
	elif t < T_DUCK:
		# sitting waist-deep in the foam, as in the photo
		lift = 0.008 * sin((t - T_SAT) * 4.0)
		size = 1.0
	elif t < T_GONE:
		var u := (t - T_DUCK) / (T_GONE - T_DUCK)
		lift = lerpf(0.0, UNDER, u * u)
		size = lerpf(1.0, SMALL, u * u)
		stir = 0.5
	else:
		seen = false
		stir = 0.5 - 0.28 * (t - T_GONE) / (LOOP - T_GONE)

	_mouse.visible = seen
	_mouse.position = Vector3(across, lift, 0.0)
	var wide := size / sqrt(squash)
	_mouse.basis = (Basis(Vector3.UP, face) * Basis(Vector3.BACK, roll)).scaled_local(Vector3(wide, size * squash, wide))
	_legs[0].rotation = Vector3(kick - stride, 0.0, 0.0)
	_legs[1].rotation = Vector3(kick + stride, 0.0, 0.0)
	_tail.basis = Basis(Vector3.UP, 0.3 * sin(t * 6.0)) * Basis(Vector3.RIGHT, -0.5 * kick) * _tail_rest

	# his arms swing up as one from the shoulders, and the candy goes with his hands until it is thrown
	# (the bowed wire straightens as it goes up, and his shoulders shrug: that is what gets the candy clear of his nose
	# and above his head on such short arms)
	var swing := Basis(Vector3.RIGHT, -raise * ARMS_UP)
	var reach := 1.0 + ARMS_STRETCH * smoothstep(0.0, 0.45, raise)
	var reaching := swing * Basis.from_scale(Vector3(1.0, reach, reach))
	_arms.position = _arms_rest + Vector3.UP * (0.08 * clampf(raise, 0.0, 1.0))
	_arms.basis = reaching
	var held := _arms.position + reaching * (_candy_rest - _arms_rest)
	if flight < 0.0:
		_candy.position = held
		_candy.basis = swing
	else:
		_candy.position = held + Vector3.UP * (4.0 * TOSS_HEIGHT * flight * (1.0 - flight))
		_candy.basis = swing * Basis(Vector3.RIGHT, -TAU * flight)

	# splash rings run outward from where he bursts out, where he lands and where he ducks under
	var ring := 0.0
	var ring_at := 0.0
	for burst: Array in [[T_POP + 0.05, 0.07], [T_LAND, 0.04], [T_GONE - 0.1, 0.035]]:
		var age: float = t - burst[0]
		if age > 0.0 and age < 0.9:
			ring = burst[1] * (1.0 - age / 0.9)
			ring_at = 0.12 + age * 0.62
	for m in _foam:
		m.set_shader_parameter("foam_clock", t)
		m.set_shader_parameter("foam_stir", stir)
		m.set_shader_parameter("foam_swell", swell)
		m.set_shader_parameter("foam_ring", ring)
		m.set_shader_parameter("foam_ring_at", ring_at)


func _place_camera() -> void:
	var target := Vector3(0.0, 1.15, 0.0)
	var dir := Vector3(sin(yaw) * cos(pitch), sin(pitch), cos(yaw) * cos(pitch))
	_camera.position = target + dir * distance
	_camera.look_at(target)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		idle = false
		if event.pressed:
			_touches[event.index] = event.position
		else:
			_touches.erase(event.index)
		_pinch = 0.0
	elif event is InputEventScreenDrag:
		_touches[event.index] = event.position
		if _touches.size() >= 2:
			var pts: Array = _touches.values()
			var gap: float = (pts[0] as Vector2).distance_to(pts[1])
			if _pinch > 0.0 and gap > 0.0:
				distance = clampf(distance * _pinch / gap, 1.6, 10.0)
			_pinch = gap
		else:
			yaw -= event.relative.x * 0.008
			pitch = clampf(pitch + event.relative.y * 0.006, -0.05, 1.4)
	elif event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			distance = clampf(distance * 0.92, 1.6, 10.0)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			distance = clampf(distance / 0.92, 1.6, 10.0)
