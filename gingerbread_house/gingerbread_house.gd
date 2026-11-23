class_name GingerbreadHouse
extends Node3D
## A gingerbread house, made the way real ones are: separate baked slabs (walls, gables, two roof slabs
## that overhang, a chimney of four little slabs) a little out of square, stuck together with piped
## icing along every join, with open doorways, windows cut right through and glazed with sugar glass,
## and a biscuit door standing ajar, on a cake board dusted with icing-sugar snow. Six houses, each
## dressed from a seed with piping and sweets, in any colours.
##
## Add one as a child and set its settings; it builds itself (one mesh, one draw) when it enters the
## tree, and again on the next idle frame after any setting changes. Its origin is the middle of the
## underside of its board, its front faces +z, and the models are in metres: set `size` for a game
## with another unit (12.5 where 1 unit is 8 cm).
##
##   var house := GingerbreadHouse.new()
##   house.kind = GingerbreadHouse.Kind.COTTAGE
##   house.size = 12.5
##   add_child(house)
##
## GingerbreadHouse.make(kind, palette, seed, size) is the same in one line, and
## GingerbreadHouse.village(count, palette, seed, size) a whole lane of them (GingerbreadVillage).

## Which house.
enum Kind {
	COTTAGE,    ## the classic: a gable front with a round-topped door and a window each side, a chimney; 20 x 17 x 22 cm
	TOWNHOUSE,  ## tall and narrow, three floors of windows under a steep roof; 12.5 x 13 x 31 cm
	CHALET,     ## an A-frame: the roof comes right down to the board; 22 x 18 x 22 cm
	CHURCH,     ## a nave with pointed windows and a square tower with a spire at its front; 13 x 27 x 33 cm
	SHOP,       ## a long front with a wide shop window under a striped awning, the door at one end; 24 x 15 x 19 cm
	WONKY,      ## the home-made one: it leans, a roof slab broke and was stuck back, far too much icing; 16 x 14 x 16 cm
}

## The colours of the icing and the sweets.
enum Palette {
	CLASSIC,    ## white icing; red, green and a little gold
	PASTEL,     ## white icing; pink, mint, sky blue, lemon and lilac on paler bread
	SNOW,       ## everything white: white icing, white and silver sweets, pale blue shadows
	CHOCOLATE,  ## dark chocolate bread, cream icing, caramel, milk chocolate and cherry
	CUSTOM,     ## the three custom settings below
}

const KIND_NAMES: Array[String] = ["cottage", "townhouse", "chalet", "church", "shop", "wonky"]
const MODELS := preload("models/gingerbread.glb")
const PICTURE := preload("textures/gingerbread_sheet.png")
const SHADER := preload("gingerbread.gdshader")
const MANIFEST := preload("models/gingerbread_houses.json")

const WHITE := Color(0.97, 0.95, 0.9)
const RED := Color(0.78, 0.08, 0.1)
const GREEN := Color(0.13, 0.5, 0.2)
const GOLD := Color(0.95, 0.74, 0.16)
const PINK := Color(0.97, 0.66, 0.76)
const MINT := Color(0.6, 0.88, 0.74)
const SKY := Color(0.6, 0.8, 0.96)
const LEMON := Color(0.99, 0.92, 0.5)
const LILAC := Color(0.8, 0.7, 0.94)
const BREAD := Color(0.6, 0.35, 0.16)
const CHOCOLATE := Color(0.46, 0.27, 0.15)
const AMBER := Color(0.96, 0.6, 0.13)

## Which of the six houses this is.
@export var kind := Kind.COTTAGE: set = _set_kind
## The colours of the icing and sweets (the bread too, for PASTEL and CHOCOLATE). Default CLASSIC.
@export var palette := Palette.CLASSIC: set = _set_palette
## How heavily it is decorated. 0: bare slabs, the icing in the joins and the door, nothing else.
## 0.3: piped window frames and a few motifs. 0.6 (the default): roof tiles piped on, sweets along
## the ridge and a few on the roof, candy canes at the door, shutters, a few things in the yard.
## 1: encrusted, sweets in rows on the roof, a fence (from 0.65), the yard full.
@export_range(0.0, 1.0, 0.01) var decoration := 0.6: set = _set_decoration
## How much snow (icing sugar and coconut). 0: only the dusting on the board. 0.4 (the default): a
## cap of snow on the upper roof, a few icicles. 1: the roof buried, icicles all along the eaves,
## drifts in the yard, a cap on the chimney.
@export_range(0.0, 1.0, 0.01) var snow := 0.4: set = _set_snow
## How big: 1 for a game in metres (the cottage is 20 cm across), 12.5 for a unit of 8 cm.
@export_range(0.01, 100.0, 0.01, "or_greater") var size := 1.0: set = _set_size
## The low models and fewer sweets, for a house that is small on screen: under half the triangles,
## square edges to the slabs, piping in single straight strips. Default off.
@export var low_detail := false: set = _set_low_detail
## Everything left to chance: which piping, which sweets and where, what stands in the yard. 0: a
## different house each time; any other number: always the same house. Default 1.
@export var seed := 1: set = _set_seed

@export_group("Light inside")
## Whether the house is lit from inside: the sugar-glass panes, the inner walls and floor and a patch
## of snow at the door are drawn glowing warm (painted light: it costs nothing and lights nothing
## else). Off: the panes are plain amber sweets and the inside is dark. Default on.
@export var windows_glow := true: set = _set_windows_glow
## How bright that glow is drawn. 0.4 embers, 1 (the default) candlelight, 2.5 blazing.
@export_range(0.0, 3.0, 0.01) var glow_strength := 1.0: set = _set_glow_strength
## How much the glow wavers, like a candle flame: 0 steady, 1 (the default) a gentle flicker, 3
## guttering. Each house flickers out of step with the others. (It scales the material's own `waver`
## for this house only by switching it on or off: 0 here is steady, anything else follows the material.)
@export_range(0.0, 3.0, 0.01) var flicker := 1.0: set = _set_flicker
## A real light inside as well (an OmniLight3D at the middle of the room), so the glow falls on the
## board, the yard and whatever is near. Off by default: each one is a light the renderer must
## handle (phones manage only a few on one object), and the painted glow already reads as lit.
@export var light_inside := false: set = _set_light_inside
## How strong that light is, for a house of size 1 (it is multiplied by `size`, as Godot thins a
## light by distance in units). 0.05 faint, 0.15 (the default) a candle, 0.6 a lamp. It reaches 35 cm
## at size 1 and casts no shadows, so some of it falls through the walls onto what is near.
@export_range(0.0, 4.0, 0.01, "or_greater") var light_energy := 0.15: set = _set_light_energy
## The colour of that light. Default a candle's orange.
@export var light_colour := Color(1.0, 0.68, 0.34): set = _set_light_colour

@export_group("Parts")
## The biscuit door: 0 shut, 0.35 (the default) standing ajar, 1 wide open against the wall. Its
## hinge is on the left as you face it and it opens outwards.
@export_range(0.0, 1.0, 0.01) var door_ajar := 0.35: set = _set_door_ajar
## Whether it has a door slab at all (off: an open doorway).
@export var door := true: set = _set_door
## Whether it stands on its own cake board. Off: the house alone, set down so that its walls stand on
## your floor (for a board or a table of your own); nothing is put in a yard then.
@export var board := true: set = _set_board
## Whether things stand on the board round it (little iced trees, gingerbread people, a snowman, a
## fence, stepping stones to the door), as `decoration` allows. Default on.
@export var yard := true: set = _set_yard

@export_group("Custom palette")
## For Palette.CUSTOM: the gingerbread itself. Default a mid brown.
@export var custom_bread := BREAD: set = _set_custom_bread
## For Palette.CUSTOM: the royal icing (the joins, the piping, the snow on the roof). Default white.
@export var custom_icing := WHITE: set = _set_custom_icing
## For Palette.CUSTOM: the colours the sweets are dealt from, two or more. The first is also the
## second colour of the piping (dots, hearts, berries). Default red, green, gold.
@export var custom_sweets := PackedColorArray([RED, GREEN, GOLD]): set = _set_custom_sweets

@export_group("Game")
## Give it a StaticBody3D with a box for each length of wall (the doorway left open), so physics
## bodies cannot pass through its walls but can go in at the door. Off by default: nothing here
## needs physics, and wall_footprints() gives the same shapes for a game that keeps its player out
## by sums.
@export var collision := false: set = _set_collision
## Whether it casts a shadow. Default on.
@export var shadows := true: set = _set_shadows

static var _library: Dictionary = {}
static var _material: ShaderMaterial
static var _layers: Dictionary = {}

var _instance: MeshInstance3D
var _body: StaticBody3D
var _lamp: OmniLight3D
var _queued := false
var _own_seed := 0
var _clock := 0.0


## What GingerbreadHouse.add_to() fills: the points of one mesh, however many houses are in it.
class Batch extends RefCounted:
	var v := PackedVector3Array()
	var n := PackedVector3Array()
	var uv := PackedVector2Array()
	var c0 := PackedFloat32Array()
	var c1 := PackedFloat32Array()
	var c2 := PackedFloat32Array()
	var idx := PackedInt32Array()

	## The mesh of everything added so far (null if nothing was).
	func mesh() -> ArrayMesh:
		if v.is_empty():
			return null
		var arrays := []
		arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX] = v
		arrays[Mesh.ARRAY_NORMAL] = n
		arrays[Mesh.ARRAY_TEX_UV] = uv
		arrays[Mesh.ARRAY_CUSTOM0] = c0
		arrays[Mesh.ARRAY_CUSTOM1] = c1
		arrays[Mesh.ARRAY_CUSTOM2] = c2
		arrays[Mesh.ARRAY_INDEX] = idx
		var flags := (Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT) \
				| (Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM1_SHIFT) \
				| (Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM2_SHIFT)
		var made := ArrayMesh.new()
		made.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays, [], {}, flags)
		made.surface_set_material(0, GingerbreadHouse.material())
		return made

	func triangles() -> int:
		return idx.size() / 3


## A house ready to add: GingerbreadHouse.make(GingerbreadHouse.Kind.CHURCH, GingerbreadHouse.Palette.PASTEL, 7, 12.5).
static func make(of_kind: Kind, of_palette := Palette.CLASSIC, of_seed := 1, of_size := 1.0) -> GingerbreadHouse:
	var house := GingerbreadHouse.new()
	house.kind = of_kind
	house.palette = of_palette
	house.seed = of_seed
	house.size = of_size
	return house


## A little village ready to add: `count` houses of mixed kinds along a lane on one snowy board.
static func village(count: int, of_palette := Palette.CLASSIC, of_seed := 1, of_size := 1.0) -> GingerbreadVillage:
	var place := GingerbreadVillage.new()
	place.count = count
	place.palette = of_palette
	place.seed = of_seed
	place.size = of_size
	return place


## Sets several settings at once from a Dictionary by name: house.wear({"palette": ..., "snow": 0.8}).
func wear(dress: Dictionary) -> void:
	for key: String in dress:
		set(key, dress[key])


## This house's settings as a Dictionary (what add_to() takes).
func spec() -> Dictionary:
	if seed == 0 and _own_seed == 0:
		_own_seed = randi_range(1, 1 << 30)
	return {
		"kind": kind, "palette": palette, "decoration": decoration, "snow": snow, "low_detail": low_detail,
		"seed": seed if seed != 0 else _own_seed, "glow": glow_strength if windows_glow else 0.0, "flicker": flicker,
		"door": door, "door_ajar": door_ajar, "board": board, "yard": yard, "sunk": not board,
		"custom_bread": custom_bread, "custom_icing": custom_icing, "custom_sweets": custom_sweets,
	}


# ------------------------------------------------------------------ where things are
## The manifest's notes on a kind of house: its slots, in metres, at size 1 (y up, front +z).
static func notes(of_kind: Kind) -> Dictionary:
	return (MANIFEST.data as Dictionary)["houses"][KIND_NAMES[of_kind]]


## Where this house's own space (metres, as the manifest has it) is in the world.
func frame() -> Transform3D:
	var sunk := 0.0 if board else float((MANIFEST.data as Dictionary)["board_thick"])
	return global_transform * Transform3D(Basis.from_scale(Vector3.ONE * size), Vector3(0.0, -sunk * size, 0.0))


## A footprint from the manifest's {centre, half, height}, put in the world by a frame.
static func print_at(item: Dictionary, in_frame: Transform3D) -> Dictionary:
	var scale_now := in_frame.basis.get_scale()
	var c: Array = item["centre"]
	var h: Array = item["half"]
	var half := Vector2(float(h[0]) * scale_now.x, float(h[1]) * scale_now.z)
	var centre := in_frame * Vector3(c[0], 0.0, c[2])
	return {
		"centre": centre, "round": false, "half": half, "turn": in_frame.basis.get_euler().y, "radius": half.length(),
		"height": float(item["height"]) * scale_now.y,
	}


## The house's footprint on the floor, in the world: one box round all its walls (its board and
## yard not counted). A Dictionary:
##   centre  Vector3, on the floor under its middle
##   round   always false (so that a game can treat it like a Present's footprint)
##   half    Vector2: half its width (along its own x) and half its depth (its own z)
##   turn    how far it is turned about the upright, in radians
##   radius  the circle that holds all of it (for a quick first test)
##   height  how tall the house is
## GingerbreadHouse.blocks(footprint, point, margin) and push_out(footprint, point, margin) use it.
## To let a small walker in at the door use wall_footprints() instead.
func footprint() -> Dictionary:
	return print_at(notes(kind)["box"], frame())


## One thin box for each length of wall, in the world, the doorway left open between them (the same
## Dictionary as footprint(); `height` is how tall that wall is). A walker kept out of these can walk
## in through the door and round the room. Under the low of an A-frame's roof there is a box too.
func wall_footprints() -> Array[Dictionary]:
	return wall_prints_at(kind, frame())


## wall_footprints() for a house that is not a node: its kind, and where its own space is.
static func wall_prints_at(of_kind: Kind, in_frame: Transform3D) -> Array[Dictionary]:
	var out: Array[Dictionary] = []
	for item: Dictionary in notes(of_kind)["solid"]:
		out.append(print_at(item, in_frame))
	return out


## The board's footprint (the same Dictionary; its height is the board's thickness): where the
## yard is. An empty Dictionary if `board` is off.
func board_footprint() -> Dictionary:
	if not board:
		return {}
	var item: Dictionary = notes(kind)["board"].duplicate()
	item["height"] = item["thick"]
	return print_at(item, frame())


## The front doorway, in the world: {centre: Vector3 (on the floor in the middle of the opening, in
## the plane of the wall's outer face), width, height, facing: Vector3 (the way out), inside:
## Vector3 (a place to stand just inside)}.
func doorway() -> Dictionary:
	return doorways()[0]


## Every doorway (each house here has one).
func doorways() -> Array[Dictionary]:
	return doorways_at(kind, frame())


## doorways() for a house that is not a node.
static func doorways_at(of_kind: Kind, in_frame: Transform3D) -> Array[Dictionary]:
	var out: Array[Dictionary] = []
	var scale_now := in_frame.basis.get_scale()
	for item: Dictionary in notes(of_kind)["doors"]:
		var c := _vec(item["c"])
		var n := _vec(item["n"])
		out.append({
			"centre": in_frame * c, "width": float(item["w"]) * scale_now.x, "height": float(item["h"]) * scale_now.y,
			"facing": (in_frame.basis * n).normalized(), "inside": in_frame * (c - n * 0.03),
		})
	return out


## Every window, in the world: {centre: Vector3 (the middle of the opening, on the wall's outer
## face), pane: Vector3 (the middle of its sugar glass), width, height, facing: Vector3 (the way
## out), shape: "rect", "arch", "round" or "lancet"}.
func windows() -> Array[Dictionary]:
	return windows_at(kind, frame())


## windows() for a house that is not a node.
static func windows_at(of_kind: Kind, in_frame: Transform3D) -> Array[Dictionary]:
	var out: Array[Dictionary] = []
	var scale_now := in_frame.basis.get_scale()
	for item: Dictionary in notes(of_kind)["windows"]:
		out.append({
			"centre": in_frame * _vec(item["c"]), "pane": in_frame * _vec(item["pane"]), "width": float(item["w"]) * scale_now.x,
			"height": float(item["h"]) * scale_now.y, "facing": (in_frame.basis * _vec(item["n"])).normalized(), "shape": item["shape"],
		})
	return out


## Where the light inside is, in the world: the middle of the room (to put a light or a flame of
## your own there).
func light_position() -> Vector3:
	return frame() * _vec(notes(kind)["light"])


## Whether a point on the floor is inside a footprint, grown by `margin` (the walker's own radius).
static func blocks(print_: Dictionary, point: Vector3, margin := 0.0) -> bool:
	var centre: Vector3 = print_["centre"]
	var d := Vector2(point.x - centre.x, point.z - centre.z)
	var turn: float = print_["turn"]
	var half: Vector2 = print_["half"]
	var own := Vector2(d.x * cos(turn) - d.y * sin(turn), d.x * sin(turn) + d.y * cos(turn))
	return absf(own.x) < half.x + margin and absf(own.y) < half.y + margin


## The nearest place outside a footprint for a point that is inside it (the point itself if it is
## not): what to set a walker's position to so that it slides along a wall.
static func push_out(print_: Dictionary, point: Vector3, margin := 0.0) -> Vector3:
	if not blocks(print_, point, margin):
		return point
	var centre: Vector3 = print_["centre"]
	var d := Vector2(point.x - centre.x, point.z - centre.z)
	var turn: float = print_["turn"]
	var half: Vector2 = print_["half"] + Vector2(margin, margin)
	var own := Vector2(d.x * cos(turn) - d.y * sin(turn), d.x * sin(turn) + d.y * cos(turn))
	if half.x - absf(own.x) < half.y - absf(own.y):
		own.x = half.x * (1.0 if own.x >= 0.0 else -1.0)
	else:
		own.y = half.y * (1.0 if own.y >= 0.0 else -1.0)
	return Vector3(centre.x + own.x * cos(turn) + own.y * sin(turn), point.y, centre.z - own.x * sin(turn) + own.y * cos(turn))


## Whether a point is in any of this house's walls (the doorway and the room are free).
func blocks_walls(point: Vector3, margin := 0.0) -> bool:
	for print_ in wall_footprints():
		if blocks(print_, point, margin):
			return true
	return false


## A point moved out of this house's walls (twice over, so a corner does not catch it).
func push_out_walls(point: Vector3, margin := 0.0) -> Vector3:
	var prints := wall_footprints()
	for _pass in 2:
		for print_ in prints:
			point = push_out(print_, point, margin)
	return point


## How many triangles this house is drawn with.
func triangles() -> int:
	if _instance == null or _instance.mesh == null:
		return 0
	return _instance.mesh.surface_get_array_index_len(0) / 3


## The one material every house is drawn with. Its uniforms: `sheen` (0 matt .. 1 as painted),
## `candle` (the colour of the glow), `glow_power` (0 .. 4), `waver` (how much the glow flickers).
static func material() -> ShaderMaterial:
	if _material == null:
		_material = ShaderMaterial.new()
		_material.shader = SHADER
		var sheet := PICTURE.get_image()
		if sheet.is_compressed():
			sheet.decompress()
		sheet.convert(Image.FORMAT_RGBA8)
		var grid: Array = (MANIFEST.data as Dictionary)["sheet"]
		var cols := int(grid[0])
		var cell := sheet.get_width() / cols
		var cut: Array[Image] = []
		for i in cols * int(grid[1]):
			var square := sheet.get_region(Rect2i((i % cols) * cell, (i / cols) * cell, cell, cell))
			square.generate_mipmaps()
			cut.append(square)
		var layers := Texture2DArray.new()
		layers.create_from_images(cut)
		_material.set_shader_parameter(&"squares", layers)
	return _material


## Forgets the models and the material (they are read again when next wanted).
static func clear_cache() -> void:
	_library.clear()
	_layers.clear()
	_material = null


# ------------------------------------------------------------------ colours
## The colours of a palette: {bread, bread_dark, flour, icing, accent, sweets: Array[Color], glass,
## snow, shade, foil, wafer, green}. `of` may carry custom_bread, custom_icing and custom_sweets.
static func colours(of_palette: Palette, of: Dictionary = {}) -> Dictionary:
	var look := {
		"bread": BREAD, "icing": WHITE, "sweets": [RED, GREEN, WHITE, GOLD], "glass": AMBER, "snow": Color(0.95, 0.96, 0.98),
		"shade": Color(0.78, 0.85, 0.95), "foil": Color(0.8, 0.82, 0.86), "wafer": Color(0.86, 0.68, 0.42), "green": Color(0.15, 0.48, 0.22),
		"flour": Color(0.93, 0.87, 0.76),
	}
	match of_palette:
		Palette.PASTEL:
			look["bread"] = Color(0.68, 0.44, 0.24)
			look["sweets"] = [PINK, MINT, SKY, LEMON, LILAC]
			look["green"] = Color(0.45, 0.78, 0.6)
			look["foil"] = Color(0.95, 0.8, 0.86)
		Palette.SNOW:
			look["sweets"] = [Color(0.96, 0.97, 1.0), Color(0.8, 0.88, 0.98), Color(0.9, 0.9, 0.93), Color(0.72, 0.8, 0.9)]
			look["green"] = Color(0.9, 0.95, 0.96)
			look["wafer"] = Color(0.93, 0.9, 0.84)
			look["glass"] = Color(0.98, 0.72, 0.3)
		Palette.CHOCOLATE:
			look["bread"] = Color(0.4, 0.23, 0.12)
			look["icing"] = Color(0.96, 0.87, 0.7)
			look["sweets"] = [Color(0.82, 0.52, 0.18), Color(0.44, 0.24, 0.12), Color(0.96, 0.9, 0.78), Color(0.5, 0.06, 0.08)]
			look["green"] = Color(0.5, 0.3, 0.14)
			look["wafer"] = Color(0.8, 0.58, 0.32)
			look["foil"] = Color(0.85, 0.68, 0.34)
			look["flour"] = Color(0.6, 0.42, 0.26)
		Palette.CUSTOM:
			look["bread"] = of.get("custom_bread", BREAD)
			look["icing"] = of.get("custom_icing", WHITE)
			var given: PackedColorArray = of.get("custom_sweets", PackedColorArray([RED, GREEN, GOLD]))
			var dealt: Array = []
			for c in given:
				dealt.append(c)
			if dealt.is_empty():
				dealt = [RED]
			look["sweets"] = dealt
	look["bread_dark"] = (look["bread"] as Color).darkened(0.4)
	look["accent"] = (look["sweets"] as Array)[0]
	return look


# ------------------------------------------------------------------ building
## Adds a house to a batch: `of` is a Dictionary of settings by name (see spec(); anything left out
## is as a new GingerbreadHouse has it), `place` where the middle of its board's underside goes
## (scale it to size it). Many houses added to one batch are one mesh: Batch.mesh().
static func add_to(batch: Batch, of: Dictionary, place: Transform3D) -> void:
	var data: Dictionary = MANIFEST.data
	var which: int = of.get("kind", Kind.COTTAGE)
	var title := KIND_NAMES[which]
	var low: bool = of.get("low_detail", false)
	var slots: Dictionary = data["houses"][title]
	var pieces: Dictionary = _models()[title + ("_lo" if low else "")]["pieces"]
	var thick := float(data["board_thick"])
	var has_board: bool = of.get("board", true)
	var root := place
	if of.get("sunk", not has_board):
		root = place * Transform3D(Basis.IDENTITY, Vector3(0.0, -thick, 0.0))
	var work := Dresser.new()
	work.batch = batch
	work.low = low
	work.look = colours(of.get("palette", Palette.CLASSIC), of)
	work.unit = place.basis.get_scale().x
	work.glow = float(of.get("glow", 1.0))
	work.rng = RandomNumberGenerator.new()
	work.rng.seed = int(of.get("seed", 1)) * 7919 + 31 + which * 101
	work.flame = 0 if float(of.get("flicker", 1.0)) <= 0.0 else 1 + int(work.rng.randi() % 15)
	work.flat_origin = of.get("snow_origin", root.origin)
	work.root = root
	work.put(pieces["shell"], Transform3D.IDENTITY)
	if has_board and pieces.has("board"):
		work.put(pieces["board"], Transform3D.IDENTITY)
	if work.glow > 0.0 and pieces.has("spill") and (has_board or of.get("spill", false)):
		work.put(pieces["spill"], Transform3D.IDENTITY)
	if of.get("door", true) and pieces.has("door"):
		for item: Dictionary in slots["doors"]:
			var u := _vec(item["u"])
			var n := _vec(item["n"])
			var up := n.cross(u).normalized()
			var swing := float(of.get("door_ajar", 0.35)) * deg_to_rad(108.0)
			var hung := Transform3D(Basis(u, up, n) * Basis(Vector3.UP, -swing), _vec(item["hinge"]))
			work.put(pieces["door"], hung)
	work.dress(slots, of, float(data["slab_thick"]), thick)


## Places the pieces of a house into a batch. One is made for each house built.
class Dresser extends RefCounted:
	var batch: Batch
	var look: Dictionary
	var rng: RandomNumberGenerator
	var root: Transform3D
	var low := false
	var unit := 1.0
	var glow := 1.0
	var flame := 0
	var flat_origin := Vector3.ZERO

	## Adds surfaces at a place in the house's own space. opt: ink (three colours for this piece),
	## layer, uv_scale and uv_shift (to pick a patch of a square), cut.
	func put(surfaces: Array, at: Transform3D, opt: Dictionary = {}) -> void:
		GingerbreadHouse._add(batch, surfaces, root * at, self, opt)

	func piece(title: String, at: Transform3D, opt: Dictionary = {}) -> void:
		var models := GingerbreadHouse._models()
		var entry: Dictionary = models[title + ("_lo" if low else "")]
		put(entry["pieces"]["body"], at, opt)

	## Something that sits on a surface: its foot at `at`, its top along `out`, its right along `right`.
	static func on(at: Vector3, out: Vector3, right: Vector3, big := Vector3.ONE, spin := 0.0) -> Transform3D:
		var y := out.normalized()
		var x := (right - y * right.dot(y)).normalized()
		var basis := Basis(x, y, x.cross(y)) * Basis(Vector3.UP, spin)
		return Transform3D(basis.scaled_local(big), at)

	## Something that stands against a wall: its foot at `at`, its right along `u`, its front along `n`.
	static func standing(at: Vector3, u: Vector3, n: Vector3, big := Vector3.ONE) -> Transform3D:
		var up := n.cross(u).normalized()
		return Transform3D(Basis(u.normalized(), up, n.normalized()).scaled_local(big), at)

	## A card of piping: its middle at `at`, `wide` along `right`, `tall` along `rise`, facing `out`
	## and lifted a hair off whatever it lies on. patch: [layer name, u0, v0, how many across, how many up].
	func card(patch: Array, at: Vector3, right: Vector3, rise: Vector3, out: Vector3, wide: float, tall: float, ink: Array, lift := 0.0005) -> void:
		var n := out.normalized()
		var basis := Basis(right.normalized() * wide, n, -rise.normalized() * tall)
		piece("card", Transform3D(basis, at + n * lift), {
			"layer": patch[0], "uv_shift": Vector2(patch[1], patch[2]), "uv_scale": Vector2(patch[3], patch[4]), "ink": ink, "cut": true,
		})

	func sweet_colour(skip := -1) -> Color:
		var all: Array = look["sweets"]
		var pick := rng.randi() % all.size()
		if pick == skip and all.size() > 1:
			pick = (pick + 1) % all.size()
		return all[pick]

	## A sweet stuck on a surface. which: 0 gumdrop, 1 round sweet (a disc of the sweets square), 2 a layered block.
	func sweet(which: int, at: Vector3, out: Vector3, right: Vector3, big := 1.0, colour := Color(0, 0, 0, 0)) -> void:
		var tint := colour if colour.a > 0.0 else sweet_colour()
		var white: Color = look["icing"]
		match which:
			0:
				piece("gumdrop", on(at, out, right, Vector3.ONE * big, rng.randf() * TAU), {"ink": [tint, tint.lerp(Color.WHITE, 0.8), white]})
			1:
				var disc := rng.randi() % 4
				var inks := [tint, white, look["green"]]
				if disc == 2:       # the chocolate button
					inks = [GingerbreadHouse.CHOCOLATE, Color(0.62, 0.4, 0.22), white]
				elif disc == 3:     # the jam biscuit
					inks = [look["wafer"], white, tint]
				piece("disc", on(at, out, right, Vector3.ONE * big, rng.randf() * TAU), {"ink": inks, "uv_shift": Vector2(0.5 * (disc % 2), 0.5 * (disc / 2))})
			_:
				var dark := Color(0.12, 0.09, 0.09) if rng.randf() < 0.5 else sweet_colour()
				piece("allsort", on(at, out, right, Vector3.ONE * big, rng.randf_range(-0.5, 0.5)), {"ink": [white, dark, tint]})

	func motif(title: String) -> Array:
		var data: Dictionary = GingerbreadHouse.MANIFEST.data
		for sheet: String in ["motifs_a", "motifs_b", "motifs_c"]:
			var k: int = (data[sheet] as Array).find(title)
			if k >= 0:
				return [sheet, (k % 3) / 3.0, (k / 3) / 3.0, 1.0 / 3.0, 1.0 / 3.0]
		return ["motifs_a", 0.0, 0.0, 1.0 / 3.0, 1.0 / 3.0]

	func band(title: String, repeats: float) -> Array:
		var span: Array = (GingerbreadHouse.MANIFEST.data as Dictionary)["bands"][title]
		return ["bands", 0.0, float(span[0]) + 0.012, repeats, float(span[1]) - float(span[0]) - 0.024]

	## Dresses a house: piping, sweets, snow and the yard, by rule from the seed.
	func dress(slots: Dictionary, of: Dictionary, slab: float, board_thick: float) -> void:
		var d: float = of.get("decoration", 0.6)
		var s: float = of.get("snow", 0.4)
		var white: Color = look["icing"]
		var accent: Color = look["accent"]
		var piping := [white.darkened(0.25), white, accent]
		var data: Dictionary = GingerbreadHouse.MANIFEST.data
		var tiles: Dictionary = data["tile"]
		var rich := d * (0.6 if low else 1.0)        # how many solid sweets: fewer on the low model
		var roof_pattern: String = ["scallop", "scallop", "lattice", "none"][rng.randi() % 4]
		if d >= 0.75 and roof_pattern == "none":
			roof_pattern = "scallop"
		var roof_sweet := rng.randi() % 4       # 3: a mix
		var band_kind: String = ["zigzag", "loops", "dots", "wave"][rng.randi() % 4]
		var ridge_sweet := rng.randi() % 3
		var up := Vector3.UP
		# ---- the roof
		var cover := lerpf(0.22, 1.0, s) if s > 0.05 else 0.0
		for roof: Dictionary in slots["roofs"]:
			var c := _v(roof["c"])
			var u := _v(roof["u"])
			var v := _v(roof["v"])
			var n := _v(roof["n"])
			var wide := float(roof["w"])
			var long := float(roof["l"])
			if d >= 0.15 and roof_pattern != "none":
				var tile := float(tiles[roof_pattern])
				card([roof_pattern, 0.0, 0.0, (wide - 0.012) / tile, (long - 0.012) / tile], c, u, -v, n, wide - 0.012, long - 0.012, piping)
			if d >= 0.5 and cover < 0.85:
				card(band(band_kind, (wide - 0.01) / float(tiles["bands"])), c + v * (long * 0.5 - 0.012), u, -v, n, wide - 0.01, 0.015, piping, 0.0009)
			if cover > 0.0:
				var deep := 0.0032 * (0.7 + s)
				var basis := Basis(u * (wide + 0.003), n * deep, v * (cover * long))
				piece("roof_snow", Transform3D(basis, c - v * (long * 0.5) + n * 0.0002), {
					"ink": [look["snow"], look["shade"], white], "uv_scale": Vector2(wide / float(tiles["snow"]), cover * long / float(tiles["snow"])),
				})
			if rich >= 0.4 and cover < 0.8:
				var first := cover * long + 0.016
				var rows := int((long - 0.014 - first) / 0.03) + 1
				var budget := int(lerpf(2.0, 14.0, (rich - 0.4) / 0.6))
				for row in rows:
					var along := first + row * 0.03
					if along > long - 0.014:
						break
					var cols := int((wide - 0.03) / 0.034)
					for col in cols:
						if budget <= 0:
							break
						var across := (col - (cols - 1) * 0.5 + (0.5 if row % 2 == 1 else 0.0)) * 0.034
						if absf(across) > wide * 0.5 - 0.014:
							continue
						var kept := false
						for keep: Array in roof["keep"]:
							if Vector2(across - float(keep[0]), along - long * 0.5 - float(keep[1])).length() < float(keep[2]) + 0.008:
								kept = true
						if kept:
							continue
						budget -= 1
						var what := roof_sweet if roof_sweet < 3 else rng.randi() % 3
						sweet(what, c + u * across + v * (along - long * 0.5), n, u, 0.9)
			if roof["eave"] and (s >= 0.25 or d >= 0.7) and not (low and s < 0.5):
				var count := int(wide / (0.024 if low else 0.015) * lerpf(0.35, 1.0, maxf(s, d * 0.7)))
				for i in count:
					var across := rng.randf_range(-0.5, 0.5) * (wide - 0.01)
					var at := c + u * across + v * (long * 0.5 - 0.002) - n * (slab * 0.8)
					var fat := rng.randf_range(0.0018, 0.0032)
					piece("icicle", Transform3D(Basis.from_scale(Vector3(fat, rng.randf_range(0.007, 0.012 + 0.02 * s), fat)), at), {"ink": [white, white, white]})
		for ridge: Dictionary in slots["ridges"]:
			if rich < 0.3:
				break
			var a := _v(ridge["a"])
			var b := _v(ridge["b"])
			var gap := 0.022 if rich >= 0.8 else 0.031
			var count := int(a.distance_to(b) / gap)
			for i in count + 1:
				var at := a.lerp(b, float(i) / maxf(count, 1.0))
				sweet(ridge_sweet, at - up * 0.0012, up, (b - a).normalized(), 0.85, (look["sweets"] as Array)[i % (look["sweets"] as Array).size()])
		for top: Dictionary in slots["chimneys"]:
			if s >= 0.3:
				var r := float(top["r"])
				piece("blob", on(_v(top["top"]) - up * 0.004, up, Vector3.RIGHT, Vector3(r * 1.25, r * 1.5, r * 1.25), rng.randf() * TAU),
						{"ink": [look["snow"], look["shade"], white], "layer": "snow"})
		for tip: Dictionary in slots["finials"]:
			if d >= 0.1:
				sweet(0, _v(tip["p"]), up, Vector3.RIGHT, float(tip["r"]) / 0.0095, accent)
		# ---- the walls
		for wall: Dictionary in slots["walls"]:
			if wall["role"] == "hidden":
				continue
			var c := _v(wall["c"])
			var u := _v(wall["u"])
			var n := _v(wall["n"])
			var rise := n.cross(u).normalized()
			var wide := float(wall["w"])
			var high := float(wall["h"])
			var holes: Array = wall["holes"]
			if d >= 0.45 and high > 0.04 and float(wall["peak"]) <= 0.0:
				var clear := true
				for hole: Array in holes:
					if float(hole[3]) > high - 0.024:
						clear = false
				if clear:
					card(band(band_kind, (wide - 0.02) / float(tiles["bands"])), c + rise * (high - 0.013), u, rise, n, wide - 0.02, 0.014, piping)
			if d >= 0.55 and high > 0.04:
				for attempt in int(lerpf(2.0, 6.0, d)):
					var x := rng.randf_range(-0.5, 0.5) * (wide - 0.05)
					var y := rng.randf_range(0.018, high - 0.03)
					var free := true
					for hole: Array in holes:
						if x > float(hole[0]) - 0.026 and x < float(hole[2]) + 0.026 and y > float(hole[1]) - 0.024 and y < float(hole[3]) + 0.024:
							free = false
					if free:
						card(motif("bricks"), c + u * x + rise * y, u, rise, n, 0.026, 0.022, piping)
		for spot: Dictionary in slots["spots"]:
			if d < 0.2 or rng.randf() > lerpf(0.55, 1.0, d):
				continue
			var p := _v(spot["p"])
			var u := _v(spot["u"])
			var n := _v(spot["n"])
			var rise := n.cross(u).normalized()
			var r := float(spot["r"])
			if rich >= 0.4 and rng.randf() < 0.45:
				sweet(1, p, n, u, clampf(r / 0.012, 0.6, 1.5))
			else:
				var names := ["heart", "snowflake", "star", "swirl", "holly", "wreath", "fir", "flower", "burst"]
				card(motif(names[rng.randi() % names.size()]), p, u, rise, n, r * 2.1, r * 2.1, piping)
		for hole: Dictionary in slots["windows"]:
			if d < 0.05:
				break
			var c := _v(hole["c"])
			var pane := _v(hole["pane"])
			var u := _v(hole["u"])
			var n := _v(hole["n"])
			var rise := n.cross(u).normalized()
			var wide := float(hole["w"])
			var high := float(hole["h"])
			match String(hole["shape"]):
				"round":
					card(motif("ring_round"), c, u, rise, n, (wide + 0.005) / 0.78, (wide + 0.005) / 0.78, piping)
				"arch":
					card(motif("ring_arch"), c, u, rise, n, (wide + 0.005) / 0.7, (high + 0.005) / 0.85, piping)
				"lancet":
					card(motif("ring_tall"), c + rise * (high * 0.006), u, rise, n, (wide + 0.005) / 0.52, (high + 0.005) / 0.89, piping)
				_:
					card(motif("ring_square"), c, u, rise, n, (wide + 0.005) / 0.8, (high + 0.005) / 0.8, piping)
			if d >= 0.35 and rng.randf() < 0.55:
				var tile := float(tiles["lattice"]) * 0.7
				card(["lattice", rng.randf(), rng.randf(), wide / tile, high / tile], pane, u, rise, n, wide, high, piping, 0.0004)
			elif d >= 0.12:
				card(motif("cross"), pane, u, rise, n, wide, high, piping, 0.0004)
			if d >= 0.3 and hole["shutters"]:
				for side: float in [-1.0, 1.0]:
					var at := c + u * (side * (wide * 0.5 + 0.0085)) - rise * (high * 0.5 + 0.002) + n * 0.0016
					piece("wafer", standing(at, u, n, Vector3(0.82, (high + 0.004) / 0.045, 1.0)), {"ink": [look["wafer"], (look["wafer"] as Color).darkened(0.3), white]})
			if rich >= 0.7 and String(hole["shape"]) != "lancet":
				for k in 3:
					sweet(0, c + u * ((k - 1) * 0.011) - rise * (high * 0.5 + 0.009), n, u, 0.5)
		for item: Dictionary in slots["doors"]:
			var c := _v(item["c"])
			var u := _v(item["u"])
			var n := _v(item["n"])
			var rise := n.cross(u).normalized()
			var wide := float(item["w"])
			var high := float(item["h"])
			if d >= 0.15:
				var tall := (high + 0.005) / 0.91
				card(motif("door_arch"), c + rise * (tall * 0.485), u, rise, n, (wide + 0.009) / 0.82, tall, piping)
			if rich >= 0.3 and item["canes"]:
				var big := high * 0.95 / 0.0445
				var stripe: Color = (look["sweets"] as Array)[0]
				for side: float in [-1.0, 1.0]:
					var at := c + u * (side * (wide * 0.5 + 0.0095)) + n * 0.0036
					piece("cane", Transform3D(Basis(u * -side, rise, n).scaled_local(Vector3.ONE * big), at), {"ink": [white, stripe, look["green"]]})
		for extra: Dictionary in slots["blobs"]:
			var r := float(extra["r"])
			piece("blob", on(_v(extra["p"]), _v(extra["n"]), Vector3.RIGHT, Vector3(r, r * 1.3, r), rng.randf() * TAU), {"ink": [white, white, white]})
		# ---- the yard
		if not of.get("board", true) and not of.get("yard_without_board", false):
			return
		if not of.get("yard", true):
			return
		var places: Array = slots["yard"].duplicate()
		for i in range(places.size() - 1, 0, -1):
			var j := rng.randi() % (i + 1)
			var held: Variant = places[i]
			places[i] = places[j]
			places[j] = held
		var filled := int(round(places.size() * clampf((d - 0.25) / 0.7, 0.0, 1.0)))
		var snowman_done := false
		for i in places.size():
			var spot: Dictionary = places[i]
			var p := _v(spot["p"])
			var r := float(spot["r"])
			if i >= filled:
				if s >= 0.5 and rng.randf() < s:
					piece("blob", on(p, up, Vector3.RIGHT, Vector3(r * 1.5, r * 0.9, r * 1.2), rng.randf() * TAU), {"ink": [look["snow"], look["shade"], white], "layer": "snow"})
				continue
			if yard_thing(p, r, not snowman_done):
				snowman_done = true
		if d >= 0.2:
			var k := 0
			for stone: Dictionary in slots["path"]:
				k += 1
				var inks := [GingerbreadHouse.CHOCOLATE, Color(0.62, 0.4, 0.22), white] if k % 2 == 0 else [look["wafer"], white, accent]
				piece("disc", on(_v(stone["p"]), up, Vector3.RIGHT, Vector3(0.9, 0.55, 0.9), rng.randf() * TAU), {"ink": inks, "uv_shift": Vector2(0.0 if k % 2 == 0 else 0.5, 0.5)})
		if d >= 0.65 and not low:
			var pickets := rng.randf() < 0.6
			for run: Dictionary in slots["fences"]:
				GingerbreadHouse.fence(self, _v(run["a"]), _v(run["b"]), pickets)

	## Something to stand in a yard at p, in a space r in radius: an iced tree, a gingerbread person, a
	## snowman (if `snowman` allows), a lollipop or a few gumdrops. True if it was a snowman.
	func yard_thing(p: Vector3, r: float, snowman := true) -> bool:
		var up := Vector3.UP
		var white: Color = look["icing"]
		var accent: Color = look["accent"]
		var roll := rng.randf()
		var turn := rng.randf_range(-0.5, 0.5)
		if roll < 0.42:
			var big := r / 0.02 * rng.randf_range(0.85, 1.2)
			piece("fir", on(p, up, Vector3.RIGHT, Vector3.ONE * big, rng.randf() * TAU), {"ink": [look["green"], white, accent]})
			sweet(0, p + up * (0.062 * big), up, Vector3.RIGHT, 0.42 * big, (look["sweets"] as Array)[(look["sweets"] as Array).size() - 1])
		elif roll < 0.62 and r >= 0.013:
			var big := minf(1.0, r / 0.02) * 0.85
			var lean := Basis(Vector3.RIGHT, -0.14)
			piece("person", Transform3D(Basis(Vector3.UP, turn) * lean * Basis.from_scale(Vector3.ONE * big), p), {"ink": [look["bread"], white, accent]})
		elif roll < 0.8 and r >= 0.016 and snowman:
			piece("snowman", Transform3D(Basis(Vector3.UP, turn).scaled_local(Vector3.ONE * (r / 0.0145)), p), {"ink": [Color(0.97, 0.96, 0.94), Color(0.12, 0.1, 0.1), Color(0.95, 0.5, 0.1)]})
			return true
		elif roll < 0.9:
			# a lollipop: a round sweet on a stick
			var tall := r * 2.2
			piece("stick", Transform3D(Basis.from_scale(Vector3(0.8, tall / 0.05, 0.8)), p), {"ink": [Color(0.95, 0.93, 0.88), Color(0.8, 0.78, 0.72), white]})
			var tint := sweet_colour()
			piece("disc", Transform3D(Basis(Vector3.UP, turn) * Basis(Vector3.RIGHT, PI * 0.5) * Basis.from_scale(Vector3.ONE * (r / 0.012)), p + up * (tall + r * 0.5) + Vector3(0, 0, -0.0025)),
					{"ink": [tint, white, look["green"]], "uv_shift": Vector2(0.5 * (rng.randi() % 2), 0.0)})
		else:
			for k in 3:
				sweet(0, p + Vector3(rng.randf_range(-1, 1), 0.0, rng.randf_range(-1, 1)) * r * 0.6, up, Vector3.RIGHT, rng.randf_range(0.7, 1.0))
		return false

	func _v(a: Array) -> Vector3:
		return Vector3(a[0], a[1], a[2])


## A fence from a to b (in the Dresser's space): wafer pickets, or pretzel-stick posts and a rail.
static func fence(work: Dresser, a: Vector3, b: Vector3, pickets: bool) -> void:
	var long := a.distance_to(b)
	if long < 0.02:
		return
	var along := (b - a).normalized()
	var out := along.cross(Vector3.UP).normalized()
	var wafer: Color = work.look["wafer"]
	if pickets:
		var count := int(long / 0.023)
		for i in count + 1:
			var at := a.lerp(b, float(i) / maxf(count, 1.0))
			var tall := work.rng.randf_range(0.5, 0.62)
			var lean := Basis(along, work.rng.randf_range(-0.08, 0.08))
			work.piece("wafer", Transform3D(lean * Basis(along, Vector3.UP, along.cross(Vector3.UP)).scaled_local(Vector3(0.78, tall, 1.0)), at),
					{"ink": [wafer, wafer.darkened(0.3), Color.WHITE]})
	else:
		var brown := [Color(0.5, 0.27, 0.1), Color(0.34, 0.16, 0.06), Color(0.97, 0.95, 0.9)]
		var count := maxi(1, int(long / 0.03))
		for i in count + 1:
			var at := a.lerp(b, float(i) / count)
			work.piece("stick", Transform3D(Basis.from_scale(Vector3(1.0, 0.56, 1.0)), at), {"ink": brown})
		for high: float in [0.012, 0.022]:
			var lying := Basis(out, along, out.cross(along)).scaled_local(Vector3(0.9, long / 0.05, 0.9))
			work.piece("stick", Transform3D(lying, a + Vector3.UP * high + out * 0.0024), {"ink": brown})


func _ready() -> void:
	_build()


func _process(delta: float) -> void:
	if _lamp == null:
		set_process(false)
		return
	_clock += delta
	var quiver := sin(_clock * 7.3) * 0.5 + sin(_clock * 12.7) * 0.3 + sin(_clock * 2.9) * 0.4
	_lamp.light_energy = light_energy * size * (1.0 + 0.13 * flicker * quiver)


func _build() -> void:
	_queued = false
	if not is_inside_tree():
		return
	if _instance == null:
		_instance = MeshInstance3D.new()
		_instance.name = "Mesh"
		add_child(_instance)
	var batch := Batch.new()
	add_to(batch, spec(), Transform3D(Basis.from_scale(Vector3.ONE * size), Vector3.ZERO))
	_instance.mesh = batch.mesh()
	_instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if shadows else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var sunk := 0.0 if board else float((MANIFEST.data as Dictionary)["board_thick"])
	if light_inside:
		if _lamp == null:
			_lamp = OmniLight3D.new()
			_lamp.name = "Candle"
			add_child(_lamp)
		_lamp.position = (_vec(notes(kind)["light"]) - Vector3(0.0, sunk, 0.0)) * size
		_lamp.light_color = light_colour
		_lamp.light_energy = light_energy * size
		_lamp.omni_range = 0.35 * size
		_lamp.omni_attenuation = 1.6
		_lamp.shadow_enabled = false
	elif _lamp != null:
		_lamp.queue_free()
		remove_child(_lamp)
		_lamp = null
	set_process(_lamp != null and flicker > 0.0)
	if _body != null:
		_body.queue_free()
		remove_child(_body)
		_body = null
	if collision:
		_body = StaticBody3D.new()
		_body.name = "Walls"
		for item: Dictionary in notes(kind)["solid"]:
			var c: Array = item["centre"]
			var h: Array = item["half"]
			var tall := float(item["height"])
			var held := CollisionShape3D.new()
			var shape := BoxShape3D.new()
			shape.size = Vector3(float(h[0]) * 2.0, tall, float(h[1]) * 2.0) * size
			held.shape = shape
			held.position = (Vector3(c[0], float((MANIFEST.data as Dictionary)["board_thick"]) + tall * 0.5, c[2]) - Vector3(0.0, sunk, 0.0)) * size
			_body.add_child(held)
		add_child(_body)


func _rebuild() -> void:
	if is_inside_tree() and not _queued:
		_queued = true
		_build.call_deferred()


# ------------------------------------------------------------------ what houses share
static func _vec(a: Array) -> Vector3:
	return Vector3(a[0], a[1], a[2])


static func _layer(title: String) -> float:
	if _layers.is_empty():
		var names: Array = (MANIFEST.data as Dictionary)["layers"]
		for i in names.size():
			_layers[names[i]] = float(i)
	return _layers.get(title, 0.0)


## Every model in the .glb by name: {pieces: {shell: [surface, ...], board: ..., body: ...}}. A
## surface is {kind: the Blender material's name, v, n, uv, c (tone and glow), idx}.
static func _models() -> Dictionary:
	if not _library.is_empty():
		return _library
	var scene: Node = (MODELS as PackedScene).instantiate()
	for top in scene.get_children():
		var title := String(top.name)
		var pieces := {}
		for child in top.get_children():
			var what := String(child.name).trim_prefix(title + "_")
			var holder := child as MeshInstance3D
			if holder == null:
				continue
			var surfaces: Array = []
			for i in holder.mesh.get_surface_count():
				var arrays := holder.mesh.surface_get_arrays(i)
				var worn := holder.mesh.surface_get_material(i)
				var idx := PackedInt32Array()
				if arrays[Mesh.ARRAY_INDEX] != null:
					idx = arrays[Mesh.ARRAY_INDEX]
				else:
					for k in (arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array).size():
						idx.append(k)
				var tint := PackedColorArray()
				if arrays[Mesh.ARRAY_COLOR] != null:
					tint = arrays[Mesh.ARRAY_COLOR]
				surfaces.append({
					"kind": String(worn.resource_name) if worn != null else "bread",
					"v": arrays[Mesh.ARRAY_VERTEX], "n": arrays[Mesh.ARRAY_NORMAL], "uv": arrays[Mesh.ARRAY_TEX_UV], "c": tint, "idx": idx,
				})
			pieces[what] = surfaces
		_library[title] = {"pieces": pieces}
	scene.free()
	return _library


## What a kind of surface wears: [square, base, print, accent, shine kept, how much of the light
## inside it shows].
static func _wears(kind_of: String, work: Dresser, opt: Dictionary) -> Array:
	var look := work.look
	var ink: Array = opt.get("ink", [])
	var white: Color = look["icing"]
	var bread: Color = look["bread"]
	var first: Color = ink[0] if ink.size() > 0 else white
	var second: Color = ink[1] if ink.size() > 1 else white
	var third: Color = ink[2] if ink.size() > 2 else white
	match kind_of:
		"bread":
			return ["bread", bread, look["bread_dark"], look["flour"], 1.0, 0.55]
		"inside":
			return ["bread", bread.lightened(0.06), look["bread_dark"], look["flour"], 1.0, 0.6]
		"icing":
			return ["icing", white, white, white, 1.0, 0.0]
		"glass":
			return ["glass", look["glass"], (look["glass"] as Color).lerp(Color(1.0, 0.95, 0.7), 0.6), white, 1.0, 1.7]
		"floor":
			return ["plain", Color(0.8, 0.72, 0.58), white, white, 0.5, 0.5]
		"awning":
			return ["stripes", white, (look["sweets"] as Array)[0], look["green"], 0.4, 0.0]
		"biscuit":
			return ["cookie", bread.lightened(0.1), white, look["accent"], 1.0, 0.0]
		"snow_flat":
			return ["snow", look["snow"], look["shade"], white, 1.0, 0.55]
		"foil":
			return ["foil", look["foil"], (look["foil"] as Color).lightened(0.5), white, 1.0, 0.0]
		"snow":
			return ["snow", first, second, third, 1.0, 0.0]
		"blob":
			return [opt.get("layer", "icing"), first, second, third, 1.0, 0.0]
		"sugar":
			return ["sugar", first, second, third, 1.0, 0.0]
		"disc":
			return ["sweets", first, second, third, 1.0, 0.0]
		"stripes":
			return ["stripes", first, second, third, 1.0, 0.0]
		"allsort":
			return ["parts", first, second, third, 1.0, 0.0]
		"allsort_top":
			return ["plain", first, first, first, 1.0, 0.0]
		"wafer":
			return ["wafer", first, second, third, 1.0, 0.0]
		"pretzel":
			return ["bread", first, second, third, 3.0, 0.0]
		"marsh":
			return ["plain", first, first, first, 0.6, 0.0]
		"face", "buttons":
			return ["parts", first, second, third, 0.6, 0.0]
		"person":
			return ["cookie", first, second, third, 1.0, 0.0]
		"fir":
			return ["tree", first, second, third, 1.0, 0.0]
		"card":
			return [opt.get("layer", "motifs_a"), first, second, third, 1.0, 0.0]
	return ["plain", first, second, third, 1.0, 0.0]


static func _add(batch: Batch, surfaces: Array, place: Transform3D, work: Dresser, opt: Dictionary) -> void:
	var turn := place.basis.inverse().transposed()
	var mirrored := place.basis.determinant() < 0.0
	var uv_scale: Vector2 = opt.get("uv_scale", Vector2.ONE)
	var uv_shift: Vector2 = opt.get("uv_shift", Vector2.ZERO)
	var cut := 2.0 if opt.get("cut", false) else 0.0
	var region: Dictionary = (MANIFEST.data as Dictionary)["region"]
	var snow_tile := float((MANIFEST.data as Dictionary)["tile"]["snow"]) * work.unit
	for surface: Dictionary in surfaces:
		var kind_of: String = surface["kind"]
		var wears := _wears(kind_of, work, opt)
		var square := _layer(wears[0])
		var base := (wears[1] as Color).srgb_to_linear()
		var printed := (wears[2] as Color).srgb_to_linear()
		var accent := (wears[3] as Color).srgb_to_linear()
		var shine: float = minf(float(wears[4]), 1.0) + cut
		var lit: float = float(wears[5]) * work.glow
		var flat := kind_of == "snow_flat"
		var scale_now := uv_scale
		var shift_now := uv_shift
		if kind_of == "allsort" or kind_of == "allsort_top":
			var patch: Array = region["allsort"]
			scale_now = Vector2(float(patch[2]) - float(patch[0]), float(patch[3]) - float(patch[1])) * 0.96
			shift_now = Vector2(float(patch[0]) + 0.01, float(patch[1]) + 0.01)
		var v: PackedVector3Array = surface["v"]
		var n: PackedVector3Array = surface["n"]
		var uv: PackedVector2Array = surface["uv"]
		var c: PackedColorArray = surface["c"]
		var idx: PackedInt32Array = surface["idx"]
		var first := batch.v.size()
		var count := v.size()
		batch.v.resize(first + count)
		batch.n.resize(first + count)
		batch.uv.resize(first + count)
		batch.c0.resize((first + count) * 4)
		batch.c1.resize((first + count) * 4)
		batch.c2.resize((first + count) * 4)
		var tinted := c.size() == count
		for i in count:
			var at := first + i
			var p := place * v[i]
			batch.v[at] = p
			batch.n[at] = (turn * n[i]).normalized()
			if flat:
				batch.uv[at] = Vector2(p.x - work.flat_origin.x, p.z - work.flat_origin.z) / snow_tile
			else:
				var own := Vector2(uv[i].x, 1.0 - uv[i].y) * scale_now + shift_now
				batch.uv[at] = Vector2(own.x, 1.0 - own.y)
			var tone := c[i].r if tinted else 1.0
			var shows := c[i].g * lit if tinted else 0.0
			var o := at * 4
			batch.c0[o] = base.r * tone
			batch.c0[o + 1] = base.g * tone
			batch.c0[o + 2] = base.b * tone
			batch.c0[o + 3] = square
			batch.c1[o] = printed.r * tone
			batch.c1[o + 1] = printed.g * tone
			batch.c1[o + 2] = printed.b * tone
			batch.c1[o + 3] = shine
			batch.c2[o] = accent.r
			batch.c2[o + 1] = accent.g
			batch.c2[o + 2] = accent.b
			batch.c2[o + 3] = minf(shows, 3.9) + (4.0 * work.flame if shows > 0.0 else 0.0)
		var start := batch.idx.size()
		batch.idx.resize(start + idx.size())
		if mirrored:
			for i in range(0, idx.size(), 3):
				batch.idx[start + i] = first + idx[i]
				batch.idx[start + i + 1] = first + idx[i + 2]
				batch.idx[start + i + 2] = first + idx[i + 1]
		else:
			for i in idx.size():
				batch.idx[start + i] = first + idx[i]


# ------------------------------------------------------------------ settings
func _set_kind(value: Kind) -> void:
	kind = value
	_rebuild()


func _set_palette(value: Palette) -> void:
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


func _set_low_detail(value: bool) -> void:
	low_detail = value
	_rebuild()


func _set_seed(value: int) -> void:
	seed = value
	_rebuild()


func _set_windows_glow(value: bool) -> void:
	windows_glow = value
	_rebuild()


func _set_glow_strength(value: float) -> void:
	glow_strength = value
	_rebuild()


func _set_flicker(value: float) -> void:
	flicker = value
	_rebuild()


func _set_light_inside(value: bool) -> void:
	light_inside = value
	_rebuild()


func _set_light_energy(value: float) -> void:
	light_energy = value
	_rebuild()


func _set_light_colour(value: Color) -> void:
	light_colour = value
	_rebuild()


func _set_door_ajar(value: float) -> void:
	door_ajar = value
	_rebuild()


func _set_door(value: bool) -> void:
	door = value
	_rebuild()


func _set_board(value: bool) -> void:
	board = value
	_rebuild()


func _set_yard(value: bool) -> void:
	yard = value
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


func _set_collision(value: bool) -> void:
	collision = value
	_rebuild()


func _set_shadows(value: bool) -> void:
	shadows = value
	_rebuild()
