class_name CloudPuffs
extends Node3D
## Dust as little 3D cloud blobs: each a lump of a few balls that puffs up fast, drifts, and shrinks away.
## Ringtail's foot dust (its `CloudDust`, the user, 2026-11-01: "your foot dust particles should be 3d cloud blobs
## rather than just simple star texture"; "shouldnt just be a perfect sphere, but a cluster of them like a little
## clouds"; "it should spawn in little rings where you step"), with the part that knows about Ringtail's player
## taken out: this one only draws puffs where it is told to. The game says when a foot lands (`ring`), when to
## leave a trail (`puff`), and how big its world is (sizes and speeds are in the game's own units).
##
## Add one as a child of anything (it draws in world space); call `puff` or `ring`. One pool of blobs, drawn
## with one material; no textures.

## How many blobs there can be at once. A ring is 3 to 9 of them and each lives `life` seconds, so 90 covers a
## fast walker; a crowd needs more. When all are in use the oldest is taken.
@export_range(8, 600) var blobs := 90
## How long a puff lives, in seconds: 0.55 is a quick scuff; 1.5 hangs in the air like smoke.
@export_range(0.1, 5.0, 0.01) var life := 0.55
## Its colour: pale dust by default.
@export var colour := Color(0.93, 0.89, 0.82)
## How flat a puff is: 1 a round cloud, 0.7 (the default) settled on the ground, 0.3 a low smear.
@export_range(0.1, 1.5, 0.01) var flat := 0.7
## What it is drawn with. Left empty, a plain matte material in `colour`. A game with a look of its own (a cel
## shader, felt) passes its material here before the node enters the tree.
@export var material: Material

var _parts: Array[MeshInstance3D] = []
var _born: Array[float] = []
var _drift: Array[Vector3] = []
var _size: Array[float] = []
var _next := 0
var _clock := 0.0


func _ready() -> void:
	top_level = true
	global_transform = Transform3D.IDENTITY
	var clusters: Array[Mesh] = []
	for v in 4:
		clusters.append(cluster(v))
	var drawn := material
	if drawn == null:
		var plain := StandardMaterial3D.new()
		plain.albedo_color = colour
		plain.roughness = 1.0
		drawn = plain
	for k in blobs:
		var part := MeshInstance3D.new()
		part.mesh = clusters[k % clusters.size()]
		part.material_override = drawn
		part.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		part.visible = false
		add_child(part)
		_parts.append(part)
		_born.append(-100.0)
		_drift.append(Vector3.ZERO)
		_size.append(0.1)


## A little cloud: a lump of a few balls of different sizes. About 1 unit across before scaling, its bottom at 0.
static func cluster(variant: int) -> Mesh:
	var rng := RandomNumberGenerator.new()
	rng.seed = 7 + variant * 31
	var ball := SphereMesh.new()
	ball.radius = 0.5
	ball.height = 1.0
	ball.radial_segments = 8
	ball.rings = 5
	var tool := SurfaceTool.new()
	tool.begin(Mesh.PRIMITIVE_TRIANGLES)
	var lumps := 4 + variant % 2
	for i in lumps:
		var a := TAU * i / lumps + rng.randf_range(-0.4, 0.4)
		var r := 0.0 if i == 0 else rng.randf_range(0.22, 0.32)
		var size := 0.62 if i == 0 else rng.randf_range(0.34, 0.48)
		tool.append_from(ball, 0, Transform3D(Basis.from_scale(Vector3.ONE * size), Vector3(cos(a) * r, size * 0.5, sin(a) * r)))
	tool.generate_normals()
	return tool.commit()


## One puff at `at` (its bottom, in world space), drifting `drift` (units a second, slowing as it ages), `size`
## across at its fullest.
func puff(at: Vector3, drift: Vector3, size: float) -> void:
	if _parts.is_empty():
		return
	var k := _next
	_next = (_next + 1) % _parts.size()
	_parts[k].position = at
	_parts[k].rotation.y = randf() * TAU
	_parts[k].scale = Vector3.ONE * 0.001
	_born[k] = _clock
	_drift[k] = drift
	_size[k] = size * randf_range(0.8, 1.2)
	_parts[k].visible = true


## A ring of `count` puffs on the ground round `at`, spreading outward at `speed` and lifting by `lift`: a foot
## coming down (3 to 5 small ones), a jump or a landing (6 to 9 bigger ones). `spread` is how far out they start.
func ring(at: Vector3, count: int, speed: float, size: float, lift := 0.25, spread := 0.0) -> void:
	for k in count:
		var a := TAU * k / count + randf() * 0.5
		var out := Vector3(cos(a), 0.0, sin(a))
		puff(at + out * (spread if spread > 0.0 else size * 0.6), out * speed * randf_range(0.7, 1.1) + Vector3.UP * lift * speed, size)


func _process(delta: float) -> void:
	_clock += delta
	for k in _parts.size():
		if not _parts[k].visible:
			continue
		var age := (_clock - _born[k]) / life
		if age >= 1.0:
			_parts[k].visible = false
			continue
		# (puffs up fast, then shrinks away as it drifts and slows)
		var grown := smoothstep(0.0, 0.18, age) * (1.0 - smoothstep(0.45, 1.0, age))
		_parts[k].position += _drift[k] * delta * (1.0 - age)
		_parts[k].scale = Vector3(1.0, flat, 1.0) * maxf(_size[k] * grown, 0.001)
