class_name PresentPile
extends Node3D
## A heap of wrapped presents, as under a tree: mixed shapes, sizes, papers and colours from a palette,
## set down so that each rests on the floor or on another (some stacked, some leaning against a
## neighbour) and none passes through another. This node is on the floor at the middle of the heap.
##
##     var heap := Present.pile(5, Present.Palette.CLASSIC, 3, 12.5)     # five presents, seed 3, a unit of 8 cm
##     heap.position = under_the_tree
##     add_child(heap)
##     for keep_out: Dictionary in heap.footprints():                    # where the player may not walk
##         if Present.blocks(keep_out, player.position, player_radius):
##             player.position = Present.push_out(keep_out, player.position, player_radius)
##
## The whole heap is ONE mesh and one draw (every present shares one material and carries its colours
## in its points). With `merged` off each present is a Present node of its own, a draw each, for a game
## that wants to take one away.

## How many presents. Default 7.
@export_range(1, 60, 1, "or_greater") var count := 7: set = _set_count
## The colours and papers they are dealt (see Present.Palette). Default CLASSIC: red, green, cream, gold.
@export var palette := Present.Palette.CLASSIC: set = _set_palette
## For Palette.CUSTOM: the colours the papers and their prints are dealt from (give at least two).
@export var custom_papers: Array[Color] = [Color(0.7, 0.09, 0.1), Color(0.96, 0.91, 0.79)]: set = _set_custom_papers
## For Palette.CUSTOM: the colours the ribbons and bows are dealt from.
@export var custom_ribbons: Array[Color] = [Color(0.85, 0.64, 0.2)]: set = _set_custom_ribbons
## The number the heap is dealt from: the same settings and seed give the same heap, another seed
## another. Default 1.
@export var seed := 1: set = _set_seed
## How big everything is: 1 for a game counted in metres, 12.5 for a game whose unit is 8 cm. Default 1.
@export_range(0.01, 100.0, 0.01, "or_greater") var size := 1.0: set = _set_size
## How much the presents differ in size. 0 all as modelled, 0.25 (the default) a quarter smaller to a
## quarter bigger, 0.6 from tiny to huge.
@export_range(0.0, 0.8, 0.01) var size_variation := 0.25: set = _set_size_variation
## How willing a present is to be put on top of another when it fits there. 0 all on the floor, 0.6
## (the default) a heap with a few stacks, 1 stacked wherever it fits.
@export_range(0.0, 1.0) var stacking := 0.6: set = _set_stacking
## How willing the flat boxes and the tall ones are to be leant against a neighbour. 0 never, 0.5
## (the default) now and then, 1 whenever there is something to lean on.
@export_range(0.0, 1.0) var leaning := 0.5: set = _set_leaning
## How loosely they are set down. 0 shoulder to shoulder (a centimetre apart), 1 with a few
## centimetres between, 4 scattered across the floor. Default 0.3.
@export_range(0.0, 6.0, 0.01, "or_greater") var spread := 0.3: set = _set_spread
## Which kinds of present may be dealt (Present.Shape numbers). Empty (the default): all of them.
@export var shapes: Array[int] = []: set = _set_shapes
## How printed papers are scaled (see Present.paper_scale). Default 1.
@export_range(0.05, 8.0, 0.01, "or_greater") var paper_scale := 1.0: set = _set_paper_scale
## Draw the low models (about a quarter of the triangles). Default off.
@export var low_detail := false: set = _set_low_detail
## One mesh and one draw for the whole heap (the default). Off: a Present node for each, a draw each.
@export var merged := true: set = _set_merged
## Give each present on the floor a StaticBody3D box or cylinder. Off by default (see footprints()).
@export var collision := false: set = _set_collision
## Whether the heap casts shadows. Default on.
@export var shadows := true: set = _set_shadows

var _plans: Array[Dictionary] = []
var _made: Array[Node] = []
var _triangles := 0
var _queued := false


## Where the player may not walk: a footprint (see Present.footprint()) for every present standing or
## leaning on the floor, in the world. The ones stacked on others are left out: what they stand on
## already covers them. Read it after the heap is in the tree, and again if it is moved.
func footprints() -> Array[Dictionary]:
	var out: Array[Dictionary] = []
	var grown := global_basis.get_scale()
	var turned := global_basis.get_euler().y
	for plan in _plans:
		if not plan["grounded"]:
			continue
		var centre: Vector2 = plan["centre"]
		var half: Vector2 = plan["half"]
		var wide := Vector2(half.x * size * grown.x, half.y * size * grown.z)
		out.append({
			"centre": global_transform * (Vector3(centre.x, 0.0, centre.y) * size),
			"round": plan["round"],
			"half": wide,
			"turn": float(plan["turn"]) + turned,
			"radius": maxf(wide.x, wide.y) if plan["round"] else wide.length(),
			"height": float(plan["top"]) * size * grown.y,
		})
	return out


## Whether a point on the floor is inside any present of the heap, each grown by `margin`.
func blocks(point: Vector3, margin := 0.0) -> bool:
	for print_ in footprints():
		if Present.blocks(print_, point, margin):
			return true
	return false


## The point moved out of every present it is inside (the point itself if it is in none): set a
## walker's position to this each step and it slides round the heap.
func push_out(point: Vector3, margin := 0.0) -> Vector3:
	var prints := footprints()
	for _pass in 3:
		var moved := false
		for print_ in prints:
			if Present.blocks(print_, point, margin):
				point = Present.push_out(print_, point, margin + 0.0001)
				moved = true
		if not moved:
			break
	return point


## One circle on the floor that holds the whole heap: {centre: Vector3, radius: float}, in the world.
func reach() -> Dictionary:
	var far := 0.0
	for plan in _plans:
		far = maxf(far, (plan["centre"] as Vector2).length() + (plan["half"] as Vector2).length())
	return {"centre": global_position, "radius": far * size * maxf(global_basis.get_scale().x, global_basis.get_scale().z)}


## What was dealt: for each present its settings (as Present.add_to() takes them) and where it is in
## the heap, {spec: Dictionary, place: Transform3D (in metres, before `size`), grounded: bool, leaning:
## bool, against: which of these it leans on (-1 if none), carries: bool, and its rectangle on the floor:
## centre, half, turn, top}.
func presents() -> Array[Dictionary]:
	return _plans


## How many triangles the heap is drawn with.
func triangles() -> int:
	return _triangles


func _ready() -> void:
	_build()


func _rebuild() -> void:
	if is_inside_tree() and not _queued:
		_queued = true
		_build.call_deferred()


func _build() -> void:
	_queued = false
	if not is_inside_tree():
		return
	for node in _made:
		remove_child(node)
		node.queue_free()
	_made.clear()
	_plan()
	_triangles = 0
	var grow := Transform3D(Basis.from_scale(Vector3.ONE * size), Vector3.ZERO)
	if merged:
		var batch := Present.Batch.new()
		for plan in _plans:
			Present.add_to(batch, plan["spec"], grow * (plan["place"] as Transform3D))
		var holder := MeshInstance3D.new()
		holder.name = "Presents"
		holder.mesh = batch.mesh()
		holder.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if shadows else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(holder)
		_made.append(holder)
		_triangles = batch.triangles()
	else:
		for plan in _plans:
			var gift := Present.new()
			gift.wear(plan["spec"])
			gift.shadows = shadows
			var place: Transform3D = plan["place"]
			gift.size = size * place.basis.get_scale().x
			gift.transform = Transform3D(place.basis.orthonormalized(), place.origin * size)
			add_child(gift)
			_made.append(gift)
			var batch := Present.Batch.new()
			Present.add_to(batch, plan["spec"], Transform3D.IDENTITY)
			_triangles += batch.triangles()
	if collision:
		for plan in _plans:
			if not plan["grounded"] or plan["leaning"]:
				continue
			var half: Vector2 = plan["half"]
			var tall: float = plan["top"]
			var body := Present.solid(Vector3(half.x, tall * 0.5, half.y) * size, Vector3(0.0, tall * 0.5, 0.0) * size, plan["round"])
			var centre: Vector2 = plan["centre"]
			body.position = Vector3(centre.x, 0.0, centre.y) * size
			body.rotation.y = plan["turn"]
			add_child(body)
			_made.append(body)


# ------------------------------------------------------------------ setting the heap down
## Deals the presents and sets each down: on the floor clear of the others, on top of one it fits on,
## or leant against one. Everything here is in metres; `size` comes after.
func _plan() -> void:
	_plans.clear()
	var rng := RandomNumberGenerator.new()
	rng.seed = seed * 104729 + 7
	var kinds: Array[int] = shapes.duplicate()
	if kinds.is_empty():
		kinds = [Present.Shape.CUBE, Present.Shape.SHIRT_BOX, Present.Shape.TALL_BOX, Present.Shape.LONG_BOX,
				Present.Shape.DRUM, Present.Shape.CUBE, Present.Shape.BAG, Present.Shape.HAT_BOX, Present.Shape.PARCEL,
				Present.Shape.SHIRT_BOX, Present.Shape.TALL_BOX]
	var items: Array[Dictionary] = []
	var deck: Array[int] = []
	var worn := {}
	for i in count:
		if deck.is_empty():
			deck = kinds.duplicate()
			for k in range(deck.size() - 1, 0, -1):
				var swap := rng.randi() % (k + 1)
				var held := deck[k]
				deck[k] = deck[swap]
				deck[swap] = held
		var which: int = deck.pop_back()
		var dress := {}
		for _try in 6:      # no two presents of a heap in the same paper and colours, if it can be helped
			dress = Present.look(palette, rng, which as Present.Shape, custom_papers, custom_ribbons)
			var key := "%d %s" % [dress["paper"], (dress["paper_colour"] as Color).to_html(false)]
			if not worn.has(key):
				worn[key] = true
				break
		dress["shape"] = which
		dress["seed"] = rng.randi() % 100000 + 1
		dress["low_detail"] = low_detail
		dress["paper_scale"] = paper_scale
		var big := 1.0 + size_variation * rng.randf_range(-1.0, 1.0)
		var of := Present.measure(dress)
		items.append({"spec": dress, "big": big, "half": (of["half"] as Vector3) * big, "middle": (of["middle"] as Vector3) * big,
				"round": of["round"]})
	# the biggest go down first, so the small ones end up on top and round the edge
	items.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		var ha: Vector3 = a["half"]
		var hb: Vector3 = b["half"]
		return ha.x * ha.z > hb.x * hb.z)
	for i in items.size():
		var item := items[i]
		var which: int = item["spec"]["shape"]
		var done := false
		if i >= 1 and which != Present.Shape.TALL_BOX and rng.randf() < stacking:      # a tall box is not stood on another
			done = _stack(item, rng)
		if not done and i >= 1 and (which == Present.Shape.SHIRT_BOX or which == Present.Shape.TALL_BOX) and rng.randf() < leaning:
			done = _lean(item, rng)
		if not done:
			_set_down(item, rng)
	# nothing on a present that carries another; no tag where something leans
	for plan in _plans:
		if plan["carries"]:
			plan["spec"]["bow"] = Present.Bow.NONE
			plan["spec"]["tag"] = false
		if plan["leant_on"] or plan["leaning"]:
			plan["spec"]["tag"] = false
		if plan["leaning"] or plan["leant_on"]:
			if plan["spec"].get("bow_place", Present.BowPlace.AUTO) == Present.BowPlace.SIDE:
				plan["spec"]["bow_place"] = Present.BowPlace.AUTO
	# the node is at the middle of the heap
	var middle := Vector2.ZERO
	var grounded := 0
	for plan in _plans:
		if plan["grounded"]:
			middle += plan["centre"]
			grounded += 1
	middle /= maxf(grounded, 1)
	for plan in _plans:
		plan["centre"] = (plan["centre"] as Vector2) - middle
		var place: Transform3D = plan["place"]
		place.origin -= Vector3(middle.x, 0.0, middle.y)
		plan["place"] = place


## A present standing square on something: where its foot goes (y), turned, its middle over `centre`.
func _stand(item: Dictionary, centre: Vector2, turn: float, y: float, level: int) -> Dictionary:
	var big: float = item["big"]
	var half: Vector3 = item["half"]
	var middle: Vector3 = item["middle"]
	var turned := Basis(Vector3.UP, turn).scaled(Vector3.ONE * big)
	var foot := Vector3(centre.x, y, centre.y) - Basis(Vector3.UP, turn) * Vector3(middle.x, 0.0, middle.z)
	var plan := {
		"spec": item["spec"], "place": Transform3D(turned, foot), "centre": centre, "half": Vector2(half.x, half.z),
		"turn": turn, "round": item["round"], "top": y + half.y * 2.0, "level": level, "grounded": level == 0,
		"leaning": false, "carries": false, "leant_on": false, "against": -1,
	}
	_plans.append(plan)
	return plan


func _set_down(item: Dictionary, rng: RandomNumberGenerator) -> void:
	var half: Vector3 = item["half"]
	var gap := 0.012 + 0.03 * spread
	var turn := (rng.randi() % 4) * PI * 0.5 + rng.randf_range(-0.5, 0.5)
	var rect := Vector2(half.x, half.z) + Vector2(gap, gap) * 0.5
	var start := rng.randf() * TAU
	for k in 400:
		var far := 0.035 * (1.0 + spread) * sqrt(float(k)) * (1.0 + 0.6 * spread)
		var angle := start + k * 2.39996
		var at := Vector2(cos(angle), sin(angle)) * far
		if _free(at, rect, turn, null, 0.0):
			_stand(item, at, turn, 0.0, 0)
			return
	_stand(item, Vector2(cos(start), sin(start)) * (2.0 + _plans.size()), turn, 0.0, 0)


## Whether a turned rectangle whose foot is at a height is clear of every present that reaches above
## that height (but `except`): the ones on the floor, and the ones stacked that overhang.
func _free(centre: Vector2, half: Vector2, turn: float, except: Variant, foot: float) -> bool:
	for plan in _plans:
		if float(plan["top"]) <= foot + 0.001 or (except != null and is_same(plan, except)):
			continue
		if _overlap(centre, half, turn, plan["centre"], plan["half"], plan["turn"]):
			return false
	return true


## Two turned rectangles: do they overlap? (The separating-axis test.)
static func _overlap(ca: Vector2, ha: Vector2, ta: float, cb: Vector2, hb: Vector2, tb: float) -> bool:
	var axes := [Vector2(cos(ta), -sin(ta)), Vector2(sin(ta), cos(ta)), Vector2(cos(tb), -sin(tb)), Vector2(sin(tb), cos(tb))]
	var d := cb - ca
	for axis: Vector2 in axes:
		var reach_a := ha.x * absf(axis.dot(axes[0])) + ha.y * absf(axis.dot(axes[1]))
		var reach_b := hb.x * absf(axis.dot(axes[2])) + hb.y * absf(axis.dot(axes[3]))
		if absf(d.dot(axis)) >= reach_a + reach_b:
			return false
	return true


## On top of a present with a flat top that it fits on (it may overhang a little).
func _stack(item: Dictionary, rng: RandomNumberGenerator) -> bool:
	var half: Vector3 = item["half"]
	var order: Array = range(_plans.size())
	for k in range(order.size() - 1, 0, -1):
		var swap := rng.randi() % (k + 1)
		var held: int = order[k]
		order[k] = order[swap]
		order[swap] = held
	for index: int in order:
		var under := _plans[index]
		var which: int = under["spec"]["shape"]
		if under["carries"] or under["leaning"] or under["leant_on"] or int(under["level"]) >= 2 or not Present.FLAT_TOPPED[which]:
			continue
		if which == Present.Shape.HAT_BOX and float(under["spec"].get("lid_ajar", 0.0)) > 0.0:
			continue
		var room: Vector2 = under["half"]
		for _try in 5:
			var turn := float(under["turn"]) + (rng.randi() % 2) * PI * 0.5 + rng.randf_range(-0.45, 0.45)
			var rel := turn - float(under["turn"])
			var fits := true
			var slack := Vector2(1e9, 1e9)
			for corner in [Vector2(1, 1), Vector2(1, -1), Vector2(-1, 1), Vector2(-1, -1)]:
				# a little of it may hang over a box's edge; none over a round one's
				var p := Vector2(half.x * corner.x, half.z * corner.y) * (1.0 if under["round"] else 0.88)
				var own := Vector2(p.x * cos(rel) + p.y * sin(rel), -p.x * sin(rel) + p.y * cos(rel))
				if under["round"]:
					fits = fits and own.length() <= maxf(room.x, room.y)
					slack = slack.min(Vector2.ONE * (maxf(room.x, room.y) - own.length()) * 0.5)
				else:
					fits = fits and absf(own.x) <= room.x and absf(own.y) <= room.y
					slack = slack.min(Vector2(room.x - absf(own.x), room.y - absf(own.y)))
			if not fits:
				continue
			var shift := Vector2(rng.randf_range(-1.0, 1.0) * slack.x, rng.randf_range(-1.0, 1.0) * slack.y)
			var under_turn: float = under["turn"]
			var centre: Vector2 = under["centre"] + Vector2(shift.x * cos(under_turn) + shift.y * sin(under_turn),
					-shift.x * sin(under_turn) + shift.y * cos(under_turn))
			if not _free(centre, Vector2(half.x, half.z) + Vector2(0.006, 0.006), turn, under, float(under["top"])):
				continue
			under["carries"] = true
			_stand(item, centre, turn, float(under["top"]) + 0.002, int(under["level"]) + 1)
			return true
	return false


## Leant against the side of a present on the floor: a flat box stood on its edge with its top (and
## bow) outwards, or a tall box tipped over against its neighbour. It pivots on the foot of the side
## that faces the neighbour, and its upper edge rests on the neighbour's side or top edge.
func _lean(item: Dictionary, rng: RandomNumberGenerator) -> bool:
	var half: Vector3 = item["half"]
	var middle: Vector3 = item["middle"]
	var big: float = item["big"]
	var flat: bool = item["spec"]["shape"] == Present.Shape.SHIRT_BOX
	# as it stands when leant: how long it is along the neighbour, how thick towards it, how high
	var along := half.x * 2.0
	var thick := half.y * 2.0 if flat else half.z * 2.0
	var high := half.z * 2.0 if flat else half.y * 2.0
	var order: Array = range(_plans.size())
	for k in range(order.size() - 1, 0, -1):
		var swap := rng.randi() % (k + 1)
		var held: int = order[k]
		order[k] = order[swap]
		order[swap] = held
	for index: int in order:
		var wall := _plans[index]
		if not wall["grounded"] or wall["leaning"] or wall["leant_on"] or wall["carries"]:
			continue
		if not Present.FLAT_TOPPED[int(wall["spec"]["shape"])]:
			continue        # nothing leans on a bag or a lump
		var tilt := rng.randf_range(0.2, 0.42)
		var wall_top: float = wall["top"]
		if wall_top < 0.45 * high * cos(tilt):
			continue
		var wall_half: Vector2 = wall["half"]
		var wall_turn: float = wall["turn"]
		var start := rng.randi() % 4
		for s in 4:
			var side := (start + s) % 4
			var angle := wall_turn - side * PI * 0.5
			var out := Vector2(cos(angle), -sin(angle))            # out of that side of the neighbour, on the floor
			var slide := Vector2(-out.y, out.x)
			var depth := wall_half.x if side % 2 == 0 else wall_half.y
			var width := wall_half.y if side % 2 == 0 else wall_half.x
			if wall["round"]:
				depth = maxf(wall_half.x, wall_half.y)
				width = depth * 0.4
			# its foot stands this far from the neighbour's side
			var gap := (high * sin(tilt) if high * cos(tilt) <= wall_top else wall_top * tan(tilt)) + 0.004
			var reach := gap + thick * cos(tilt)
			var offset := rng.randf_range(-1.0, 1.0) * maxf(width - along * 0.5, 0.0)
			var face: Vector2 = wall["centre"] + out * depth + slide * offset
			var rect_centre := face + out * (reach * 0.5 + 0.004)
			var rect_half := Vector2(reach * 0.5, along * 0.5)
			var rect_turn := atan2(-out.y, out.x)
			if not _free(rect_centre, rect_half + Vector2(0.006, 0.006), rect_turn, wall, 0.0):
				continue
			if high * cos(tilt) > wall_top:
				wall["carries"] = true      # it rests on the neighbour's top edge and stands over it: nothing else goes up there
			# its own frame as it stands: across (along the neighbour), up its height, and out of its outer face
			var out3 := Vector3(out.x, 0.0, out.y)
			var up := (Vector3.UP * cos(tilt) - out3 * sin(tilt)).normalized()
			var outer := (out3 * cos(tilt) + Vector3.UP * sin(tilt)).normalized()
			var across := up.cross(outer).normalized()
			var pivot := Vector3(face.x, 0.0, face.y) + out3 * gap
			var frame: Basis
			var foot: Vector3
			if flat:
				# the model's top faces outwards, its depth runs up
				frame = Basis(-across, outer, up)
				foot = pivot + up * (half.z - middle.z) + across * middle.x
			else:
				frame = Basis(across, up, outer)
				foot = pivot + outer * (half.z - middle.z) - across * middle.x
			wall["leant_on"] = true
			_plans.append({
				"spec": item["spec"], "place": Transform3D(frame.scaled(Vector3.ONE * big), foot), "centre": rect_centre,
				"half": rect_half, "turn": rect_turn, "round": false, "top": high * cos(tilt) + thick * sin(tilt), "level": 0,
				"grounded": true, "leaning": true, "carries": false, "leant_on": false, "against": index,
			})
			return true
	return false


# ------------------------------------------------------------------ settings
func _set_count(value: int) -> void:
	count = maxi(value, 1)
	_rebuild()


func _set_palette(value: Present.Palette) -> void:
	palette = value
	_rebuild()


func _set_custom_papers(value: Array[Color]) -> void:
	custom_papers = value
	_rebuild()


func _set_custom_ribbons(value: Array[Color]) -> void:
	custom_ribbons = value
	_rebuild()


func _set_seed(value: int) -> void:
	seed = value
	_rebuild()


func _set_size(value: float) -> void:
	size = maxf(value, 0.0001)
	_rebuild()


func _set_size_variation(value: float) -> void:
	size_variation = clampf(value, 0.0, 0.8)
	_rebuild()


func _set_stacking(value: float) -> void:
	stacking = clampf(value, 0.0, 1.0)
	_rebuild()


func _set_leaning(value: float) -> void:
	leaning = clampf(value, 0.0, 1.0)
	_rebuild()


func _set_spread(value: float) -> void:
	spread = maxf(value, 0.0)
	_rebuild()


func _set_shapes(value: Array[int]) -> void:
	shapes = value
	_rebuild()


func _set_paper_scale(value: float) -> void:
	paper_scale = maxf(value, 0.001)
	_rebuild()


func _set_low_detail(value: bool) -> void:
	low_detail = value
	_rebuild()


func _set_merged(value: bool) -> void:
	merged = value
	_rebuild()


func _set_collision(value: bool) -> void:
	collision = value
	_rebuild()


func _set_shadows(value: bool) -> void:
	shadows = value
	_rebuild()
