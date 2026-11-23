class_name GingerbreadVillage
extends Node3D
## A little gingerbread village: several houses of mixed kinds along a lane on one snowy board, with
## stepping stones, a fence along the front, iced trees, gingerbread people and a snowman, all from a
## seed. The whole village is one mesh and one draw (see `merged`).
##
## Its origin is the middle of the underside of its board; the lane runs along x and the houses
## face +z across it. Sizes are metres: set `size` for a game with another unit.
##
##   var place := GingerbreadHouse.village(5, GingerbreadHouse.Palette.CLASSIC, 3, 12.5)
##   add_child(place)
##   var keep_out := place.wall_footprints()      # after it is in the tree

## How many houses. 1 to 12; the default 5 is about 90 cm of lane.
@export_range(1, 12) var count := 5: set = _set_count
## Which kinds may be dealt (GingerbreadHouse.Kind numbers); empty for all six. No two neighbours
## are alike if it can be helped, and there is one church at most.
@export var kinds: Array[int] = []: set = _set_kinds
## The colours of the icing and sweets, for every house. Default CLASSIC.
@export var palette := GingerbreadHouse.Palette.CLASSIC: set = _set_palette
## How heavily the houses and the board are decorated: 0 bare slabs on a bare board, 0.6 (the
## default) as a keen family would, 1 encrusted and crowded.
@export_range(0.0, 1.0, 0.01) var decoration := 0.6: set = _set_decoration
## How much snow on the roofs and in drifts: 0 only the dusting on the board, 0.4 (the default) caps
## on the roofs, 1 buried.
@export_range(0.0, 1.0, 0.01) var snow := 0.4: set = _set_snow
## How big: 1 for a game in metres, 12.5 for a unit of 8 cm.
@export_range(0.01, 100.0, 0.01, "or_greater") var size := 1.0: set = _set_size
## The same settings and seed give the same village. Default 1.
@export var seed := 1: set = _set_seed
## How far apart the houses stand, in metres at size 1: 0 shoulder to shoulder, 0.03 (the default)
## room for a tree between, 0.15 scattered.
@export_range(0.0, 0.3, 0.001, "or_greater") var spacing := 0.03: set = _set_spacing
## Houses on both sides of the lane, facing each other, in place of one row with the lane in front.
@export var both_sides := false: set = _set_both_sides
## The low models and fewer sweets: for a village that is small on screen. Default off.
@export var low_detail := false: set = _set_low_detail
## Whether the houses are lit from inside (painted light: panes, inner walls, the snow at each door).
@export var windows_glow := true: set = _set_windows_glow
## How bright that glow is drawn: 0.4 embers, 1 (the default) candlelight, 2.5 blazing.
@export_range(0.0, 3.0, 0.01) var glow_strength := 1.0: set = _set_glow_strength
## How many of the houses get a real light inside as well (an OmniLight3D each), from the middle of
## the lane outwards. 0 by default: the painted glow is free, each real light is not.
@export_range(0, 12) var lights_inside := 0: set = _set_lights_inside
## How strong each of those lights is at size 1 (multiplied by `size`). 0.15 (the default) is a candle.
@export_range(0.0, 4.0, 0.01, "or_greater") var light_energy := 0.15: set = _set_light_energy
## How ajar the doors stand: 0 shut, 0.35 (the default) ajar, 1 wide open. Each differs a little.
@export_range(0.0, 1.0, 0.01) var door_ajar := 0.35: set = _set_door_ajar
## One mesh and one draw for the whole village. Off: the board and what stands on it are one mesh
## and each house is a GingerbreadHouse node of its own (a draw each), for a game that changes one
## house at a time. Default on.
@export var merged := true: set = _set_merged
## For Palette.CUSTOM: the gingerbread, the icing, and the colours the sweets are dealt from.
@export var custom_bread := GingerbreadHouse.BREAD: set = _set_custom_bread
@export var custom_icing := GingerbreadHouse.WHITE: set = _set_custom_icing
@export var custom_sweets := PackedColorArray([GingerbreadHouse.RED, GingerbreadHouse.GREEN, GingerbreadHouse.GOLD]): set = _set_custom_sweets
## Whether it casts a shadow. Default on.
@export var shadows := true: set = _set_shadows

var _instance: MeshInstance3D
var _plans: Array[Dictionary] = []
var _board := {}
var _lamps: Array[OmniLight3D] = []
var _nodes: Array[GingerbreadHouse] = []
var _queued := false
var _planned := false
var _clock := 0.0


## What was dealt, in the village's own space at size 1: for each house {kind, spec (its settings),
## place: Transform3D (where its own space is), box: {centre: Vector3, half: Vector2, turn}}.
func houses() -> Array[Dictionary]:
	_plan()
	return _plans


## Where a house's own space is in the world (the frame that GingerbreadHouse's *_at helpers take).
func house_frame(index: int) -> Transform3D:
	_plan()
	return global_transform * Transform3D(Basis.from_scale(Vector3.ONE * size), Vector3.ZERO) * (_plans[index]["place"] as Transform3D)


## One box round each house, in the world (see GingerbreadHouse.footprint() for what is in it).
func footprints() -> Array[Dictionary]:
	_plan()
	var out: Array[Dictionary] = []
	for i in _plans.size():
		out.append(GingerbreadHouse.print_at(GingerbreadHouse.notes(_plans[i]["kind"])["box"], house_frame(i)))
	return out


## A thin box for each length of every house's walls, the doorways left open: keep a small walker
## out of these and it can go in at any door.
func wall_footprints() -> Array[Dictionary]:
	_plan()
	var out: Array[Dictionary] = []
	for i in _plans.size():
		out.append_array(GingerbreadHouse.wall_prints_at(_plans[i]["kind"], house_frame(i)))
	return out


## Every house's doorway, in the world, in the order of houses() (see GingerbreadHouse.doorway()).
func doorways() -> Array[Dictionary]:
	_plan()
	var out: Array[Dictionary] = []
	for i in _plans.size():
		out.append(GingerbreadHouse.doorways_at(_plans[i]["kind"], house_frame(i))[0])
	return out


## Every window of every house, in the world (see GingerbreadHouse.windows()).
func windows() -> Array[Dictionary]:
	_plan()
	var out: Array[Dictionary] = []
	for i in _plans.size():
		out.append_array(GingerbreadHouse.windows_at(_plans[i]["kind"], house_frame(i)))
	return out


## Where the light inside each house is, in the world, in the order of houses().
func light_positions() -> Array[Vector3]:
	_plan()
	var out: Array[Vector3] = []
	for i in _plans.size():
		out.append(house_frame(i) * GingerbreadHouse._vec(GingerbreadHouse.notes(_plans[i]["kind"])["light"]))
	return out


## The board's footprint, in the world (the same Dictionary as a house's; height is its thickness).
func board_footprint() -> Dictionary:
	_plan()
	return GingerbreadHouse.print_at(_board, global_transform * Transform3D(Basis.from_scale(Vector3.ONE * size), Vector3.ZERO))


## Whether a point is in any house's walls, grown by `margin`.
func blocks(point: Vector3, margin := 0.0) -> bool:
	for print_ in wall_footprints():
		if GingerbreadHouse.blocks(print_, point, margin):
			return true
	return false


## A point moved out of every house's walls.
func push_out(point: Vector3, margin := 0.0) -> Vector3:
	var prints := wall_footprints()
	for _pass in 2:
		for print_ in prints:
			point = GingerbreadHouse.push_out(print_, point, margin)
	return point


## How many triangles the village is drawn with.
func triangles() -> int:
	var total := 0
	if _instance != null and _instance.mesh != null:
		total += _instance.mesh.surface_get_array_index_len(0) / 3
	for house in _nodes:
		total += house.triangles()
	return total


func _ready() -> void:
	_build()


func _process(delta: float) -> void:
	_clock += delta
	for i in _lamps.size():
		var quiver := sin(_clock * 7.3 + i * 2.1) * 0.5 + sin(_clock * 12.7 + i * 1.3) * 0.3 + sin(_clock * 2.9 + i * 4.7) * 0.4
		_lamps[i].light_energy = light_energy * size * (1.0 + 0.13 * quiver)


## Deals the houses and sets them out (at size 1, in the village's own space).
func _plan() -> void:
	if _planned:
		return
	_planned = true
	_plans.clear()
	var rng := RandomNumberGenerator.new()
	rng.seed = seed * 104729 + 13
	var allowed: Array[int] = []
	for k in kinds:
		if k >= 0 and k < GingerbreadHouse.KIND_NAMES.size() and not allowed.has(k):
			allowed.append(k)
	if allowed.is_empty():
		allowed = [0, 1, 2, 3, 4, 5]
	var deck: Array[int] = []
	var dealt: Array[int] = []
	var church_used := false
	for i in count:
		if deck.is_empty():
			deck = allowed.duplicate()
			for a in range(deck.size() - 1, 0, -1):
				var b := rng.randi() % (a + 1)
				var held := deck[a]
				deck[a] = deck[b]
				deck[b] = held
		var pick := deck.size() - 1
		for attempt in deck.size():
			var k := deck[pick]
			var repeats := not dealt.is_empty() and dealt[dealt.size() - 1] == k
			var second_church := k == GingerbreadHouse.Kind.CHURCH and church_used
			if (repeats or second_church) and allowed.size() > 1:
				pick = (pick + deck.size() - 1) % deck.size()
			else:
				break
		var chosen := deck[pick]
		deck.remove_at(pick)
		if chosen == GingerbreadHouse.Kind.CHURCH:
			church_used = true
		dealt.append(chosen)
	var lane := 0.035       # half the lane's width
	var cursor := [0.0, 0.0]    # how far along x each row has got
	var lo := Vector2(1e9, 1e9)
	var hi := Vector2(-1e9, -1e9)
	for i in count:
		var row := (i % 2) if both_sides else 0
		var note: Dictionary = GingerbreadHouse.notes(dealt[i])
		var box: Dictionary = note["box"]
		var c: Array = box["centre"]
		var h: Array = box["half"]
		var half := Vector2(h[0], h[1])
		var turn := rng.randf_range(-0.12, 0.12) + (PI if row == 1 else 0.0)
		var reach := half.x * absf(cos(turn)) + half.y * absf(sin(turn)) + 0.004
		var gap := spacing * rng.randf_range(0.7, 1.4) if cursor[row] > 0.0 else 0.0
		var x: float = cursor[row] + gap + reach
		cursor[row] = x + reach
		# its front (its own +z, counted from the middle of its box) stands back from the lane
		var front := lane + rng.randf_range(0.03, 0.05) + half.y
		var middle := Vector3(x, 0.0, -front if row == 0 else front)
		var basis := Basis(Vector3.UP, turn)
		var origin := middle - basis * Vector3(c[0], 0.0, c[2])
		var spec := {
			"kind": dealt[i], "palette": palette, "decoration": decoration, "snow": snow, "low_detail": low_detail,
			"seed": seed * 31 + i * 7 + 1, "glow": glow_strength if windows_glow else 0.0, "flicker": 1.0,
			"door": true, "door_ajar": clampf(door_ajar * rng.randf_range(0.6, 1.5), 0.0, 1.0), "board": false, "yard": false, "sunk": false,
			"spill": true, "snow_origin": Vector3.ZERO, "custom_bread": custom_bread, "custom_icing": custom_icing, "custom_sweets": custom_sweets,
		}
		_plans.append({"kind": dealt[i], "spec": spec, "place": Transform3D(basis, origin), "middle": middle, "half": half, "turn": turn, "row": row})
		var spread := Vector2(reach, half.y * absf(cos(turn)) + half.x * absf(sin(turn)))
		lo = lo.min(Vector2(middle.x, middle.z) - spread)
		hi = hi.max(Vector2(middle.x, middle.z) + spread)
	# centre the village on its own origin, and size the board round it
	if not both_sides:
		hi.y = maxf(hi.y, lane + 0.085)
	lo -= Vector2(0.04, 0.03)
	hi += Vector2(0.04, 0.03)
	var shift := Vector3((lo.x + hi.x) * 0.5, 0.0, (lo.y + hi.y) * 0.5)
	for plan in _plans:
		var place: Transform3D = plan["place"]
		plan["place"] = Transform3D(place.basis, place.origin - shift)
		plan["middle"] = (plan["middle"] as Vector3) - shift
	_board = {"centre": [0.0, 0.0, 0.0], "half": [(hi.x - lo.x) * 0.5, (hi.y - lo.y) * 0.5],
			"height": float((GingerbreadHouse.MANIFEST.data as Dictionary)["board_thick"]), "lane": -shift.z}


func _build() -> void:
	_queued = false
	if not is_inside_tree():
		return
	_planned = false
	_plan()
	for house in _nodes:
		house.queue_free()
		remove_child(house)
	_nodes.clear()
	for lamp in _lamps:
		lamp.queue_free()
		remove_child(lamp)
	_lamps.clear()
	if _instance == null:
		_instance = MeshInstance3D.new()
		_instance.name = "Mesh"
		add_child(_instance)
	var thick: float = _board["height"]
	var half := Vector2(_board["half"][0], _board["half"][1])
	var lane_z: float = _board["lane"]
	var batch := GingerbreadHouse.Batch.new()
	var whole := Transform3D(Basis.from_scale(Vector3.ONE * size), Vector3.ZERO)
	var work := GingerbreadHouse.Dresser.new()
	work.batch = batch
	work.low = low_detail
	work.look = GingerbreadHouse.colours(palette, {"custom_bread": custom_bread, "custom_icing": custom_icing, "custom_sweets": custom_sweets})
	work.unit = size
	work.glow = 0.0
	work.rng = RandomNumberGenerator.new()
	work.rng.seed = seed * 7129 + 5
	work.root = whole
	work.flat_origin = Vector3.ZERO
	work.piece("village_board", Transform3D(Basis.from_scale(Vector3(half.x * 2.0, 1.0, half.y * 2.0)), Vector3.ZERO))
	var rng := work.rng
	var floor_y := Vector3(0.0, thick, 0.0)
	var white: Color = work.look["icing"]
	# the lane: stepping stones from one end of the board to the other
	if decoration >= 0.15:
		var steps := int((half.x * 2.0 - 0.05) / 0.03)
		for i in steps:
			var x := -half.x + 0.035 + i * 0.03
			var z := lane_z + 0.009 * sin(i * 0.9) + rng.randf_range(-0.003, 0.003)
			var chocolate := i % 2 == 0
			var inks := [GingerbreadHouse.CHOCOLATE, Color(0.62, 0.4, 0.22), white] if chocolate else [work.look["wafer"], white, work.look["accent"]]
			work.piece("disc", GingerbreadHouse.Dresser.on(Vector3(x, thick, z), Vector3.UP, Vector3.RIGHT, Vector3(0.95, 0.55, 0.95), rng.randf() * TAU),
					{"ink": inks, "uv_shift": Vector2(0.0 if chocolate else 0.5, 0.5)})
	# from each door to the lane
	var taken: Array = []       # circles already used: Vector3(x, z, radius)
	for i in _plans.size():
		var plan := _plans[i]
		var frame: Transform3D = plan["place"]
		var door: Dictionary = GingerbreadHouse.notes(plan["kind"])["doors"][0]
		var at := frame * GingerbreadHouse._vec(door["c"])
		var out := (frame.basis * GingerbreadHouse._vec(door["n"])).normalized()
		var far := absf(at.z - lane_z) - 0.02
		var stones := int(far / 0.026)
		for k in stones:
			var p := at + out * (0.02 + k * 0.026)
			taken.append(Vector3(p.x, p.z, 0.016))
			if decoration >= 0.25:
				work.piece("disc", GingerbreadHouse.Dresser.on(Vector3(p.x, thick, p.z), Vector3.UP, Vector3.RIGHT, Vector3(0.8, 0.5, 0.8), rng.randf() * TAU),
						{"ink": [work.look["wafer"], white, work.look["accent"]], "uv_shift": Vector2(0.5, 0.5)})
		taken.append(Vector3(at.x + out.x * 0.02, at.z + out.z * 0.02, 0.03))
		var m: Vector3 = plan["middle"]
		var hb: Vector2 = plan["half"]
		taken.append(Vector3(m.x, m.z, maxf(hb.x, hb.y) * 1.05))
		taken.append(Vector3(m.x - hb.x * 0.5, m.z, hb.y * 1.05))
		taken.append(Vector3(m.x + hb.x * 0.5, m.z, hb.y * 1.05))
	# what stands about: trees, people, a snowman, lollipops, drifts
	var wanted := int(round(lerpf(0.0, 3.0 + _plans.size() * 2.2, clampf((decoration - 0.2) / 0.8, 0.0, 1.0))))
	var snowman_done := false
	var tries := 0
	while wanted > 0 and tries < 400:
		tries += 1
		var r := rng.randf_range(0.013, 0.022)
		var p := Vector3(rng.randf_range(-half.x + 0.03, half.x - 0.03), thick, rng.randf_range(-half.y + 0.03, half.y - 0.035))
		if absf(p.z - lane_z) < 0.03 + r:
			continue
		var free := true
		for circle: Vector3 in taken:
			if Vector2(p.x - circle.x, p.z - circle.y).length() < circle.z + r:
				free = false
				break
		if not free:
			continue
		taken.append(Vector3(p.x, p.z, r * 1.15))
		wanted -= 1
		if work.yard_thing(p, r, not snowman_done):
			snowman_done = true
	if snow >= 0.5:
		for i in int(snow * 6.0):
			var r := rng.randf_range(0.015, 0.03)
			var p := Vector3(rng.randf_range(-half.x + 0.04, half.x - 0.04), thick - 0.001, rng.randf_range(-half.y + 0.04, half.y - 0.04))
			if absf(p.z - lane_z) < 0.04 + r:
				continue
			work.piece("blob", GingerbreadHouse.Dresser.on(p, Vector3.UP, Vector3.RIGHT, Vector3(r * 1.5, r * 0.8, r * 1.1), rng.randf() * TAU),
					{"ink": [work.look["snow"], work.look["shade"], white], "layer": "snow"})
	# a fence along the front edge, a gap in its middle
	if decoration >= 0.45 and not low_detail:
		var z := half.y - 0.014
		var pickets := rng.randf() < 0.6
		GingerbreadHouse.fence(work, Vector3(-half.x + 0.03, thick, z), Vector3(-0.035, thick, z), pickets)
		GingerbreadHouse.fence(work, Vector3(0.035, thick, z), Vector3(half.x - 0.03, thick, z), pickets)
	# the houses
	for i in _plans.size():
		var plan := _plans[i]
		if merged:
			GingerbreadHouse.add_to(batch, plan["spec"], whole * (plan["place"] as Transform3D))
		else:
			var house := GingerbreadHouse.new()
			house.wear({"kind": plan["kind"], "palette": palette, "decoration": decoration, "snow": snow, "low_detail": low_detail,
					"seed": int(plan["spec"]["seed"]), "windows_glow": windows_glow, "glow_strength": glow_strength,
					"door_ajar": float(plan["spec"]["door_ajar"]), "board": false, "size": size, "shadows": shadows,
					"custom_bread": custom_bread, "custom_icing": custom_icing, "custom_sweets": custom_sweets})
			var place: Transform3D = plan["place"]
			# a house without its board sets itself down by the board's thickness: lift it back onto this one
			house.transform = Transform3D(place.basis, (place.origin + floor_y) * size)
			add_child(house)
			_nodes.append(house)
	_instance.mesh = batch.mesh()
	_instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if shadows else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	# real lights in some, from the middle outwards
	var order: Array = range(_plans.size())
	order.sort_custom(func(a: int, b: int) -> bool: return absf((_plans[a]["middle"] as Vector3).x) < absf((_plans[b]["middle"] as Vector3).x))
	for k in mini(lights_inside, order.size()):
		var plan := _plans[order[k]]
		var lamp := OmniLight3D.new()
		lamp.name = "Candle%d" % k
		lamp.position = ((plan["place"] as Transform3D) * GingerbreadHouse._vec(GingerbreadHouse.notes(plan["kind"])["light"])) * size
		lamp.light_color = Color(1.0, 0.68, 0.34)
		lamp.light_energy = light_energy * size
		lamp.omni_range = 0.35 * size
		lamp.omni_attenuation = 1.6
		add_child(lamp)
		_lamps.append(lamp)
	set_process(not _lamps.is_empty())


func _rebuild() -> void:
	_planned = false
	if is_inside_tree() and not _queued:
		_queued = true
		_build.call_deferred()


func _set_count(value: int) -> void:
	count = value
	_rebuild()


func _set_kinds(value: Array[int]) -> void:
	kinds = value
	_rebuild()


func _set_palette(value: GingerbreadHouse.Palette) -> void:
	palette = value
	_rebuild()


func _set_decoration(value: float) -> void:
	decoration = value
	_rebuild()


func _set_snow(value: float) -> void:
	snow = value
	_rebuild()


func _set_size(value: float) -> void:
	size = value
	_rebuild()


func _set_seed(value: int) -> void:
	seed = value
	_rebuild()


func _set_spacing(value: float) -> void:
	spacing = value
	_rebuild()


func _set_both_sides(value: bool) -> void:
	both_sides = value
	_rebuild()


func _set_low_detail(value: bool) -> void:
	low_detail = value
	_rebuild()


func _set_windows_glow(value: bool) -> void:
	windows_glow = value
	_rebuild()


func _set_glow_strength(value: float) -> void:
	glow_strength = value
	_rebuild()


func _set_lights_inside(value: int) -> void:
	lights_inside = value
	_rebuild()


func _set_light_energy(value: float) -> void:
	light_energy = value
	_rebuild()


func _set_door_ajar(value: float) -> void:
	door_ajar = value
	_rebuild()


func _set_merged(value: bool) -> void:
	merged = value
	_rebuild()


func _set_custom_bread(value: Color) -> void:
	custom_bread = value
	_rebuild()


func _set_custom_icing(value: Color) -> void:
	custom_icing = value
	_rebuild()


func _set_custom_sweets(value: PackedColorArray) -> void:
	custom_sweets = value
	_rebuild()


func _set_shadows(value: bool) -> void:
	shadows = value
	_rebuild()
