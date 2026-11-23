class_name OrnamentSet
extends Node3D
## Christmas tree ornaments, any number of them, drawn as ONE mesh (two draws with their glints): glass baubles in
## painted designs, a bell, wooden, felt, dough and gingerbread ones, toppers, bead and tinsel garlands.
## (GameCommon godot/ornaments. For a single ornament there is `Ornament`, which is a set of one.)
##
##   var baubles := OrnamentSet.new()
##   baubles.size = 12.5                                     # this game's units to a metre (Felt Mouse: 1 unit = 8 cm)
##   tree.add_child(baubles)                                 # a child of the tree, so the tree's own space is theirs
##   baubles.decorate(OrnamentSet.tips(tree, 30, 7), {"palette": OrnamentSet.Palette.CLASSIC, "seed": 7})
##   baubles.top(OrnamentSet.Kind.STAR_TOPPER, tip)
##   baubles.knock(mouse.global_position, Vector3(0.5, 0, 0), 0.6)   # the ones near there swing and settle
##
## Or one at a time: baubles.add(OrnamentSet.Kind.BALL, where, {"design": OrnamentSet.Design.STARS, "colour": Color.RED}).
## Every hanging ornament's place is the TOP of its thread: it hangs below that point.
##
## The models are in models/ornaments.glb (built in Blender by tools/build_ornaments.py), all real size in
## metres. Colour is not in the pictures: they hold amounts (how light, how much second colour, how much white,
## glitter) and each ornament's two colours ride on its vertices, so any ornament comes in any colours at no cost.

enum Kind {
	BALL, TEARDROP, ONION, REFLECTOR, RIBBED, ICICLE, BELL, WOODEN_STAR, HEART, SNOWFLAKE, PINE_CONE, CANDY_CANE,
	GINGERBREAD, MITTEN, STOCKING, STRAW_STAR, PAPER_STAR, DOUGH_STAR, DRUM, ROCKING_HORSE,
	STAR_TOPPER, SPIRE_TOPPER, BEADS, TINSEL,
}
## The painted designs a glass ornament (ball, teardrop, onion, reflector, ribbed, spire topper) can wear.
enum Design { PLAIN, BANDS, DOTS, STARS, SNOWFLAKES, GLITTER_BAND, SNOWCAP, SWIRLS, STRIPES, ZIGZAG, TREES, HARLEQUIN, ANTIQUE }
enum Palette { CLASSIC, SILVER_BLUE, PASTEL, HANDMADE, CUSTOM }

const RED := Color(0.72, 0.05, 0.06)
const GREEN := Color(0.06, 0.36, 0.14)
const GOLD := Color(0.95, 0.70, 0.22)
const CREAM := Color(0.96, 0.92, 0.82)
const SILVER := Color(0.80, 0.83, 0.88)
const WOOD := Color(0.86, 0.66, 0.42)
const FELT_RED := Color(0.82, 0.10, 0.09)
const FELT_GREEN := Color(0.10, 0.45, 0.18)
const TWINE_RED := Color(0.75, 0.10, 0.10)
const JUTE := Color(0.70, 0.56, 0.36)

## Each kind: its model's name; whether it is glass that takes a Design ("cell" is a fixed design cell for the ones
## that do not: ice, tinsel); the colours it wears unless told otherwise; its thread's two colours; "tint" 0 never
## recoloured by a palette, 1 its first colour is, 2 both are; "heavy" 0 (hangs high, small) .. 1 (hangs low);
## whether it gets a glint; whether it is handmade.
const KINDS := [
	{"name": "ball", "glass": true, "a": RED, "b": GOLD, "thread": [GOLD, GOLD], "tint": 2, "heavy": 0.7, "glint": true},
	{"name": "teardrop", "glass": true, "a": GOLD, "b": RED, "thread": [GOLD, GOLD], "tint": 2, "heavy": 0.3, "glint": true},
	{"name": "onion", "glass": true, "a": GREEN, "b": GOLD, "thread": [GOLD, GOLD], "tint": 2, "heavy": 0.6, "glint": true},
	{"name": "reflector", "glass": true, "a": RED, "b": GOLD, "thread": [GOLD, GOLD], "tint": 2, "heavy": 0.9, "glint": true},
	{"name": "ribbed", "glass": true, "a": GOLD, "b": RED, "thread": [GOLD, GOLD], "tint": 2, "heavy": 0.8, "glint": true},
	{"name": "icicle", "glass": true, "cell": 13, "a": Color(0.72, 0.86, 0.98), "b": Color.WHITE, "thread": [SILVER, SILVER], "tint": 0, "heavy": 0.0, "glint": true},
	{"name": "bell", "a": GOLD, "b": RED, "thread": [TWINE_RED, TWINE_RED], "tint": 1, "heavy": 0.6, "glint": true, "metal": true},
	{"name": "wooden_star", "a": WOOD, "b": RED, "thread": [JUTE, JUTE], "tint": 0, "heavy": 0.4, "handmade": true},
	{"name": "heart", "a": FELT_RED, "b": CREAM, "thread": [TWINE_RED, CREAM], "tint": 1, "heavy": 0.5, "handmade": true},
	{"name": "snowflake", "a": Color(0.80, 0.90, 1.0), "b": Color.WHITE, "thread": [SILVER, SILVER], "tint": 0, "heavy": 0.1},
	{"name": "pine_cone", "a": Color(0.58, 0.37, 0.20), "b": CREAM, "thread": [JUTE, JUTE], "tint": 0, "heavy": 0.7, "handmade": true},
	{"name": "candy_cane", "a": Color(0.85, 0.06, 0.08), "b": FELT_GREEN, "thread": [CREAM, CREAM], "tint": 0, "heavy": 0.2, "handmade": true},
	{"name": "gingerbread", "a": Color(0.70, 0.43, 0.20), "b": FELT_RED, "thread": [TWINE_RED, CREAM], "tint": 0, "heavy": 0.5, "handmade": true},
	{"name": "mitten", "a": FELT_RED, "b": FELT_GREEN, "thread": [TWINE_RED, CREAM], "tint": 1, "heavy": 0.5, "handmade": true},
	{"name": "stocking", "a": FELT_GREEN, "b": FELT_RED, "thread": [TWINE_RED, CREAM], "tint": 1, "heavy": 0.5, "handmade": true},
	{"name": "straw_star", "a": Color(0.90, 0.76, 0.42), "b": RED, "thread": [TWINE_RED, TWINE_RED], "tint": 0, "heavy": 0.1, "handmade": true},
	{"name": "paper_star", "a": CREAM, "b": RED, "thread": [TWINE_RED, CREAM], "tint": 0, "heavy": 0.2, "handmade": true},
	{"name": "dough_star", "a": Color(0.93, 0.86, 0.72), "b": RED, "thread": [TWINE_RED, CREAM], "tint": 0, "heavy": 0.5, "handmade": true},
	{"name": "drum", "a": RED, "b": GOLD, "thread": [GOLD, GOLD], "tint": 1, "heavy": 0.8, "handmade": true},
	{"name": "rocking_horse", "a": RED, "b": GREEN, "thread": [TWINE_RED, CREAM], "tint": 1, "heavy": 0.8, "handmade": true},
	{"name": "star_topper", "a": GOLD, "b": RED, "thread": [GOLD, GOLD], "tint": 0, "heavy": 0.0, "glint": true, "rigid": true},
	{"name": "spire_topper", "glass": true, "a": RED, "b": GOLD, "thread": [GOLD, GOLD], "tint": 2, "heavy": 0.0, "glint": false, "rigid": true},
	{"name": "beads", "a": RED, "b": GOLD, "thread": [GOLD, GOLD], "tint": 2, "heavy": 0.0, "rigid": true},
	{"name": "tinsel", "glass": true, "cell": 14, "a": SILVER, "b": Color.WHITE, "thread": [SILVER, SILVER], "tint": 1, "heavy": 0.0, "rigid": true},
]

## What `decorate` deals from for each palette: the glass colours, the accents painted on them, the share of
## ornaments that are not glass baubles, and which of those kinds may appear.
const PALETTES := {
	Palette.CLASSIC: {
		"colours": [Color(0.72, 0.05, 0.06), Color(0.95, 0.70, 0.22), Color(0.06, 0.36, 0.14)],
		"accents": [Color(0.95, 0.70, 0.22), Color(0.96, 0.92, 0.82)],
		"others": 0.35,
		"kinds": [Kind.BELL, Kind.CANDY_CANE, Kind.PINE_CONE, Kind.GINGERBREAD, Kind.WOODEN_STAR, Kind.HEART, Kind.STRAW_STAR, Kind.DRUM, Kind.ICICLE],
	},
	Palette.SILVER_BLUE: {
		"colours": [Color(0.78, 0.81, 0.87), Color(0.08, 0.22, 0.60), Color(0.42, 0.66, 0.90), Color(0.93, 0.95, 1.0)],
		"accents": [Color(0.86, 0.88, 0.93), Color(1.0, 1.0, 1.0)],
		"others": 0.3,
		"kinds": [Kind.SNOWFLAKE, Kind.ICICLE, Kind.BELL, Kind.PINE_CONE, Kind.SNOWFLAKE, Kind.ICICLE],
	},
	Palette.PASTEL: {
		"colours": [Color(0.95, 0.58, 0.68), Color(0.56, 0.86, 0.72), Color(0.58, 0.76, 0.95), Color(0.98, 0.88, 0.56), Color(0.76, 0.64, 0.92)],
		"accents": [Color(1.0, 1.0, 1.0), Color(0.98, 0.90, 0.62)],
		"others": 0.3,
		"kinds": [Kind.HEART, Kind.SNOWFLAKE, Kind.MITTEN, Kind.STOCKING, Kind.PAPER_STAR, Kind.BELL, Kind.DOUGH_STAR],
	},
	Palette.HANDMADE: {
		"colours": [Color(0.82, 0.10, 0.09), Color(0.10, 0.45, 0.18), Color(0.93, 0.88, 0.76)],
		"accents": [Color(0.96, 0.92, 0.82), Color(0.82, 0.10, 0.09)],
		"others": 1.0,
		"kinds": [Kind.WOODEN_STAR, Kind.HEART, Kind.GINGERBREAD, Kind.MITTEN, Kind.STOCKING, Kind.STRAW_STAR, Kind.PAPER_STAR,
				Kind.DOUGH_STAR, Kind.DRUM, Kind.ROCKING_HORSE, Kind.PINE_CONE, Kind.CANDY_CANE],
	},
}
const BAUBLES := [Kind.BALL, Kind.BALL, Kind.TEARDROP, Kind.ONION, Kind.REFLECTOR, Kind.RIBBED]
const THREAD_BUILT := 0.03      # the thread's length in the models
const DESIGN_CELLS := 16.0
const PIECE := 0.1              # a garland piece's length, real metres

## The game's units to a real metre: the models are real size (a ball 6 cm across) and everything is multiplied by
## this. 1 in a game measured in metres; 12.5 in Felt Mouse, where 1 unit is 8 cm. Larger for toy-like, oversized
## ornaments. Takes effect at the next rebuild.
@export_range(0.01, 200.0, 0.01, "or_greater") var size := 1.0:
	set(value):
		size = value
		_changed()
## Use each ornament's low model (about a quarter of the triangles: 30 to 150 in place of 60 to 480). For
## phones and for trees seen from across a room; close up the low baubles are plainly angular.
@export var low_detail := false:
	set(value):
		low_detail = value
		_changed()
## How much every hanging ornament sways by itself, in degrees either way: 0 dead still, 1 (the default) barely
## breathing as in a quiet room, 5 a draughty hall, 20 a tree in the wind. Toppers and garlands never sway.
@export_range(0.0, 45.0, 0.1, "or_greater") var sway := 1.0:
	set(value):
		sway = value
		_apply()
## The four-pointed star of light on each shiny ornament (glass, the bell, the star topper), which twinkles slowly
## and reads as a sparkle with no post-process glow: 0 none (and one draw fewer), 0.6 (the default) a soft
## glint, 2 dazzling. It is drawn on top of the room's light, so in a pitch-dark room turn it down.
@export_range(0.0, 4.0, 0.01, "or_greater") var glint := 0.6:
	set(value):
		glint = value
		_changed()
## How strongly glossy surfaces mirror the painted room (a window's highlight, a warm floor, a pale rim) when a
## light reaches them: 0 flat paint, 1 (the default) polished glass, 2 chrome.
@export_range(0.0, 4.0, 0.01, "or_greater") var shine := 1.0:
	set(value):
		shine = value
		_apply()
## How much of that mirrored room shows on an ornament no light reaches: 0 only real lights make it shine (right
## for a dark room), 0.3 (the default) a faint gleam everywhere, 1 always fully shiny (right for daylight).
@export_range(0.0, 2.0, 0.01, "or_greater") var room_light := 0.3:
	set(value):
		room_light = value
		_apply()
## How lively glitter is (glitter bands, snow caps, frost, tinsel, the star topper): 0 none, 1 (the default)
## grains winking as the eye or the ornament moves, 3 a disco.
@export_range(0.0, 5.0, 0.01, "or_greater") var sparkle := 1.0:
	set(value):
		sparkle = value
		_apply()
## The colour of every glass ornament's metal cap and wire loop, and of the toppers' sockets: gold (the default)
## or silver are the real ones.
@export var cap_colour := Color(0.90, 0.70, 0.30):
	set(value):
		cap_colour = value
		_changed()
## Whether the ornaments throw shadows. Off by default: they are small, and a shadow-casting light draws them again.
@export var cast_shadows := false:
	set(value):
		cast_shadows = value
		if _body:
			_body.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if value else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

static var _models := {}        # name -> what _read made of a mesh
static var _sheets := {}
static var _shaders := {}
static var _looks := {}

var _items: Array[Dictionary] = []
var _body: MeshInstance3D
var _dirty := false
var _knocks := [[Vector4.ZERO, Vector4(0, 0, 0, 1000.0)], [Vector4.ZERO, Vector4(0, 0, 0, 1000.0)]]
var _next_knock := 0
var _triangles := 0


func _ready() -> void:
	set_process(false)
	if _dirty:
		rebuild()


# ------------------------------------------------------------------------------------------------ hanging things
## Hangs one ornament with the top of its thread at `at` (in this node's own space). Options, all optional:
## "design" (a Design, for glass), "colour", "colour2" (its two colours), "scale" (against real size, 1),
## "thread" (the thread's length in real metres, 0.03; a candy cane has none), "out" (a direction its front
## should face, e.g. away from the trunk) or "turn" (radians about the vertical), "seed". Returns its number.
func add(kind: Kind, at: Vector3, options := {}) -> int:
	var rng := RandomNumberGenerator.new()
	rng.seed = hash([int(options.get("seed", _items.size() * 7919 + 13)), kind])
	var facts: Dictionary = KINDS[kind]
	var turn := float(options.get("turn", rng.randf() * TAU if facts.get("glass", false) or kind == Kind.BELL or kind == Kind.PINE_CONE else rng.randf_range(-0.5, 0.5)))
	var out: Vector3 = options.get("out", Vector3.ZERO)
	if not options.has("turn") and Vector2(out.x, out.z).length() > 0.001:
		turn += atan2(out.x, out.z)
	var item := {
		"kind": kind,
		"at": at,
		"basis": options.get("basis", Basis(Vector3.UP, turn)),
		"design": int(options.get("design", Design.PLAIN)),
		"a": options.get("colour", facts["a"]),
		"b": options.get("colour2", facts["b"]),
		"scale": float(options.get("scale", 1.0)),
		"thread": maxf(float(options.get("thread", THREAD_BUILT)), 0.002),
		"phase": rng.randf(),
		"rigid": bool(options.get("rigid", facts.get("rigid", false))),
	}
	_items.append(item)
	_changed()
	return _items.size() - 1


## Puts a topper (Kind.STAR_TOPPER or Kind.SPIRE_TOPPER) on a tree's tip at `tip` (this node's space): its cone
## socket goes over the tip. Options as for `add`, and "sink" (how far down over the tip the socket's mouth sits,
## real metres, 0.035).
func top(kind: Kind, tip: Vector3, options := {}) -> int:
	var given := options.duplicate()
	var grown := size * float(given.get("scale", 1.0))
	if not given.has("turn") and not given.has("out"):
		given["turn"] = 0.0
	return add(kind, tip - Vector3.UP * float(given.get("sink", 0.035)) * grown, given)


## Lays a garland (Kind.BEADS or Kind.TINSEL) along `line` (points in this node's space), in 10 cm pieces end to
## end, so give a line that curves gently. Options: "colour", "colour2", "scale".
func drape(kind: Kind, line: PackedVector3Array, options := {}) -> void:
	var step := PIECE * size * float(options.get("scale", 1.0))
	if line.size() < 2 or step <= 0.0:
		return
	var from := line[0]
	var next := 1
	var guard := 0
	while next < line.size() and guard < 4000:
		guard += 1
		# the next point of the line one piece away from `from`
		var reached := false
		var to := from
		while next < line.size():
			var a := line[next - 1] if from.distance_to(line[next - 1]) < step else from
			var b := line[next]
			if from.distance_to(b) >= step:
				var lo := 0.0
				var hi := 1.0
				for _i in 16:
					var mid := (lo + hi) * 0.5
					if from.distance_to(a.lerp(b, mid)) < step:
						lo = mid
					else:
						hi = mid
				to = a.lerp(b, hi)
				reached = true
				break
			next += 1
		if not reached:
			break
		var x := (to - from).normalized()
		var y := Vector3.UP - x * Vector3.UP.dot(x)
		y = y.normalized() if y.length() > 0.01 else x.cross(Vector3.RIGHT).normalized()
		var given := options.duplicate()
		given["basis"] = Basis(x, y, x.cross(y)) * Basis(Vector3.RIGHT, float(_items.size()) * 1.7)
		add(kind, from, given)
		from = to


## Hangs a mixed, balanced set on `points` (each a Dictionary with "position" and, if known, "out", as `tips`,
## `under` and `along` return; or plain Vector3s). No two neighbours match, heavier ornaments hang lower and
## larger, lighter ones higher and smaller. Options: "palette" (a Palette, CLASSIC), "seed" (1), "others" (the
## share that are not glass baubles, 0..1; each palette has its own), "scale" (Vector2 smallest and largest
## against real size, (0.8, 1.15)), "thread" (Vector2 shortest and longest thread in real metres, (0.012, 0.035)),
## "plain" (the share of glass left unpainted, 0.25), and for Palette.CUSTOM "colours" and "accents" (Arrays of
## Color) and "kinds" (the non-bauble kinds allowed).
func decorate(points: Array, options := {}) -> void:
	if points.is_empty():
		return
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(int(options.get("seed", 1)))
	var palette: Dictionary = PALETTES[options.get("palette", Palette.CLASSIC)] if int(options.get("palette", Palette.CLASSIC)) != Palette.CUSTOM else PALETTES[Palette.CLASSIC]
	var colours: Array = options.get("colours", palette["colours"])
	var accents: Array = options.get("accents", palette["accents"])
	var others: Array = options.get("kinds", palette["kinds"])
	var share := float(options.get("others", palette["others"]))
	var sizes: Vector2 = options.get("scale", Vector2(0.8, 1.15))
	var threads: Vector2 = options.get("thread", Vector2(0.012, 0.035))
	var plain := float(options.get("plain", 0.25))
	if others.is_empty():
		share = 0.0
	if colours.is_empty():
		colours = [RED]
	if accents.is_empty():
		accents = [CREAM]

	var places: Array[Vector3] = []
	var outs: Array[Vector3] = []
	var low := INF
	var high := -INF
	for p: Variant in points:
		var where: Vector3 = p["position"] if p is Dictionary else p
		places.append(where)
		outs.append(p.get("out", Vector3.ZERO) if p is Dictionary else Vector3.ZERO)
		low = minf(low, where.y)
		high = maxf(high, where.y)
	# how near counts as a neighbour: about twice the usual gap
	var gap := 0.0
	for i in places.size():
		var nearest := INF
		for j in places.size():
			if j != i:
				nearest = minf(nearest, places[i].distance_squared_to(places[j]))
		gap += sqrt(nearest) / places.size() if nearest < INF else 0.0
	var near := gap * 2.2

	_load()
	var placed: Array[Dictionary] = []
	var counts := {}
	for i in places.size():
		var height := 0.5 if high - low < 0.0001 else (places[i].y - low) / (high - low)
		var best := {}
		var best_cost := INF
		for attempt in 14:
			var kind: Kind = others[rng.randi() % others.size()] if rng.randf() < share else BAUBLES[rng.randi() % BAUBLES.size()]
			var facts: Dictionary = KINDS[kind]
			var shade := rng.randi() % colours.size()
			var design := Design.PLAIN
			if facts.get("glass", false) and not facts.has("cell") and rng.randf() >= plain:
				design = (1 + rng.randi() % (Design.size() - 1)) as Design
			var grown := lerpf(sizes.y, sizes.x, height) * rng.randf_range(0.93, 1.07)
			var rope := rng.randf_range(threads.x, threads.y)
			var source: Dictionary = _models["orn_" + String(facts["name"])]
			var middle: Vector3 = places[i] + ((source["centre"] as Vector3) - Vector3(0, rope - THREAD_BUILT if source["hangs"] else 0.0, 0)) * size * grown
			var girth: float = float(source["radius"]) * size * grown
			var cost := absf(float(facts["heavy"]) - (1.0 - height)) * 1.6 + rng.randf() * 0.3
			for other in placed:      # two bodies in one place: far worse than any mismatch
				var room: float = middle.distance_to(other["middle"]) - (girth + float(other["girth"])) * 0.9
				if room < 0.0:
					cost += 20.0 + 200.0 * -room / maxf(girth, 0.0001)
			cost += float(counts.get(kind, 0)) * (0.5 if facts.get("glass", false) else 1.2)
			var same_look := int(facts["tint"]) == 0 or kind == Kind.BELL
			var closest := INF
			for other in placed:
				closest = minf(closest, places[i].distance_to(other["at"]))
			for other in placed:
				var away: float = places[i].distance_to(other["at"])
				# never a twin of a neighbour, nor of the nearest ornament however far
				if (away < near or away <= closest) and other["kind"] == kind and other["design"] == design and (same_look or other["shade"] == shade):
					cost += 50.0
				if away < near:
					var close := 1.0 - 0.5 * away / maxf(near, 0.0001)
					if other["kind"] == kind:
						cost += 3.0 * close
					if other["shade"] == shade and int(facts["tint"]) > 0 and other["tinted"]:
						cost += 2.5 * close
					if other["design"] == design and design != Design.PLAIN:
						cost += 1.5 * close
			if cost < best_cost:
				best_cost = cost
				best = {"kind": kind, "shade": shade, "design": design, "tinted": int(facts["tint"]) > 0, "at": places[i],
						"middle": middle, "girth": girth, "grown": grown, "rope": rope}
		placed.append(best)
		counts[best["kind"]] = int(counts.get(best["kind"], 0)) + 1
		var chosen: Dictionary = KINDS[best["kind"]]
		var given := {
			"design": best["design"],
			"scale": best["grown"],
			"thread": best["rope"],
			"out": outs[i],
			"seed": rng.randi(),
		}
		if int(chosen["tint"]) >= 1:
			var first: Color = colours[best["shade"]]
			if best["kind"] == Kind.BELL or best["kind"] == Kind.TINSEL:
				first = accents[0]     # a bell is metal: the palette's gold or silver
			given["colour"] = first
			if int(chosen["tint"]) >= 2:
				var second: Color = accents[rng.randi() % accents.size()]
				if _alike(second, first):
					second = accents[(accents.find(second) + 1) % accents.size()]
				if _alike(second, first):
					second = colours[(best["shade"] + 1) % colours.size()]
				given["colour2"] = second
		add(best["kind"], places[i], given)


static func _alike(a: Color, b: Color) -> bool:
	return absf(a.r - b.r) + absf(a.g - b.g) + absf(a.b - b.b) < 0.25


## Takes every ornament down.
func clear() -> void:
	_items.clear()
	_changed()


## How many ornaments (a garland counts one for each 10 cm piece).
func count() -> int:
	return _items.size()


## Triangles drawn, glints included (after a rebuild).
func triangle_count() -> int:
	return _triangles


## Every ornament as hung: "kind", "at" (the top of its thread), "design", "a", "b" (colours), "scale", "thread".
func ornaments() -> Array[Dictionary]:
	return _items.duplicate(true)


## Where an ornament's body is and how big (this node's space): {"centre", "radius", "bottom"} for collisions or
## for keeping other things clear of it.
func body_of(index: int) -> Dictionary:
	_load()
	var item := _items[index]
	var source: Dictionary = _models[_model_name(item["kind"])]
	var grown: float = size * item["scale"]
	var drop: float = item["thread"] - THREAD_BUILT if source["hangs"] else 0.0
	var middle: Vector3 = source["centre"] - Vector3(0, drop, 0)
	return {
		"centre": item["at"] + (item["basis"] as Basis) * middle * grown,
		"radius": float(source["radius"]) * grown,
		"bottom": (item["at"] as Vector3).y + (float(source["bottom"]) - drop) * grown,
	}


# ------------------------------------------------------------------------------------------------ swinging
## Knocks the ornaments near `where` (a place in the world) so they swing and come to rest: `push` is which way
## (in the world) and how far in radians at the most (0.3 a nudge, 0.8 a good shake); `reach` is how far from
## `where` the knock is felt, in the game's units (0: every ornament of the set). Each swings at its own rate (a
## long thread slowly, a short one quickly) and settles in about five seconds. Two knocks can be live at once; a
## third replaces the older.
func knock(where: Vector3, push: Vector3, reach := 0.0) -> void:
	var at := to_local(where) if is_inside_tree() else where
	var way := global_transform.basis.inverse() * push if is_inside_tree() else push
	if way.length() > 0.0001:
		way = way.normalized() * minf(push.length(), 1.3)
	_knocks[_next_knock] = [Vector4(at.x, at.y, at.z, reach), Vector4(way.x, way.y, way.z, 0.0)]
	_next_knock = 1 - _next_knock
	_send_knocks()
	set_process(true)


func _process(delta: float) -> void:
	var live := false
	for k: Array in _knocks:
		var push: Vector4 = k[1]
		if push.w < 900.0:
			push.w += delta
			if push.w > 9.0:
				push.w = 1000.0
			else:
				live = true
			k[1] = push
	_send_knocks()
	if not live:
		set_process(false)


func _send_knocks() -> void:
	if _body:
		_body.set_instance_shader_parameter(&"knock_a_at", _knocks[0][0])
		_body.set_instance_shader_parameter(&"knock_a_push", _knocks[0][1])
		_body.set_instance_shader_parameter(&"knock_b_at", _knocks[1][0])
		_body.set_instance_shader_parameter(&"knock_b_push", _knocks[1][1])


# ------------------------------------------------------------------------------------------------ where to hang
## Finds places to hang ornaments on a tree: the tips of its branches, spread evenly round and up it. `tree` is any
## Node3D with meshes under it (a PineTree's instance, a model); the points come back in `tree`'s own space, so add
## the OrnamentSet as a child of `tree`. It takes, in each band of height and each direction round the trunk, the
## point furthest out, so ornaments hang at the outside of the foliage and not inside it. Options: "top_clear" (the
## share of the height at the top left bare for the topper, 0.14), "bottom_clear" (the share at the foot left bare,
## 0.0), "inset" (how far in from the very tip, as a share of the way to the trunk, 0.08), "drop" (how far below
## the tip the hanging point is, in `tree`'s units, 0).
static func tips(tree: Node3D, how_many: int, seed := 1, options := {}) -> Array[Dictionary]:
	var cloud := _cloud(tree)
	var found: Array[Dictionary] = []
	if cloud.is_empty() or how_many <= 0:
		return found
	var low := INF
	var high := -INF
	var middle := Vector3.ZERO
	for p in cloud:
		low = minf(low, p.y)
		high = maxf(high, p.y)
		middle += p / cloud.size()
	var top_clear := float(options.get("top_clear", 0.14))
	var bottom_clear := float(options.get("bottom_clear", 0.0))
	var inset := float(options.get("inset", 0.08))
	var bands := clampi(int(round(sqrt(float(how_many)) * 1.7)), 3, 28)
	var sectors := 18
	var furthest := {}
	var band_reach := PackedFloat32Array()
	band_reach.resize(bands)
	for p in cloud:
		var share := (p.y - low) / maxf(high - low, 0.0001)
		if share > 1.0 - top_clear or share < bottom_clear:
			continue
		var band := mini(int((share - bottom_clear) / maxf(1.0 - top_clear - bottom_clear, 0.0001) * bands), bands - 1)
		var flat := Vector2(p.x - middle.x, p.z - middle.z)
		var reach := flat.length_squared()
		var key := band * sectors + int(fposmod(flat.angle(), TAU) / TAU * sectors) % sectors
		if not furthest.has(key) or reach > float(furthest[key][0]):
			furthest[key] = [reach, p]
		band_reach[band] = maxf(band_reach[band], reach)
	var candidates: Array[Vector3] = []
	for key: int in furthest:
		if float(furthest[key][0]) >= band_reach[key / sectors] * 0.36:   # (squared: 60% of the band's reach)
			candidates.append(furthest[key][1])
	for p in _spread(candidates, how_many, seed):
		var flat := Vector3(p.x - middle.x, 0.0, p.z - middle.z)
		var out := flat.normalized() if flat.length() > 0.0001 else Vector3.FORWARD
		found.append({"position": p - flat * inset - Vector3.UP * float(options.get("drop", 0.0)), "out": out})
	return found


## Finds places to hang ornaments under anything (a garland, a bough, a shelf, a mantelpiece): the lowest point of
## its meshes in each patch of a grid, spread evenly. Points are in `thing`'s own space. `out` is the way the
## ornaments should face (zero: away from the thing's middle).
static func under(thing: Node3D, how_many: int, seed := 1, out := Vector3.ZERO) -> Array[Dictionary]:
	var cloud := _cloud(thing)
	var found: Array[Dictionary] = []
	if cloud.is_empty() or how_many <= 0:
		return found
	var box := AABB(cloud[0], Vector3.ZERO)
	for p in cloud:
		box = box.expand(p)
	var patch := maxf(maxf(box.size.x, box.size.z) / maxf(float(how_many) * 1.5, 1.0), 0.0001)
	var lowest := {}
	for p in cloud:
		var key := Vector2i(int((p.x - box.position.x) / patch), int((p.z - box.position.z) / patch))
		if not lowest.has(key) or p.y < (lowest[key] as Vector3).y:
			lowest[key] = p
	var candidates: Array[Vector3] = []
	for key: Vector2i in lowest:
		candidates.append(lowest[key])
	var middle := box.get_center()
	for p in _spread(candidates, how_many, seed):
		var away := Vector3(p.x - middle.x, 0.0, p.z - middle.z)
		found.append({"position": p, "out": out if out != Vector3.ZERO else (away.normalized() if away.length() > 0.0001 else Vector3.BACK)})
	return found


## Places along a line (a garland's own line, a string, a rail): `how_many` of them, evenly but not machine-evenly
## (`jitter` 0 exact, 0.35 by hand), each `drop` below the line and facing `out`.
static func along(line: PackedVector3Array, how_many: int, seed := 1, out := Vector3.ZERO, drop := 0.0, jitter := 0.35) -> Array[Dictionary]:
	var found: Array[Dictionary] = []
	if line.size() < 2 or how_many <= 0:
		return found
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(seed)
	var total := 0.0
	for i in range(1, line.size()):
		total += line[i].distance_to(line[i - 1])
	for n in how_many:
		var want := total * clampf((n + 0.5 + rng.randf_range(-jitter, jitter)) / how_many, 0.0, 1.0)
		var run := 0.0
		for i in range(1, line.size()):
			var piece := line[i].distance_to(line[i - 1])
			if run + piece >= want or i == line.size() - 1:
				var p := line[i - 1].lerp(line[i], clampf((want - run) / maxf(piece, 0.000001), 0.0, 1.0))
				found.append({"position": p - Vector3.UP * drop, "out": out})
				break
			run += piece
	return found


## Every vertex of every mesh under `root`, in `root`'s own space (it need not be in the scene yet).
static func _cloud(root: Node3D) -> PackedVector3Array:
	var cloud := PackedVector3Array()
	var holders: Array[Node] = [root]
	holders.append_array(root.find_children("*", "MeshInstance3D", true, false))
	for holder in holders:
		var shown := holder as MeshInstance3D
		if shown == null or shown.mesh == null or shown.get_parent() is OrnamentSet:
			continue
		var to_root := Transform3D.IDENTITY
		var step: Node = shown
		while step != root and step is Node3D:
			to_root = (step as Node3D).transform * to_root
			step = step.get_parent()
		for surface in shown.mesh.get_surface_count():
			var points: PackedVector3Array = shown.mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]
			cloud.append_array(to_root * points)
	return cloud


## `how_many` of `candidates`, each as far as can be from those already taken.
static func _spread(candidates: Array[Vector3], how_many: int, seed: int) -> Array[Vector3]:
	var taken: Array[Vector3] = []
	if candidates.is_empty():
		return taken
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(seed)
	var nearest := PackedFloat32Array()
	nearest.resize(candidates.size())
	nearest.fill(INF)
	var pick := rng.randi() % candidates.size()
	while taken.size() < mini(how_many, candidates.size()):
		taken.append(candidates[pick])
		var best := -1.0
		var last := candidates[pick]
		for i in candidates.size():
			nearest[i] = minf(nearest[i], candidates[i].distance_squared_to(last))
			var scored := nearest[i] * rng.randf_range(0.8, 1.0)
			if scored > best:
				best = scored
				pick = i
	return taken


# ------------------------------------------------------------------------------------------------ building
func _changed() -> void:
	if _dirty:
		return
	_dirty = true
	if is_inside_tree():
		rebuild.call_deferred()


## Builds the mesh now (it is otherwise built once, on the next idle frame after anything changed).
func rebuild() -> void:
	_dirty = false
	_load()
	if _body == null:
		_body = MeshInstance3D.new()
		_body.name = "Ornaments"
		add_child(_body)
	_body.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if cast_shadows else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_triangles = 0
	if _items.is_empty():
		_body.mesh = null
		return
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var uvs := PackedVector2Array()
	var tags := PackedVector2Array()
	var hung := PackedFloat32Array()
	var first := PackedFloat32Array()
	var second := PackedFloat32Array()
	var index := PackedInt32Array()
	var g_verts := PackedVector3Array()
	var g_uvs := PackedVector2Array()
	var g_hung := PackedFloat32Array()
	var g_facts := PackedFloat32Array()
	var g_tint := PackedFloat32Array()
	var g_index := PackedInt32Array()
	var cap := cap_colour.srgb_to_linear()
	for item in _items:
		var facts: Dictionary = KINDS[item["kind"]]
		var source: Dictionary = _models[_model_name(item["kind"])]
		var grown: float = size * item["scale"]
		var extra: float = item["thread"] - THREAD_BUILT if source["hangs"] else 0.0
		var basis: Basis = (item["basis"] as Basis).scaled_local(Vector3.ONE * grown)
		var at: Vector3 = item["at"]
		var base := verts.size()
		# the thread stretched (or shortened): everything below it moves down as one, the thread in proportion
		var shape: PackedVector3Array = source["verts"].duplicate()
		if extra != 0.0:
			var slack: PackedFloat32Array = source["slack"]
			for n: int in source["threaded"]:
				shape[n].y += slack[n] * extra
		verts.append_array(Transform3D(basis, at - basis.y * extra) * shape)
		normals.append_array(Transform3D(item["basis"], Vector3.ZERO) * (source["normals"] as PackedVector3Array))
		var cell := int(facts.get("cell", item["design"]))
		if not source["cells"].has(cell):
			var moved: PackedVector2Array = source["uvs"].duplicate()
			var of_glass: PackedByteArray = source["glass"]
			for n in moved.size():
				if of_glass[n] == 1:
					moved[n].y = (cell + clampf(moved[n].y, 0.0, 1.0)) / DESIGN_CELLS
			source["cells"][cell] = moved
		uvs.append_array(source["cells"][cell])
		tags.append_array(source["tags"])
		var length: float = 0.0 if item["rigid"] else maxf(item["thread"] + float(source["drop"]) * item["scale"], 0.01)
		var a := (item["a"] as Color).srgb_to_linear()
		var b := (item["b"] as Color).srgb_to_linear()
		var ta := (facts["thread"][0] as Color).srgb_to_linear()
		var tb := (facts["thread"][1] as Color).srgb_to_linear()
		var parts: PackedByteArray = source["parts"]
		var glitter: PackedByteArray = source["glitter"]
		var many := parts.size()
		var start := hung.size()
		hung.resize(start + many * 4)
		first.resize(start + many * 4)
		second.resize(start + many * 4)
		for n in many:
			var o := start + n * 4
			hung[o] = at.x
			hung[o + 1] = at.y
			hung[o + 2] = at.z
			hung[o + 3] = length
			var one := a
			var two := b
			if parts[n] == 1:
				one = cap
				two = cap
			elif parts[n] == 2:
				one = ta
				two = tb
			first[o] = one.r
			first[o + 1] = one.g
			first[o + 2] = one.b
			first[o + 3] = item["phase"]
			second[o] = two.r
			second[o + 1] = two.g
			second[o + 2] = two.b
			second[o + 3] = float(glitter[n])
		for n: int in source["index"]:
			index.append(base + n)
		_triangles += (source["index"] as PackedInt32Array).size() / 3
		if glint > 0.0 and facts.get("glint", false):
			var middle: Vector3 = Transform3D(basis, at - basis.y * extra) * (source["centre"] as Vector3)
			var g := g_verts.size()
			for corner: Vector2 in [Vector2(-1, -1), Vector2(1, -1), Vector2(1, 1), Vector2(-1, 1)]:
				g_verts.append(middle)
				g_uvs.append(corner)
				g_hung.append_array([at.x, at.y, at.z, length])
				g_facts.append_array([float(source["radius"]) * grown, item["phase"], 0.0, 0.0])
				var tone := cap if facts.get("metal", false) else a
				g_tint.append_array([tone.r, tone.g, tone.b, 1.0])
			g_index.append_array([g, g + 1, g + 2, g, g + 2, g + 3])
			_triangles += 2

	var format := (Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT) \
			| (Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM1_SHIFT) \
			| (Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM2_SHIFT)
	var built := ArrayMesh.new()
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_TEX_UV] = uvs
	arrays[Mesh.ARRAY_TEX_UV2] = tags
	arrays[Mesh.ARRAY_CUSTOM0] = hung
	arrays[Mesh.ARRAY_CUSTOM1] = first
	arrays[Mesh.ARRAY_CUSTOM2] = second
	arrays[Mesh.ARRAY_INDEX] = index
	built.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays, [], {}, format)
	if not g_verts.is_empty():
		var cards := []
		cards.resize(Mesh.ARRAY_MAX)
		cards[Mesh.ARRAY_VERTEX] = g_verts
		cards[Mesh.ARRAY_TEX_UV] = g_uvs
		cards[Mesh.ARRAY_CUSTOM0] = g_hung
		cards[Mesh.ARRAY_CUSTOM1] = g_facts
		cards[Mesh.ARRAY_CUSTOM2] = g_tint
		cards[Mesh.ARRAY_INDEX] = g_index
		built.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, cards, [], {}, format)
	# swinging moves things outside the mesh's own box: leave room
	built.custom_aabb = built.get_aabb().grow(0.12 * size)
	_body.mesh = built
	_apply()
	_send_knocks()


## How many draws the set costs: 1, or 2 with glints.
func draw_count() -> int:
	return _body.mesh.get_surface_count() if _body and _body.mesh else 0


func _model_name(kind: int) -> String:
	return "orn_%s%s" % [KINDS[kind]["name"], "_lo" if low_detail else ""]


func _apply() -> void:
	if _body == null or _body.mesh == null:
		return
	_body.set_instance_shader_parameter(&"sway_amount", deg_to_rad(sway))
	_body.set_surface_override_material(0, _look("ornament", {"shine": shine, "room_light": room_light, "sparkle": sparkle}))
	if _body.mesh.get_surface_count() > 1:
		_body.set_surface_override_material(1, _look("ornament_glint", {"glint_strength": glint}))


## One material for each distinct look, shared by every set that has it.
static func _look(which: String, values: Dictionary) -> ShaderMaterial:
	var key := which + str(values)
	if not _looks.has(key):
		var made := ShaderMaterial.new()
		made.shader = _shaders[which]
		if which == "ornament":
			made.set_shader_parameter(&"paint_sheet", _sheets["ornament_paint"])
			made.set_shader_parameter(&"design_sheet", _sheets["ornament_designs"])
			made.set_shader_parameter(&"shine_sheet", _sheets["ornament_shine"])
		for value: String in values:
			made.set_shader_parameter(value, values[value])
		_looks[key] = made
	return _looks[key]


## Forgets the models, pictures and materials read so far (they are read once and shared by every set).
static func clear_cache() -> void:
	_models.clear()
	_sheets.clear()
	_shaders.clear()
	_looks.clear()


## Reads the models, pictures and shaders, once. Call it on a loading screen (OrnamentSet.preload_all()) to keep
## the first ornament from costing a hitch.
static func preload_all() -> void:
	_load()


static func _load() -> void:
	if not _models.is_empty():
		return
	var home := (OrnamentSet as GDScript).resource_path.get_base_dir()
	for which: String in ["ornament", "ornament_glint"]:
		_shaders[which] = load("%s/%s.gdshader" % [home, which])
	for which: String in ["ornament_paint", "ornament_designs", "ornament_shine"]:
		# The amounts as painted, with mipmaps, whatever the import settings were (no compression: it would smear
		# one amount into another).
		var sheet: Texture2D = load("%s/textures/%s.png" % [home, which])
		var picture := sheet.get_image()
		if picture:
			if picture.is_compressed():
				picture.decompress()
			if which != "ornament_shine" and not picture.has_mipmaps():
				picture.generate_mipmaps()
			sheet = ImageTexture.create_from_image(picture)
		_sheets[which] = sheet
	var scene := load(home + "/models/ornaments.glb") as PackedScene
	var root := scene.instantiate()
	for found in root.find_children("*", "MeshInstance3D", true, false):
		_models[String(found.name)] = _read((found as MeshInstance3D).mesh)
	root.free()


## A model as plain arrays, its surfaces joined, with what the second UVs say about each point unpacked:
## which part (0 body, 1 cap metal, 2 thread), glitter, how far down the thread it is, how glossy.
static func _read(mesh: Mesh) -> Dictionary:
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var uvs := PackedVector2Array()
	var tags := PackedVector2Array()
	var parts := PackedByteArray()
	var glitter := PackedByteArray()
	var glass := PackedByteArray()
	var slack := PackedFloat32Array()
	var threaded := PackedInt32Array()
	var index := PackedInt32Array()
	var low := Vector3.ONE * INF
	var high := Vector3.ONE * -INF
	var hangs := false
	for surface in mesh.get_surface_count():
		var look := mesh.surface_get_material(surface)
		var of_glass := look != null and String(look.resource_name) == "glass"
		var got := mesh.surface_get_arrays(surface)
		var base := verts.size()
		var points: PackedVector3Array = got[Mesh.ARRAY_VERTEX]
		var packed: PackedVector2Array = got[Mesh.ARRAY_TEX_UV2]
		verts.append_array(points)
		normals.append_array(got[Mesh.ARRAY_NORMAL])
		uvs.append_array(got[Mesh.ARRAY_TEX_UV])
		for n in points.size():
			var code := packed[n].x * 16.0
			var part := int(floor(code / 4.0 + 0.0001))
			var rest := code - 4.0 * part
			var glittering := 1 if rest >= 2.0 else 0
			var hang := clampf(rest - 2.0 * glittering - 0.5, 0.0, 1.0)
			parts.append(part)
			glitter.append(1 if of_glass else glittering)
			glass.append(1 if of_glass else 0)
			tags.append(Vector2(1.0 if of_glass else 0.0, clampf(packed[n].y, 0.0, 1.0)))
			slack.append(1.0 - hang)
			if hang > 0.0:
				hangs = true
			if hang < 0.999:
				threaded.append(base + n)
			if part == 0:
				low = low.min(points[n])
				high = high.max(points[n])
		for n: int in got[Mesh.ARRAY_INDEX]:
			index.append(base + n)
	var centre := (low + high) * 0.5
	return {
		"verts": verts, "normals": normals, "uvs": uvs, "tags": tags, "parts": parts, "glitter": glitter, "glass": glass,
		"slack": slack, "threaded": threaded if hangs else PackedInt32Array(), "index": index, "hangs": hangs, "cells": {},
		"centre": centre, "radius": maxf(high.x - low.x, high.z - low.z) * 0.5, "drop": -centre.y, "bottom": low.y,
	}
