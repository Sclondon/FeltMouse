extends Node3D
## The felt mouse on a turntable: drag to turn, pinch or wheel to come closer.
## The model is models/mouse.glb (built by tools/build_mouse.py). Its material names say how each
## part is dressed: felt_* and fleece_* get the felt shader and shells of fuzz, bead_* is shiny
## plastic, thread_* is plain matte thread.

const FELT: Shader = preload("res://shaders/felt.gdshader")
const MODEL: PackedScene = preload("res://models/mouse.glb")
const SHELLS := 14

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

var yaw := 0.35
var pitch := 0.22
var distance := 4.3
var idle := true  ## turns slowly by itself until touched
var _touches := {}
var _pinch := 0.0
var _materials := {}
var _camera: Camera3D
var _turntable: Node3D


func _ready() -> void:
	_build_stage()
	_turntable = Node3D.new()
	add_child(_turntable)
	var model := MODEL.instantiate()
	_turntable.add_child(model)
	for mi: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
		_dress(mi)
	_place_camera()


func _dress(mi: MeshInstance3D) -> void:
	var src := mi.mesh.surface_get_material(0) as BaseMaterial3D
	if src == null:
		return
	var kind := String(src.resource_name)
	if not LOOKS.has(kind):
		if kind.begins_with("bead"):
			src.roughness = 0.12
			src.metallic_specular = 0.8
		else:
			src.roughness = 1.0
		return
	mi.set_surface_override_material(0, _felt(kind, src.albedo_color, 0))
	for i in range(1, SHELLS + 1):
		var shell := MeshInstance3D.new()
		shell.mesh = mi.mesh
		shell.material_override = _felt(kind, src.albedo_color, i)
		shell.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mi.add_child(shell)


func _felt(kind: String, colour: Color, shell: int) -> ShaderMaterial:
	var key := "%s/%d" % [kind, shell]
	if _materials.has(key):
		return _materials[key]
	var m := ShaderMaterial.new()
	m.shader = FELT
	m.set_shader_parameter("tint", colour)
	m.set_shader_parameter("layer", float(shell) / SHELLS)
	var look: Dictionary = LOOKS[kind]
	for k: String in look:
		m.set_shader_parameter(k, look[k])
	_materials[key] = m
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
	env.fog_depth_begin = 7.0
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
	sun.directional_shadow_max_distance = 12.0
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
	_place_camera()


func _place_camera() -> void:
	var target := Vector3(0.0, 0.82, 0.0)
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
				distance = clampf(distance * _pinch / gap, 1.6, 9.0)
			_pinch = gap
		else:
			yaw -= event.relative.x * 0.008
			pitch = clampf(pitch + event.relative.y * 0.006, -0.05, 1.4)
	elif event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			distance = clampf(distance * 0.92, 1.6, 9.0)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			distance = clampf(distance / 0.92, 1.6, 9.0)
