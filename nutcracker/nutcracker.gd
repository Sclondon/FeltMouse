class_name Nutcracker
extends Node3D
## A wooden nutcracker: one of five turned-and-painted figures built in Blender (a soldier in a tall
## shako, a king with crown and sceptre, a drummer, a guard in a bearskin with a sword, a baker with a
## rolling pin), each with a jaw that works on the lever down its back, arms on shoulder pegs, a fur
## beard and hair, and a turned plinth. This node is at the middle of the plinth's foot, on the table;
## the figure faces +z.
##
##     var nut := Nutcracker.new()
##     nut.kind = Nutcracker.Kind.SOLDIER
##     nut.palette = Nutcracker.Palette.CLASSIC
##     nut.size = 12.5               # the models are in metres: 12.5 for a game whose unit is 8 cm
##     nut.motion = Nutcracker.Motion.MARCH
##     add_child(nut)
##     nut.crack()                   # opens wide and snaps shut; nut.salute(); nut.bump(direction)
##     var keep_out := nut.footprint()   # {centre, radius, height, ...}: see footprint()
##
## A figure is ONE draw (one mesh, one surface), two when it holds a walnut. Every figure in the game
## shares one material and one shader program; its colours and its pose are numbers of its own
## (instance uniforms), so a row of ten is ten draws of the same program with nothing rebuilt.

## The jaw has snapped shut (crack(), CLACK, a bump): the moment for a game's clack sound.
signal clacked
## crack() has broken the walnut it held (`holds` is now CRACKED_WALNUT).
signal cracked
## The plinth has come down flat on a step of the march: the moment for a footfall.
signal stepped
## A drumstick (or a miming arm) has come down. `right` says which.
signal drummed(right: bool)

enum Kind {
	SOLDIER,   ## tall and slim: a tall black shako with a peak, a badge and a pom-pom, braid across the chest
	KING,      ## stout, in a robe to the floor with an ermine hem: a crown, a long beard, a sceptre
	DRUMMER,   ## short, big-headed and boyish: a pillbox hat with a plume, a drum slung in front, two sticks
	GUARD,     ## the tallest and thinnest: a huge bearskin, white cross-belts, a sword held upright
	BAKER,     ## round-bellied: a puffed white baker's hat, an apron, a curled moustache, a rolling pin
}

enum Palette {
	CLASSIC,           ## red coat, blue trousers, black hat, gold trim, white hair
	GREEN_AND_GOLD,    ## green coat, dark red trousers, dark green hat, gold trim, white hair
	WHITE_AND_SILVER,  ## white coat, pale blue trousers, slate blue hat, silver trim, pale blond hair
	CUSTOM,            ## the six colour settings below
}

enum Holds {
	NOTHING,
	WALNUT,          ## a whole walnut between its teeth (crack() breaks it)
	CRACKED_WALNUT,  ## the two halves of one, the kernel showing
}

enum Motion {
	STILL,   ## stands as it was made
	CLACK,   ## opens its jaw and snaps it shut, over and over
	MARCH,   ## marches on the spot: rocks from side to side on its plinth, arms swinging stiffly
	DRUM,    ## beats its drum, one stick after the other (the kinds with no drum beat the air)
	SALUTE,  ## holds a salute (the kinds with something in the right hand raise that)
}

const NAMES: Array[String] = ["soldier", "king", "drummer", "guard", "baker"]
## coat, trousers, hat, trim, hair, skin for each palette but CUSTOM
const PALETTES: Array = [
	[Color(0.72, 0.08, 0.07), Color(0.1, 0.2, 0.5), Color(0.05, 0.05, 0.06), Color(0.86, 0.66, 0.2),
			Color(0.93, 0.91, 0.86), Color(0.93, 0.72, 0.58)],
	[Color(0.1, 0.36, 0.17), Color(0.5, 0.07, 0.08), Color(0.05, 0.13, 0.08), Color(0.86, 0.66, 0.2),
			Color(0.93, 0.91, 0.86), Color(0.93, 0.72, 0.58)],
	[Color(0.93, 0.93, 0.9), Color(0.5, 0.6, 0.74), Color(0.2, 0.27, 0.4), Color(0.74, 0.76, 0.8),
			Color(0.88, 0.82, 0.66), Color(0.94, 0.75, 0.62)],
]

# ---- how far things turn, in degrees. tools/build_nutcrackers.py checks that nothing cuts into
# anything over exactly these (CHECKED POSES there): change both.
## The jaw opens at most this far.
const JAW_MAX := 16.0
## How far each arm may swing about its peg: right from, to; left from, to (under 0 is forwards and up).
const ARM_RANGE: Array = [[-155.0, 40.0, -60.0, 40.0], [-45.0, 12.0, -60.0, 40.0], [-55.0, 0.0, -30.0, 0.0],
		[-48.0, 12.0, -60.0, 40.0], [-50.0, 12.0, -60.0, 40.0]]
## The right arm's salute: its swing, and how far it leans in towards the hat.
const SALUTES: Array[Vector2] = [Vector2(-150.0, 8.0), Vector2(-40.0, 0.0), Vector2(-50.0, 0.0),
		Vector2(-42.0, 0.0), Vector2(-45.0, 0.0)]
## The moustache sits crooked by up to this either way, by the seed.
const TASH_TILT := 7.0
## How far the arms swing in a march (right, left), and rise to beat a drum.
const MARCH_SWING: Array = [[26.0, 26.0], [8.0, 22.0], [14.0, 14.0], [8.0, 24.0], [8.0, 24.0]]
const DRUM_RISE: Array = [[32.0, 32.0], [14.0, 30.0], [18.0, 18.0], [12.0, 30.0], [14.0, 30.0]]

const MODELS := preload("models/nutcrackers.glb")
const PAINT := preload("textures/nutcracker_paint.png")
const MASKS := preload("textures/nutcracker_masks.png")
const SHADER := preload("nutcracker.gdshader")

## Which figure it is (see Kind): the soldier by default.
@export var kind := Kind.SOLDIER: set = _set_kind
## Its uniform: classic red and blue (the default), green and gold, white and silver, or CUSTOM to use the
## six colours below.
@export var palette := Palette.CLASSIC: set = _set_palette
## How big it is. The models are made in metres (the soldier stands 47 cm tall with his hat, the drummer
## 40 cm), so 1 suits a game counted in metres and 12.5 a game whose unit is 8 cm. Default 1.
@export_range(0.01, 100.0, 0.01, "or_greater") var size := 1.0: set = _set_size
## Draw the low model (about 500 to 600 triangles in place of 1,400 to 1,560: half the sides, three-sided
## locks of fur, no slot behind the jaw, the belt only painted). For figures that are small on screen.
## Everything still moves. Default off.
@export var low_detail := false: set = _set_low_detail
## A number that sets what is left to chance in this one figure: where its paint has chipped, how
## crooked its moustache sits, how its arms hang, whether its jaw is quite shut, and the beat it keeps
## (so a row of them do not move in step). 0 (the default) gives every figure a different one; any
## other number always gives the same figure.
@export var seed := 0: set = _set_seed
## How worn its paint is: 0 fresh from the workshop with not a chip, 0.35 (the default) the odd chip
## on its edges and nose showing wood, 1 well loved and chipped all over, 3 most of the paint gone.
@export_range(0.0, 3.0, 0.01, "or_greater") var wear := 0.35: set = _set_wear
## What it has between its teeth: nothing (the default), a whole walnut, or a cracked one. Its jaw rests
## open on it. crack() breaks a whole one.
@export var holds := Holds.NOTHING: set = _set_holds
## What it is doing (see Motion): standing still by default. crack(), salute() and bump() play over
## any of them.
@export var motion := Motion.STILL: set = _set_motion
## How lively its motions are: 0 barely moving and slow, 1 (the default) a brisk toy, 2 frantic with
## wide swings. It changes both how fast and how far.
@export_range(0.0, 3.0, 0.01, "or_greater") var liveliness := 1.0
## How far its jaw hangs open when it is doing nothing with it: 0 shut (the default), 1 as wide as it
## goes. Ignored while it holds a walnut.
@export_range(0.0, 1.0) var jaw_open := 0.0: set = _set_jaw_open
## It casts a shadow. Default on.
@export var shadows := true: set = _set_shadows

@export_group("Custom colours")
## The coat, sleeves, the king's robe, the drum's shell and the plumes, when `palette` is CUSTOM.
@export var coat_colour := Color(0.72, 0.08, 0.07): set = _set_coat
## The trousers, when `palette` is CUSTOM.
@export var trousers_colour := Color(0.1, 0.2, 0.5): set = _set_trousers
## The hat: the shako, the pillbox, the bearskin's fur (the crown wears the trim colour over a cap in
## the coat colour, and the baker's hat is always white), when `palette` is CUSTOM.
@export var hat_colour := Color(0.05, 0.05, 0.06): set = _set_hat
## Everything painted on in gold: braid, buttons, epaulettes, cuffs, the stripe down the trousers, the
## buckle, the crown, the sword's hilt, when `palette` is CUSTOM.
@export var trim_colour := Color(0.86, 0.66, 0.2): set = _set_trim
## The fur: hair, beard and moustache, when `palette` is CUSTOM. Dark colours hide the fur's strands.
@export var hair_colour := Color(0.93, 0.91, 0.86): set = _set_hair
## The painted face and hands, when `palette` is CUSTOM.
@export var skin_colour := Color(0.93, 0.72, 0.58): set = _set_skin

static var _library: Dictionary = {}
static var _sources: Dictionary = {}
static var _material: ShaderMaterial

var _body: Node3D          # scaled by `size`
var _rocker: Node3D        # rocks about the plinth's edge
var _figure: MeshInstance3D
var _held: Node3D
var _model: Dictionary = {}
var _queued := false
var _rng := RandomNumberGenerator.new()
var _time := 0.0
var _jaw := 0.0            # degrees, as drawn
var _arm_r := 0.0
var _arm_l := 0.0
var _lean_r := 0.0
var _rest_r := 0.0         # how the arms hang, by the seed
var _rest_l := 0.0
var _ajar := 0.0
var _tash := 0.0
var _chips := 0.0
var _hold_angle := 0.0
var _crack_at := -1.0      # seconds into a crack(), under 0 when none
var _crack_done := false
var _salute_at := -1.0
var _wobble_at := -1.0
var _wobble_way := Vector2.ZERO
var _wobble_size := 0.0
var _last_wave := 0.0
var _last_clack := 0.0


## A nutcracker ready to add: Nutcracker.make(Nutcracker.Kind.KING, Nutcracker.Palette.GREEN_AND_GOLD, 12.5, 4).
static func make(of_kind: Kind, of_palette := Palette.CLASSIC, of_size := 1.0, of_seed := 0) -> Nutcracker:
	var nut := Nutcracker.new()
	nut.kind = of_kind
	nut.palette = of_palette
	nut.size = of_size
	nut.seed = of_seed
	return nut


## A walnut by itself, lying on its side on the floor at the node's place (27 mm long at size 1), whole
## or as two cracked halves with the kernel showing: for a bowl of nuts, or what falls out of the jaw.
## It is drawn with the nutcrackers' material: one draw whole, two cracked.
static func walnut(is_cracked := false, of_size := 1.0, low := false) -> Node3D:
	var nut := Node3D.new()
	nut.name = "Walnut"
	nut.scale = Vector3.ONE * of_size
	var tail := "_lo" if low else ""
	if is_cracked:
		# each half on its back, kernel up, a little apart and turned
		for half: Array in [["walnut_half_a", Vector3.FORWARD, -0.0135, Vector3(0.012, 0.0, 0.005), 0.5],
				["walnut_half_b", Vector3.BACK, 0.0135, Vector3(-0.013, 0.0, -0.006), -0.9]]:
			var spot := Node3D.new()
			spot.position = half[3]
			spot.rotation.y = half[4]
			nut.add_child(spot)
			var part := _nut_part(String(half[0]) + tail)
			part.transform = Transform3D(Basis(half[1], PI * 0.5), Vector3(half[2], 0.0118, 0.0))
			spot.add_child(part)
	else:
		var whole := _nut_part("walnut_whole" + tail)
		whole.transform = Transform3D(Basis(Vector3.FORWARD, PI * 0.5), Vector3(-0.0135, 0.0118, 0.0))
		nut.add_child(whole)
	return nut


## Open wide and snap shut, once (about half a second). If it holds a whole walnut, the walnut cracks
## as the jaw comes down: `holds` becomes CRACKED_WALNUT and `cracked` is sent. `clacked` is sent as
## the teeth meet either way.
func crack() -> void:
	_crack_at = 0.0
	_crack_done = false
	set_process(true)


## Salute once: the right arm snaps up, holds a second and comes down (for a salute that stays, set
## `motion` to SALUTE). The king raises his sceptre, the guard his sword, the baker his rolling pin,
## the drummer a stick.
func salute() -> void:
	_salute_at = 0.0
	set_process(true)


## Something has knocked it: it rocks on its plinth away from the knock and back, rattling, its arms
## swinging and its jaw chattering, and settles in about a second and a half. `direction` is the way the
## knock pushes it, in the world (only its level part counts); `strength` 1 is a firm nudge that tips it
## about nine degrees, 2 nearly has it over. It never falls.
func bump(direction: Vector3, strength := 1.0) -> void:
	var local := global_basis.inverse() * direction
	var way := Vector2(local.x, local.z)
	if way.length() < 0.0001:
		way = Vector2(0.0, -1.0)
	_wobble_way = way.normalized()
	_wobble_size = clampf(strength, 0.0, 2.2) * 9.0
	_wobble_at = 0.0
	set_process(true)


## Whether a crack(), a salute() or a bump() is still playing.
func is_busy() -> bool:
	return _crack_at >= 0.0 or _salute_at >= 0.0 or _wobble_at >= 0.0


## Where it stands, for games that keep the player out with simple shapes, in the world:
## `centre` (the middle of the plinth's foot), `radius` (a circle that holds the plinth), `height` (the
## top of its hat), `wide` (a circle that holds all of it as it stands: arms, drum, sword) and `round`
## (always true, so it can be mixed with the presents component's footprints). Ask again if it moves.
func footprint() -> Dictionary:
	var model := _model if not _model.is_empty() else _prepared(NAMES[kind] + ("_lo" if low_detail else ""))
	var unit := size * global_basis.get_scale().y if is_inside_tree() else size
	return {
		"centre": global_position if is_inside_tree() else position,
		"radius": float(model["radius"]) * unit,
		"height": float(model["height"]) * unit,
		"wide": float(model["wide"]) * unit,
		"round": true,
	}


## Whether a point (a player `margin` wide) is inside a footprint, below its top.
static func blocks(print_: Dictionary, point: Vector3, margin := 0.0) -> bool:
	var centre: Vector3 = print_["centre"]
	if point.y > centre.y + float(print_["height"]):
		return false
	return Vector2(point.x - centre.x, point.z - centre.z).length() < float(print_["radius"]) + margin


## The point moved out of a footprint, if it was in it: call after moving the player.
static func push_out(print_: Dictionary, point: Vector3, margin := 0.0) -> Vector3:
	if not blocks(print_, point, margin):
		return point
	var centre: Vector3 = print_["centre"]
	var away := Vector2(point.x - centre.x, point.z - centre.z)
	if away.length() < 0.00001:
		away = Vector2(0.0, 1.0)
	away = away.normalized() * (float(print_["radius"]) + margin)
	return Vector3(centre.x + away.x, point.y, centre.z + away.y)


## Where the middle of its mouth is in the world: for a sound, or a walnut flying out.
func mouth_position() -> Vector3:
	if _rocker == null or _model.is_empty():
		return global_position
	return _rocker.global_transform * (_model["marks"]["mouth"] as Vector3)


## How many triangles are being drawn for it (and what it holds).
func triangles() -> int:
	var total := 0
	if not _model.is_empty():
		total = int(_model["triangles"])
	if _held != null:
		for child in _held.get_children():
			total += (child as MeshInstance3D).mesh.surface_get_array_index_len(0) / 3
	return total


## The one material every nutcracker and walnut is drawn with. Its `gloss` (0 matt .. 1 as painted) and
## `bare_wood` (the colour under chipped paint) can be set for the whole game.
static func material() -> ShaderMaterial:
	if _material == null:
		_material = ShaderMaterial.new()
		_material.shader = SHADER
		_material.set_shader_parameter(&"paint", PAINT)
		_material.set_shader_parameter(&"masks", MASKS)
	return _material


## Forget the prepared meshes (after the models are rebuilt while the game runs).
static func clear_cache() -> void:
	_library.clear()
	_sources.clear()


func _ready() -> void:
	_build()


func _process(delta: float) -> void:
	if _figure == null:
		return
	delta = minf(delta, 0.05)
	var tempo := clampf(0.55 + 0.45 * liveliness, 0.2, 2.0)
	var reach := clampf(liveliness, 0.0, 1.6)
	_time += delta * tempo
	var limits: Array = ARM_RANGE[kind]
	var want_jaw := _hold_angle if holds != Holds.NOTHING else maxf(jaw_open * JAW_MAX, _ajar)
	var snap_jaw := false
	var want_r := _rest_r
	var want_l := _rest_l
	var want_lean := 0.0
	var rock := Vector2.ZERO          # which way its top leans, degrees
	var busy := false
	match motion:
		Motion.CLACK:
			busy = true
			var f := fposmod(_time / 0.8, 1.0)
			if holds == Holds.NOTHING:
				want_jaw = JAW_MAX * 0.8 * minf(reach, 1.25) / 1.25 * (_ease(f / 0.72) if f < 0.72 else 0.0)
				snap_jaw = true
				if f < _last_clack:
					pass
				elif _last_clack < 0.72 and f >= 0.72:
					clacked.emit()
			_last_clack = f
		Motion.MARCH:
			busy = true
			var wave := sin(_time * TAU / 0.9)
			var stiff := signf(wave) * pow(absf(wave), 0.6)
			rock.x = 4.0 * reach * stiff
			var swing: Array = MARCH_SWING[kind]
			if kind == Kind.DRUMMER:      # he drums as he marches: the sticks only go up
				want_r = -float(swing[0]) * reach * maxf(stiff, 0.0)
				want_l = -float(swing[1]) * reach * maxf(-stiff, 0.0)
			else:
				want_r += float(swing[0]) * reach * stiff
				want_l -= float(swing[1]) * reach * stiff
			if signf(wave) != signf(_last_wave) and _last_wave != 0.0:
				stepped.emit()
				if kind == Kind.DRUMMER:
					drummed.emit(wave < 0.0)
			_last_wave = wave
		Motion.DRUM:
			busy = true
			var wave := sin(_time * TAU / 0.36)
			var rise: Array = DRUM_RISE[kind]
			want_r = -float(rise[0]) * minf(reach, 1.3) * pow(maxf(wave, 0.0), 0.7)
			want_l = -float(rise[1]) * minf(reach, 1.3) * pow(maxf(-wave, 0.0), 0.7)
			if signf(wave) != signf(_last_wave) and _last_wave != 0.0:
				drummed.emit(wave < 0.0)
			_last_wave = wave
		Motion.SALUTE:
			want_r = SALUTES[kind].x
			want_lean = SALUTES[kind].y
	if _salute_at >= 0.0:
		busy = true
		_salute_at += delta
		var up := 1.0
		if _salute_at > 1.25:
			up = 1.0 - _ease((_salute_at - 1.25) / 0.3)
		if _salute_at >= 1.55:
			_salute_at = -1.0
		else:
			want_r = lerpf(want_r, SALUTES[kind].x, up)
			want_lean = lerpf(want_lean, SALUTES[kind].y, up)
	if _crack_at >= 0.0:
		busy = true
		_crack_at += delta
		var shut := _hold_angle if holds == Holds.WALNUT else want_jaw
		if holds != Holds.NOTHING and _crack_done:
			shut = _hold_angle
		snap_jaw = true
		if _crack_at < 0.22:
			want_jaw = lerpf(_jaw, JAW_MAX, _ease(_crack_at / 0.22))
		elif _crack_at < 0.36:
			want_jaw = JAW_MAX
		elif _crack_at < 0.4:
			want_jaw = lerpf(JAW_MAX, shut, (_crack_at - 0.36) / 0.04)
		else:
			if not _crack_done:
				_crack_done = true
				clacked.emit()
				if holds == Holds.WALNUT:
					holds = Holds.CRACKED_WALNUT
					cracked.emit()
			want_jaw = shut
			if _crack_at >= 0.55:
				_crack_at = -1.0
	if _wobble_at >= 0.0:
		busy = true
		_wobble_at += delta
		var fade := exp(-2.6 * _wobble_at)
		var swing := cos(_wobble_at * TAU * (3.2 + 1.5 * _wobble_at))
		rock += _wobble_way * _wobble_size * fade * swing
		# loose parts carry on: the arms swing against the rock, the jaw chatters
		var jostle := _wobble_size * 1.6 * fade * sin(_wobble_at * TAU * 4.3)
		want_r += jostle
		want_l -= jostle * 0.8
		if holds == Holds.NOTHING:
			want_jaw = maxf(want_jaw, minf(_wobble_size * 0.9 * fade * absf(sin(_wobble_at * TAU * 6.5)), JAW_MAX))
			snap_jaw = true
		if _wobble_at > 1.7:
			_wobble_at = -1.0
			clacked.emit()
	want_r = clampf(want_r, float(limits[0]), float(limits[1]))
	want_l = clampf(want_l, float(limits[2]), float(limits[3]))
	want_jaw = clampf(want_jaw, 0.0, JAW_MAX)
	# a toy's joints: stiff, quick, no easing
	var quick := 900.0 * delta * maxf(tempo, 0.6)
	_arm_r = move_toward(_arm_r, want_r, quick)
	_arm_l = move_toward(_arm_l, want_l, quick)
	_lean_r = move_toward(_lean_r, want_lean, quick * 0.2)
	_jaw = want_jaw if snap_jaw else move_toward(_jaw, want_jaw, 160.0 * delta)
	_pose()
	_rock(rock)
	if not busy and _arm_r == want_r and _arm_l == want_l and _jaw == want_jaw and _lean_r == want_lean:
		set_process(false)


static func _ease(t: float) -> float:
	t = clampf(t, 0.0, 1.0)
	return 1.0 - (1.0 - t) * (1.0 - t)


# ------------------------------------------------------------------ drawing it
## Send the pose to the shader (three numbers of this figure's own).
func _pose() -> void:
	if _figure == null:
		return
	var hat := _colours()[2]
	_figure.set_instance_shader_parameter(&"tint_hat", Color(hat.r, hat.g, hat.b, deg_to_rad(_jaw)))
	# the right arm leans in about the forward axis one way, the left the other
	var right := Basis(Vector3.BACK, deg_to_rad(-_lean_r)) * Basis(Vector3.RIGHT, deg_to_rad(_arm_r))
	var q := right.get_rotation_quaternion()
	_figure.set_instance_shader_parameter(&"turn_right", Vector4(q.x, q.y, q.z, q.w))
	q = Quaternion(Vector3.RIGHT, deg_to_rad(_arm_l))
	_figure.set_instance_shader_parameter(&"turn_left", Vector4(q.x, q.y, q.z, q.w))


## Lean it `lean` degrees (x, z: the way its top goes), turning about the edge of the plinth on that
## side so its foot never goes through the table.
func _rock(lean: Vector2) -> void:
	if _rocker == null:
		return
	var angle := deg_to_rad(lean.length())
	if angle < 0.00001:
		_rocker.transform = Transform3D.IDENTITY
		return
	var way := lean.normalized()
	var edge := Vector3(way.x, 0.0, way.y) * float(_model["foot"])
	var turn := Basis(Vector3(way.y, 0.0, -way.x), angle)
	_rocker.transform = Transform3D(turn, edge - turn * edge)


## The six colours it wears: coat, trousers, hat, trim, hair, skin.
func _colours() -> Array[Color]:
	var six: Array[Color] = []
	if palette == Palette.CUSTOM:
		six = [coat_colour, trousers_colour, hat_colour, trim_colour, hair_colour, skin_colour]
	else:
		six.assign(PALETTES[palette])
	return six


func _paint() -> void:
	if _figure == null:
		return
	var six := _colours()
	_figure.set_instance_shader_parameter(&"tint_coat", Color(six[0].r, six[0].g, six[0].b, wear * _wear_own()))
	_figure.set_instance_shader_parameter(&"tint_trousers", Color(six[1].r, six[1].g, six[1].b, _chips))
	_figure.set_instance_shader_parameter(&"tint_trim", Color(six[3].r, six[3].g, six[3].b, deg_to_rad(_tash)))
	_figure.set_instance_shader_parameter(&"tint_hair", Color(six[4].r, six[4].g, six[4].b, 0.0))
	_figure.set_instance_shader_parameter(&"tint_skin", Color(six[5].r, six[5].g, six[5].b, 0.0))
	_pose()


func _wear_own() -> float:
	return 0.75 + 0.5 * fposmod(_chips * 3.7, 1.0)


func _build() -> void:
	_queued = false
	if not is_inside_tree():
		return
	if _body != null:
		_body.queue_free()
		remove_child(_body)
	_held = null
	_model = _prepared(NAMES[kind] + ("_lo" if low_detail else ""))
	_rng.seed = seed if seed != 0 else int(get_instance_id()) * 7919 + 13
	_chips = _rng.randf()
	_tash = _rng.randf_range(-TASH_TILT, TASH_TILT)
	var limits: Array = ARM_RANGE[kind]
	_rest_r = clampf(_rng.randf_range(-3.0, 3.0), float(limits[0]), float(limits[1]))
	_rest_l = clampf(_rng.randf_range(-3.0, 3.0), float(limits[2]), float(limits[3]))
	_ajar = maxf(_rng.randf_range(-1.5, 1.2), 0.0)
	_time = _rng.randf_range(0.0, 20.0)
	_body = Node3D.new()
	_body.name = "Body"
	_body.scale = Vector3.ONE * size
	add_child(_body)
	_rocker = Node3D.new()
	_rocker.name = "Rocker"
	_body.add_child(_rocker)
	_figure = MeshInstance3D.new()
	_figure.name = "Figure"
	_figure.mesh = _model["mesh"]
	_figure.material_override = material()
	_figure.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if shadows \
			else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_rocker.add_child(_figure)
	_hold()
	_arm_r = _rest_r
	_arm_l = _rest_l
	_lean_r = 0.0
	_jaw = _hold_angle if holds != Holds.NOTHING else maxf(jaw_open * JAW_MAX, _ajar)
	_paint()
	set_process(true)


## Put what it holds between its teeth, and work out how far the jaw rests open on it.
func _hold() -> void:
	if _rocker == null:
		return
	if _held != null:
		_held.queue_free()
		_rocker.remove_child(_held)
		_held = null
	_hold_angle = 0.0
	if holds == Holds.NOTHING:
		return
	var marks: Dictionary = _model["marks"]
	var mouth: Vector3 = marks["mouth"]
	var top: Vector3 = marks["jawtop"]
	var pivot: Vector3 = marks["jaw"]
	# a nut to suit the head (the mouth mark is 0.8 of the head's radius out), held at the front of
	# the mouth between the two rows of teeth, half of it showing
	var head := mouth.z / 0.8
	var r := head * 0.25
	var centre := Vector3(0.0, mouth.y - r - 0.0004, head * 0.97)
	# the angle at which the jaw's top face comes up under the nut
	var low := 0.0
	var high := deg_to_rad(JAW_MAX)
	for i in 18:
		var mid := (low + high) * 0.5
		var c := cos(mid)
		var s := sin(mid)
		var rel := top - pivot
		var moved := pivot + Vector3(rel.x, rel.y * c - rel.z * s, rel.y * s + rel.z * c)
		var gap := (centre - moved).dot(Vector3(0.0, c, s))
		if gap < r:
			low = mid
		else:
			high = mid
	_hold_angle = rad_to_deg(high)
	_held = Node3D.new()
	_held.name = "Held"
	_rocker.add_child(_held)
	var tail := "_lo" if low_detail else ""
	var k := r / 0.0118
	if holds == Holds.WALNUT:
		var whole := _nut_part("walnut_whole" + tail)
		# on its side, its seam level
		whole.transform = Transform3D(Basis(Vector3.FORWARD, PI * 0.5).scaled(Vector3.ONE * k), centre + Vector3(-0.0135 * k, 0.0, 0.0))
		_held.add_child(whole)
	else:
		# the lower half on the bottom teeth, kernel up; the upper half tipped forward off it
		var lower := _nut_part("walnut_half_a" + tail)
		lower.transform = Transform3D(Basis(Vector3.FORWARD, PI * 0.5).scaled(Vector3.ONE * k),
				centre + Vector3(-0.0135 * k, -0.1 * r, 0.0))
		_held.add_child(lower)
		var upper := _nut_part("walnut_half_b" + tail)
		var tipped := Basis(Vector3.RIGHT, 0.5) * Basis(Vector3.FORWARD, PI * 0.5)
		upper.transform = Transform3D(tipped.scaled(Vector3.ONE * k), centre + tipped * Vector3(0.0, 0.0135 * k, 0.0) * -1.0
				+ Vector3(0.0, 0.05 * r, 0.75 * r))
		_held.add_child(upper)
	for child in _held.get_children():
		(child as MeshInstance3D).cast_shadow = _figure.cast_shadow


static func _nut_part(title: String) -> MeshInstance3D:
	var part := MeshInstance3D.new()
	part.name = title
	part.mesh = _prepared(title)["mesh"]
	part.material_override = material()
	return part


func _rebuild() -> void:
	if is_inside_tree() and not _queued:
		_queued = true
		_build.call_deferred()


# ------------------------------------------------------------------ what figures share
## A model from the .glb, made ready once: its mesh with each point's pivot, part, colour and wear put
## where the shader reads them (the .glb carries them in a second UV set and in empties), its marks,
## and how big it is. {"mesh", "marks", "radius", "foot", "wide", "height", "triangles"}
static func _prepared(title: String) -> Dictionary:
	if _library.has(title):
		return _library[title]
	if _sources.is_empty():
		var scene: Node = (MODELS as PackedScene).instantiate()
		for top in scene.get_children():
			var found := {"marks": {}}
			for child in top.get_children():
				if child is MeshInstance3D:
					found["mesh"] = (child as MeshInstance3D).mesh
				elif child is Node3D:
					found["marks"][String(child.name).trim_prefix(String(top.name) + "_")] = (child as Node3D).position
			_sources[String(top.name)] = found
		scene.free()
	var marks: Dictionary = _sources[title]["marks"]
	var source: Mesh = _sources[title]["mesh"]
	var arrays := source.surface_get_arrays(0)
	var points: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var codes: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV2]
	var pivots: Array[Vector3] = [Vector3.ZERO, marks.get("jaw", Vector3.ZERO), marks.get("armr", Vector3.ZERO),
			marks.get("arml", Vector3.ZERO), marks.get("tash", Vector3.ZERO), marks.get("jaw", Vector3.ZERO)]
	var hang: Vector3 = marks.get("jawtop", Vector3.ZERO) - marks.get("jaw", Vector3.ZERO)
	var custom0 := PackedFloat32Array()
	var custom1 := PackedFloat32Array()
	custom0.resize(points.size() * 4)
	custom1.resize(points.size() * 4)
	var radius := 0.0
	var foot_x := 0.0
	var foot_z := 0.0
	var wide := 0.0
	var height := 0.0
	for i in points.size():
		var part := clampi(int(floor(codes[i].x * 8.0)), 0, 5)
		var packed := codes[i].y * 8.0
		var zone := clampf(floor(packed), 0.0, 6.0)
		var chips := clampf((packed - zone - 0.05) / 0.9, 0.0, 1.0)
		var pivot := pivots[part]
		custom0[i * 4] = pivot.x
		custom0[i * 4 + 1] = pivot.y
		custom0[i * 4 + 2] = pivot.z
		custom0[i * 4 + 3] = float(part)
		custom1[i * 4] = zone
		custom1[i * 4 + 1] = chips
		custom1[i * 4 + 2] = hang.y
		custom1[i * 4 + 3] = hang.z
		var p := points[i]
		var out := Vector2(p.x, p.z).length()
		wide = maxf(wide, out)
		height = maxf(height, p.y)
		if part == 0 and p.y < 0.012:      # the plinth's foot
			radius = maxf(radius, out)
			foot_x = maxf(foot_x, absf(p.x))
			foot_z = maxf(foot_z, absf(p.z))
	var made := ArrayMesh.new()
	var fresh := []
	fresh.resize(Mesh.ARRAY_MAX)
	fresh[Mesh.ARRAY_VERTEX] = points
	fresh[Mesh.ARRAY_NORMAL] = arrays[Mesh.ARRAY_NORMAL]
	fresh[Mesh.ARRAY_TEX_UV] = arrays[Mesh.ARRAY_TEX_UV]
	fresh[Mesh.ARRAY_CUSTOM0] = custom0
	fresh[Mesh.ARRAY_CUSTOM1] = custom1
	fresh[Mesh.ARRAY_INDEX] = arrays[Mesh.ARRAY_INDEX]
	var format := (Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT) \
			| (Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM1_SHIFT)
	made.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, fresh, [], {}, format)
	# the arms swing out of the mesh's own box: one that holds every pose
	var box := made.get_aabb().grow(0.0)
	var arm := 0.2
	made.custom_aabb = AABB(Vector3(-wide - 0.05, 0.0, -arm), Vector3(2.0 * wide + 0.1, maxf(height, box.size.y) + 0.08, 2.0 * arm)) \
			if marks.has("armr") else box
	var entry := {"mesh": made, "marks": marks, "radius": radius, "foot": minf(foot_x, foot_z), "wide": wide,
			"height": height, "triangles": (arrays[Mesh.ARRAY_INDEX] as PackedInt32Array).size() / 3}
	_library[title] = entry
	return entry


# ------------------------------------------------------------------ settings
func _set_kind(value: Kind) -> void:
	kind = value
	_rebuild()


func _set_palette(value: Palette) -> void:
	palette = value
	_paint()


func _set_size(value: float) -> void:
	size = maxf(value, 0.0001)
	if _body != null:
		_body.scale = Vector3.ONE * size


func _set_low_detail(value: bool) -> void:
	low_detail = value
	_rebuild()


func _set_seed(value: int) -> void:
	seed = value
	_rebuild()


func _set_wear(value: float) -> void:
	wear = maxf(value, 0.0)
	_paint()


func _set_holds(value: Holds) -> void:
	holds = value
	_hold()
	set_process(true)


func _set_motion(value: Motion) -> void:
	motion = value
	_last_wave = 0.0
	_last_clack = 0.0
	set_process(true)


func _set_jaw_open(value: float) -> void:
	jaw_open = clampf(value, 0.0, 1.0)
	set_process(true)


func _set_shadows(value: bool) -> void:
	shadows = value
	_rebuild()


func _set_coat(value: Color) -> void:
	coat_colour = value
	_paint()


func _set_trousers(value: Color) -> void:
	trousers_colour = value
	_paint()


func _set_hat(value: Color) -> void:
	hat_colour = value
	_paint()


func _set_trim(value: Color) -> void:
	trim_colour = value
	_paint()


func _set_hair(value: Color) -> void:
	hair_colour = value
	_paint()


func _set_skin(value: Color) -> void:
	skin_colour = value
	_paint()
