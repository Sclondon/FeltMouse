class_name Present
extends Node3D
## A wrapped present: one of eight Blender models (four boxes with the paper folded and taped at
## their ends, a pleated drum, a gift bag with rope handles and tissue, a round hat box with a lid, a
## lumpy parcel tied with string), wearing one of ten printed papers in its own colours, tied with
## ribbon one of three ways, with one of four bows and a blank tag. This node is at the present's
## foot, on the floor.
##
##     var gift := Present.new()
##     gift.shape = Present.Shape.TALL_BOX
##     gift.paper = Present.Paper.HOLLY
##     gift.paper_colour = Color(0.96, 0.91, 0.79)
##     gift.print_colour = Color(0.11, 0.34, 0.19)
##     gift.accent_colour = Color(0.7, 0.09, 0.1)
##     gift.ribbon_colour = Color(0.7, 0.09, 0.1)
##     gift.size = 12.5              # the models are in metres: 12.5 for a game whose unit is 8 cm
##     add_child(gift)
##     var keep_out := gift.footprint()      # see footprint(), blocks() and push_out()
##
## A present is ONE mesh and one draw, whatever it wears: every colour is carried by its points and
## every present shares one material, one shader and one picture. A heap of them is one draw too:
## see PresentPile (Present.pile(...)).

enum Shape {
	CUBE,       ## a cube, 16 cm
	SHIRT_BOX,  ## a flat box, 30 x 22 x 6 cm
	TALL_BOX,   ## a box standing up, 12 x 12 x 26 cm, its folded ends at top and bottom
	LONG_BOX,   ## a long thin box, 36 x 9 x 8 cm
	DRUM,       ## a round tin, 18 cm across, the paper pleated over its top to a sticker
	BAG,        ## a paper gift bag, 18 x 9 x 22 cm, with rope handles and tissue standing out of it
	HAT_BOX,    ## a round hat box, 25 cm across, with a lid that can stand ajar on tissue
	PARCEL,     ## something awkward wrapped anyway: a lump, tied both ways with string
}

enum Paper {
	STRIPES,  ## stripes, with a thin line of the accent beside each
	CANDY,    ## slanting candy stripes, two thin accent lines between
	DOTS,     ## polka dots, the accent a crescent beside each (a second ink a little out of place)
	STARS,    ## stars big and small, the accent small dots
	SNOW,     ## snowflakes, the accent specks of snow
	HOLLY,    ## holly sprigs in the print colour, their berries in the accent
	TREES,    ## little fir trees, their star, trunk and baubles in the accent
	PLAID,    ## tartan: woven bands of the print colour, thin lines of the accent
	KRAFT,    ## plain brown paper: the print colour is only its flecks and ribs
	FOIL,     ## a crinkled foil-like plain paper: the print colour is its glints
}

enum Ribbon {
	CROSS,     ## both ways round, crossing on top (on the parcel: string)
	BAND,      ## once round (round the middle of the drum and the hat box)
	DIAGONAL,  ## across two opposite corners of a box (the round ones wear BAND instead)
	NONE,      ## no ribbon
}

enum Finish {
	SATIN,  ## satin with a woven edge
	FOIL,   ## painted to look like gold or silver foil ribbon: streaks of light along it
}

enum Bow {
	NONE,
	CLASSIC,  ## two loops, a knot and two swallow-tailed ends
	POMPOM,   ## a pom-pom of many loops
	ROSETTE,  ## a flat stick-on rosette of pointed petals
	STRING,   ## string tied in a bow
}

enum BowPlace {
	AUTO,    ## on the ribbon: on the corner band of a DIAGONAL tie, otherwise the middle of the top
	TOP,     ## the middle of the top (on the bag: its front)
	CORNER,  ## towards a corner of the top
	SIDE,    ## on its front face (the flat boxes have no room there: towards an end of the top)
}

enum Palette {
	CLASSIC,          ## red, green, cream and gold
	PASTEL,           ## pink, mint, sky blue, lemon, lilac and white
	KRAFT_AND_RED,    ## brown paper, red and white, string
	BLUE_AND_SILVER,  ## navy, ice blue, silver and white
	CUSTOM,           ## colours you give
}

const SHAPE_NAMES: Array[String] = ["cube", "shirt_box", "tall_box", "long_box", "drum", "bag", "hat_box", "parcel"]
const BOW_NAMES: Array[String] = ["", "bow_classic", "bow_pompom", "bow_rosette", "bow_string"]
## Which shapes are round (their footprint is a circle).
const ROUND: Array[bool] = [false, false, false, false, true, false, true, false]
## Which shapes something else can be stood on.
const FLAT_TOPPED: Array[bool] = [true, true, true, true, true, false, true, false]
const MODELS := preload("models/presents.glb")
const PICTURE := preload("textures/presents_papers.png")
const SHADER := preload("presents.gdshader")
# the squares of the picture after the ten papers
const SQUARE_SATIN := 10
const SQUARE_RIBBON_FOIL := 11
const SQUARE_TWINE := 12
const SQUARE_TISSUE := 13
const SQUARE_PARTS := 14
const SQUARE_PLAIN := 15

const RED := Color(0.7, 0.09, 0.1)
const GREEN := Color(0.11, 0.34, 0.19)
const CREAM := Color(0.96, 0.91, 0.79)
const GOLD := Color(0.9, 0.72, 0.3)
const WHITE := Color(0.96, 0.96, 0.94)
const PINK := Color(0.96, 0.72, 0.78)
const MINT := Color(0.68, 0.89, 0.79)
const SKY := Color(0.68, 0.83, 0.95)
const LEMON := Color(0.98, 0.93, 0.62)
const LILAC := Color(0.82, 0.74, 0.93)
const BROWN_PAPER := Color(0.66, 0.5, 0.34)
const DARK_BROWN := Color(0.45, 0.31, 0.19)
const JUTE := Color(0.88, 0.81, 0.66)
const NAVY := Color(0.09, 0.16, 0.4)
const ICE := Color(0.62, 0.78, 0.92)
const SILVER := Color(0.76, 0.79, 0.84)
## The palettes: each row is a present's paper colour, print colour, accent colour and ribbon colour.
const WAYS := [
	[[RED, CREAM, GOLD, GOLD], [GREEN, CREAM, RED, RED], [CREAM, RED, GREEN, GREEN], [CREAM, GREEN, RED, RED],
			[GOLD, CREAM, RED, RED], [RED, GOLD, GREEN, CREAM], [GREEN, GOLD, RED, GOLD]],
	[[PINK, WHITE, LILAC, WHITE], [MINT, WHITE, PINK, PINK], [SKY, WHITE, LEMON, LEMON], [LEMON, PINK, MINT, MINT],
			[LILAC, WHITE, LEMON, WHITE], [WHITE, PINK, MINT, SKY]],
	[[BROWN_PAPER, WHITE, RED, RED], [BROWN_PAPER, RED, WHITE, RED], [BROWN_PAPER, DARK_BROWN, RED, JUTE],
			[RED, WHITE, BROWN_PAPER, CREAM], [BROWN_PAPER, GREEN, RED, RED], [BROWN_PAPER, DARK_BROWN, RED, RED]],
	[[NAVY, SILVER, WHITE, SILVER], [ICE, WHITE, NAVY, WHITE], [SILVER, WHITE, NAVY, NAVY], [WHITE, NAVY, ICE, ICE],
			[NAVY, WHITE, ICE, WHITE], [ICE, NAVY, WHITE, SILVER]],
]
## The papers each palette deals from (a paper named twice comes up twice as often).
const PAPERS_OF := [
	[Paper.STRIPES, Paper.CANDY, Paper.DOTS, Paper.STARS, Paper.HOLLY, Paper.TREES, Paper.PLAID, Paper.SNOW, Paper.FOIL],
	[Paper.STRIPES, Paper.CANDY, Paper.DOTS, Paper.STARS, Paper.SNOW, Paper.TREES, Paper.DOTS],
	[Paper.KRAFT, Paper.KRAFT, Paper.KRAFT, Paper.DOTS, Paper.STARS, Paper.STRIPES, Paper.HOLLY, Paper.TREES, Paper.SNOW],
	[Paper.SNOW, Paper.SNOW, Paper.STARS, Paper.DOTS, Paper.STRIPES, Paper.CANDY, Paper.PLAID, Paper.FOIL, Paper.TREES],
]

## Which present it is (see Shape): a cube by default.
@export var shape := Shape.CUBE: set = _set_shape
## How big it is. The models are made in metres (the cube is 16 cm), so 1 suits a game counted in metres
## and 12.5 a game whose unit is 8 cm. 0.5 is a present half the real size, 3 a giant one. Default 1.
@export_range(0.01, 100.0, 0.01, "or_greater") var size := 1.0: set = _set_size
## Draw the low model: about a quarter of the triangles (a box with its ribbon is about 50 in place
## of 220), no rounded edges, no tape, flat ribbon. For presents that are small on screen. Default off.
@export var low_detail := false: set = _set_low_detail
## A number that sets everything left to chance here (how it leans and sags, which way its bow is
## turned). The same settings and the same seed give the same present. 0 (the default) gives every
## present its own.
@export var seed := 0: set = _set_seed

@export_group("Paper")
## The printed pattern (see Paper). Default DOTS.
@export var paper := Paper.DOTS: set = _set_paper
## The colour of the paper itself, between the print. Default a Christmas red.
@export var paper_colour := RED: set = _set_paper_colour
## The colour of the printed pattern (the dots, stripes, trees). On KRAFT paper it is only the flecks,
## on FOIL the glints: there a paler shade of the paper colour looks best. Default cream.
@export var print_colour := CREAM: set = _set_print_colour
## The colour of the second ink: holly berries, the stars on the trees, the thin lines beside stripes,
## the crescent beside each dot. Set it to the paper colour to print in one ink only. Default gold.
@export var accent_colour := GOLD: set = _set_accent_colour
## How big the pattern is printed. 1 repeats it every 8 cm of paper (dots 1 cm across); 0.5 prints it
## half that size, small and busy; 3 prints it huge, a few dots to a box. It never stretches: the paper
## is laid as it is really folded, at one scale on every face. Default 1.
@export_range(0.05, 8.0, 0.01, "or_greater") var paper_scale := 1.0: set = _set_paper_scale

@export_group("Ribbon")
## How it is tied (see Ribbon). The bag has no ribbon round it whatever this says; the parcel is tied
## with string. Default CROSS.
@export var ribbon := Ribbon.CROSS: set = _set_ribbon
## The colour of the ribbon and the bow. It also colours the stripe in the string, the bag's rope
## handles and (paler) its tissue paper, and the line round the tag. Default gold.
@export var ribbon_colour := GOLD: set = _set_ribbon_colour
## What the ribbon is made of: SATIN (a soft sheen, a woven edge) or FOIL (bright painted streaks, for
## gold and silver). Default SATIN.
@export var ribbon_finish := Finish.SATIN: set = _set_ribbon_finish
## The bow (see Bow), or NONE. Default CLASSIC.
@export var bow := Bow.CLASSIC: set = _set_bow
## Where the bow sits (see BowPlace). Default AUTO: on the ribbon.
@export var bow_place := BowPlace.AUTO: set = _set_bow_place
## How big the bow is against the size that suits the present. 0.5 a small neat bow, 1 as made, 2 a
## showy one that overhangs a small box. Default 1.
@export_range(0.0, 4.0, 0.01, "or_greater") var bow_size := 1.0: set = _set_bow_size
## A blank card tag on a loop of string: hanging down the front of a tall thing, lying on top of a
## flat one. Default off.
@export var tag := false: set = _set_tag

@export_group("Hand-wrapped")
## How far it leans out of true, as a soft box does: its top pushed a little to one side. Its foot
## never leaves the floor. 0 square, 1 leaning up to four degrees, 3 a box somebody sat on. Default 0.35.
@export_range(0.0, 3.0, 0.01, "or_greater") var tilt := 0.35: set = _set_tilt
## How much it has sunk: a little lower and a little wider. 0 not at all, 1 up to 8 percent lower, 3
## plainly squashed. Default 0.35.
@export_range(0.0, 3.0, 0.01, "or_greater") var squash := 0.35: set = _set_squash
## The hat box only: its lid lifted at the front to show the tissue paper inside. 0 shut, 0.3 ajar, 1
## standing well open. It stays shut when tied crosswise (the ribbon holds it). Default 0.
@export_range(0.0, 1.0) var lid_ajar := 0.0: set = _set_lid_ajar

@export_group("Game")
## Give it a StaticBody3D with one box (or, for the round ones, a cylinder) the size of its footprint,
## so physics bodies cannot pass through it. Off by default: nothing here needs physics, and
## footprint() gives the same shape for a game that keeps its player out by sums.
@export var collision := false: set = _set_collision
## Whether it casts a shadow. Default on.
@export var shadows := true: set = _set_shadows

static var _library: Dictionary = {}
static var _material: ShaderMaterial

var _instance: MeshInstance3D
var _body: StaticBody3D
var _queued := false


## What Present.add_to() fills: the points of one mesh, however many presents are in it.
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
		made.surface_set_material(0, Present.material())
		return made

	func triangles() -> int:
		return idx.size() / 3


## A present ready to add: Present.make(Present.Shape.DRUM, Present.Palette.CLASSIC, 7, 12.5). Its
## paper, colours, ribbon and bow are dealt from the palette by the seed (the same seed, the same
## present).
static func make(of_shape: Shape, palette := Palette.CLASSIC, of_seed := 1, of_size := 1.0) -> Present:
	var rng := RandomNumberGenerator.new()
	rng.seed = of_seed
	var gift := Present.new()
	gift.shape = of_shape
	gift.size = of_size
	gift.seed = of_seed
	gift.wear(look(palette, rng, of_shape))
	return gift


## A heap of presents ready to add (a PresentPile): mixed shapes and sizes, some stacked, some leaning,
## none through another. Present.pile(5, Present.Palette.CLASSIC, 3, 12.5).
static func pile(count: int, palette := Palette.CLASSIC, of_seed := 1, of_size := 1.0) -> PresentPile:
	var heap := PresentPile.new()
	heap.count = count
	heap.palette = palette
	heap.seed = of_seed
	heap.size = of_size
	return heap


## Deals a present's dress from a palette: {paper, paper_colour, print_colour, accent_colour,
## ribbon_colour, ribbon_finish, ribbon, bow, tag}. Hand it to wear(), or to add_to() with more keys.
## For Palette.CUSTOM give the colours to deal from: papers (two or more) and ribbons.
static func look(palette: Palette, rng: RandomNumberGenerator, for_shape := Shape.CUBE,
		custom_papers: Array[Color] = [], custom_ribbons: Array[Color] = []) -> Dictionary:
	var way: Array = []
	var papers: Array = PAPERS_OF[0]
	if palette == Palette.CUSTOM:
		var from: Array[Color] = custom_papers
		if from.is_empty():
			from = [RED, CREAM]
		var ties: Array[Color] = custom_ribbons
		if ties.is_empty():
			ties = from
		var base: Color = from[rng.randi() % from.size()]
		var printed: Color = from[rng.randi() % from.size()]
		if printed.is_equal_approx(base):
			printed = from[(from.find(base) + 1) % from.size()] if from.size() > 1 else base.lightened(0.6)
		way = [base, printed, ties[rng.randi() % ties.size()], ties[rng.randi() % ties.size()]]
	else:
		var ways: Array = WAYS[palette]
		way = ways[rng.randi() % ways.size()]
		papers = PAPERS_OF[palette]
	var dress := {
		"paper": papers[rng.randi() % papers.size()],
		"paper_colour": way[0], "print_colour": way[1], "accent_colour": way[2], "ribbon_colour": way[3],
	}
	if dress["paper"] == Paper.KRAFT:
		dress["paper_colour"] = BROWN_PAPER
		dress["print_colour"] = DARK_BROWN
	elif (way[0] as Color).is_equal_approx(BROWN_PAPER):
		dress["paper"] = Paper.KRAFT if rng.randf() < 0.5 else dress["paper"]
		if dress["paper"] == Paper.KRAFT:
			dress["print_colour"] = DARK_BROWN
	if dress["paper"] == Paper.FOIL:
		dress["print_colour"] = (dress["paper_colour"] as Color).lightened(0.6)
	var tie: Color = dress["ribbon_colour"]
	dress["ribbon_finish"] = Finish.FOIL if tie.is_equal_approx(GOLD) or tie.is_equal_approx(SILVER) else Finish.SATIN
	dress["ribbon"] = [Ribbon.CROSS, Ribbon.CROSS, Ribbon.CROSS, Ribbon.CROSS, Ribbon.BAND, Ribbon.BAND, Ribbon.DIAGONAL,
			Ribbon.DIAGONAL, Ribbon.NONE][rng.randi() % 9]
	var bows := [Bow.CLASSIC, Bow.CLASSIC, Bow.CLASSIC, Bow.POMPOM, Bow.POMPOM, Bow.ROSETTE, Bow.ROSETTE, Bow.STRING, Bow.NONE]
	dress["bow"] = bows[rng.randi() % bows.size()]
	if for_shape == Shape.PARCEL or dress["paper"] == Paper.KRAFT and rng.randf() < 0.6:
		dress["bow"] = Bow.STRING
	if dress["ribbon"] == Ribbon.NONE and dress["bow"] == Bow.CLASSIC:
		dress["bow"] = Bow.ROSETTE      # with no ribbon to tie, a stick-on one
	dress["tag"] = rng.randf() < 0.35
	return dress


## Put on a dress dealt by look() (or any Dictionary of this node's settings by name).
func wear(dress: Dictionary) -> void:
	for key: String in dress:
		set(key, dress[key])


## This present's settings as a Dictionary, the form add_to() takes.
func spec() -> Dictionary:
	return {
		"shape": shape, "low_detail": low_detail, "seed": seed if seed != 0 else int(get_instance_id()) % 100000 + 1,
		"paper": paper, "paper_colour": paper_colour, "print_colour": print_colour, "accent_colour": accent_colour,
		"paper_scale": paper_scale, "ribbon": ribbon, "ribbon_colour": ribbon_colour, "ribbon_finish": ribbon_finish,
		"bow": bow, "bow_place": bow_place, "bow_size": bow_size, "tag": tag, "tilt": tilt, "squash": squash,
		"lid_ajar": lid_ajar,
	}


## Where the player may not walk: this present's footprint on the floor, in the world.
##   centre  Vector3, on the floor under its middle
##   round   true for the drum and the hat box: keep out of the circle `radius` about `centre`
##   half    Vector2: for the others, half its width (along its own x) and half its depth (its own z)
##   turn    how far it is turned about the upright, in radians (its own x is at (cos, 0, -sin))
##   radius  the circle that holds all of it (for a quick first test, or to treat everything as round)
##   height  how tall it is (its bow not counted)
## Present.blocks(footprint, point, margin) and Present.push_out(footprint, point, margin) use it.
func footprint() -> Dictionary:
	var of := measure(spec())
	var scale_now := global_basis.get_scale()
	var half: Vector3 = of["half"] * size
	var middle: Vector3 = of["middle"] * size
	var print_ := {
		"centre": global_transform * Vector3(middle.x, 0.0, middle.z),
		"round": of["round"],
		"half": Vector2(half.x * scale_now.x, half.z * scale_now.z),
		"turn": global_basis.get_euler().y,
		"height": half.y * 2.0 * scale_now.y,
	}
	print_["radius"] = maxf(half.x * scale_now.x, half.z * scale_now.z) if of["round"] else Vector2(half.x * scale_now.x, half.z * scale_now.z).length()
	return print_


## Whether a point on the floor is inside a footprint (from footprint() or a pile's footprints()),
## grown by `margin` (the player's own radius).
static func blocks(print_: Dictionary, point: Vector3, margin := 0.0) -> bool:
	var centre: Vector3 = print_["centre"]
	var d := Vector2(point.x - centre.x, point.z - centre.z)
	if print_["round"]:
		return d.length() < float(print_["radius"]) + margin
	var turn: float = print_["turn"]
	var half: Vector2 = print_["half"]
	var own := Vector2(d.x * cos(turn) - d.y * sin(turn), d.x * sin(turn) + d.y * cos(turn))
	return absf(own.x) < half.x + margin and absf(own.y) < half.y + margin


## The nearest place outside a footprint for a point that is inside it (the point itself if it is
## not): what to set a walker's position to so that it slides round a present.
static func push_out(print_: Dictionary, point: Vector3, margin := 0.0) -> Vector3:
	if not blocks(print_, point, margin):
		return point
	var centre: Vector3 = print_["centre"]
	var d := Vector2(point.x - centre.x, point.z - centre.z)
	if print_["round"]:
		var away := d.normalized() if d.length() > 0.00001 else Vector2.RIGHT
		away *= float(print_["radius"]) + margin
		return Vector3(centre.x + away.x, point.y, centre.z + away.y)
	var turn: float = print_["turn"]
	var half: Vector2 = print_["half"] + Vector2(margin, margin)
	var own := Vector2(d.x * cos(turn) - d.y * sin(turn), d.x * sin(turn) + d.y * cos(turn))
	if half.x - absf(own.x) < half.y - absf(own.y):
		own.x = half.x * (1.0 if own.x >= 0.0 else -1.0)
	else:
		own.y = half.y * (1.0 if own.y >= 0.0 else -1.0)
	return Vector3(centre.x + own.x * cos(turn) + own.y * sin(turn), point.y, centre.z - own.x * sin(turn) + own.y * cos(turn))


## How many triangles this present is drawn with.
func triangles() -> int:
	if _instance == null or _instance.mesh == null:
		return 0
	return _instance.mesh.surface_get_array_index_len(0) / 3


## The one material every present is drawn with (to change `sheen`, or to read it on a loading screen).
static func material() -> ShaderMaterial:
	if _material == null:
		_material = ShaderMaterial.new()
		_material.shader = SHADER
		var sheet := PICTURE.get_image()
		if sheet.is_compressed():
			sheet.decompress()
		sheet.convert(Image.FORMAT_RGBA8)
		var cell := sheet.get_width() / 4
		var cut: Array[Image] = []
		for i in 16:
			var square := sheet.get_region(Rect2i((i % 4) * cell, (i / 4) * cell, cell, cell))
			square.generate_mipmaps()
			cut.append(square)
		var layers := Texture2DArray.new()
		layers.create_from_images(cut)
		_material.set_shader_parameter(&"squares", layers)
	return _material


## The size of a present of these settings at size 1, in its own space: {half: Vector3 (half its
## width, height and depth), middle: Vector3 (where its middle is from its foot), round: bool,
## soft: Basis (its lean and sag)}.
static func measure(of: Dictionary) -> Dictionary:
	var which: int = of.get("shape", Shape.CUBE)
	var entry: Dictionary = _models()[SHAPE_NAMES[which]]
	var box: AABB = entry["box"]
	var soft := _soft(of)
	return {
		"half": Vector3(box.size.x * 0.5 * soft.x.x, box.size.y * 0.5 * soft.y.y, box.size.z * 0.5 * soft.z.z),
		"middle": Vector3(box.get_center().x * soft.x.x, box.get_center().y * soft.y.y, box.get_center().z * soft.z.z),
		"round": ROUND[which],
		"soft": soft,
	}


## Adds a present to a batch: `of` is a Dictionary of settings by name (see spec(); anything left out
## is as a new Present has it), `place` where its foot goes (scale it to size it). Many presents
## added to one batch are one mesh: Batch.mesh().
static func add_to(batch: Batch, of: Dictionary, place: Transform3D) -> void:
	var which: int = of.get("shape", Shape.CUBE)
	var low: bool = of.get("low_detail", false)
	var entry: Dictionary = _models()[SHAPE_NAMES[which] + ("_lo" if low else "")]
	var pieces: Dictionary = entry["pieces"]
	var anchors: Dictionary = entry["anchors"]
	var rng := RandomNumberGenerator.new()
	rng.seed = int(of.get("seed", 1)) * 7919 + 17
	var whole := place * Transform3D(_soft(of), Vector3.ZERO)
	var tie: int = of.get("ribbon", Ribbon.CROSS)
	var tied := ""
	if tie == Ribbon.CROSS and pieces.has("ribbon_cross"):
		tied = "ribbon_cross"
	elif tie == Ribbon.DIAGONAL and pieces.has("ribbon_diag"):
		tied = "ribbon_diag"
	elif (tie == Ribbon.BAND or tie == Ribbon.DIAGONAL) and pieces.has("ribbon_band"):
		tied = "ribbon_band"
	_add_piece(batch, pieces["body"], whole, of)
	var lid := Transform3D.IDENTITY
	if pieces.has("lid"):
		var ajar: float = of.get("lid_ajar", 0.0)
		if ajar > 0.0 and tied != "ribbon_cross" and anchors.has("hinge"):
			var hinge: Transform3D = (anchors["hinge"] as Transform3D).orthonormalized()
			lid = hinge * Transform3D(Basis(Vector3.RIGHT, -0.6 * ajar), Vector3.ZERO) * hinge.affine_inverse()
		_add_piece(batch, pieces["lid"], whole * lid, of)
	if tied != "":
		_add_piece(batch, pieces[tied], whole, of)
	var kind: int = of.get("bow", Bow.CLASSIC)
	var where: int = of.get("bow_place", BowPlace.AUTO)
	var spot := "bow_top"
	if where == BowPlace.CORNER or (where == BowPlace.AUTO and tied == "ribbon_diag"):
		spot = "bow_corner"
	elif where == BowPlace.SIDE:
		spot = "bow_side"
	var turn_bow := rng.randf_range(-0.3, 0.3)
	var turn_tag := rng.randf_range(-0.2, 0.2)
	if kind != Bow.NONE and anchors.has(spot):
		var at: Transform3D = anchors[spot]
		var big: float = at.basis.get_scale().x * float(of.get("bow_size", 1.0))
		var on_lid := lid if spot != "bow_side" else Transform3D.IDENTITY
		var sits := Transform3D(at.basis.orthonormalized() * Basis(Vector3.UP, turn_bow).scaled(Vector3.ONE * big), at.origin)
		var bow_pieces: Dictionary = _models()[BOW_NAMES[kind] + ("_lo" if low else "")]["pieces"]
		_add_piece(batch, bow_pieces["body"], whole * on_lid * sits, of)
	if of.get("tag", false) and anchors.has("tag"):
		var at: Transform3D = anchors["tag"]
		var hangs := Transform3D(at.basis.orthonormalized() * Basis(Vector3.UP, turn_tag).scaled(Vector3.ONE * at.basis.get_scale().x), at.origin)
		var tag_pieces: Dictionary = _models()["tag_lo" if low else "tag"]["pieces"]
		_add_piece(batch, tag_pieces["body"], whole * hangs, of)


## Forgets the models and the material (they are read again when next wanted).
static func clear_cache() -> void:
	_library.clear()
	_material = null


func _ready() -> void:
	_build()


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
	if _body != null:
		_body.queue_free()
		remove_child(_body)
		_body = null
	if collision:
		var of := measure(spec())
		_body = solid(of["half"] * size, of["middle"] * size, of["round"])
		add_child(_body)


## A still body for a present of this size: a box, or a cylinder for a round one. (PresentPile uses it.)
static func solid(half: Vector3, middle: Vector3, is_round: bool) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.name = "Solid"
	var held := CollisionShape3D.new()
	if is_round:
		var can := CylinderShape3D.new()
		can.radius = maxf(half.x, half.z)
		can.height = half.y * 2.0
		held.shape = can
	else:
		var box := BoxShape3D.new()
		box.size = half * 2.0
		held.shape = box
	held.position = middle
	body.add_child(held)
	return body


func _rebuild() -> void:
	if is_inside_tree() and not _queued:
		_queued = true
		_build.call_deferred()


# ------------------------------------------------------------------ what presents share
## Every model in the .glb by name: {pieces: {body: [surface, ...], ribbon_cross: ..., lid: ...},
## anchors: {bow_top: Transform3D, ...}, box: AABB of the body and lid}. A surface is {kind: the
## Blender material's name, v, n, uv, idx}.
static func _models() -> Dictionary:
	if not _library.is_empty():
		return _library
	var scene: Node = (MODELS as PackedScene).instantiate()
	for top in scene.get_children():
		var title := String(top.name)
		var pieces := {}
		var anchors := {}
		var box := AABB()
		var boxed := false
		for child in top.get_children():
			var what := String(child.name).trim_prefix(title + "_")
			var holder := child as MeshInstance3D
			if holder != null:
				var surfaces: Array = []
				for s in holder.mesh.get_surface_count():
					var arrays := holder.mesh.surface_get_arrays(s)
					var worn := holder.mesh.surface_get_material(s)
					var idx: PackedInt32Array = PackedInt32Array()
					if arrays[Mesh.ARRAY_INDEX] != null:
						idx = arrays[Mesh.ARRAY_INDEX]
					else:
						for i in (arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array).size():
							idx.append(i)
					surfaces.append({
						"kind": String(worn.resource_name) if worn != null else "paper",
						"v": arrays[Mesh.ARRAY_VERTEX], "n": arrays[Mesh.ARRAY_NORMAL], "uv": arrays[Mesh.ARRAY_TEX_UV], "idx": idx,
					})
				pieces[what] = surfaces
				if what == "body" or what == "lid":
					box = holder.mesh.get_aabb() if not boxed else box.merge(holder.mesh.get_aabb())
					boxed = true
			elif child is Node3D:
				anchors[what] = (child as Node3D).transform
		_library[title] = {"pieces": pieces, "anchors": anchors, "box": box}
	scene.free()
	return _library


## A present's lean and sag: its top pushed a little sideways, a little lower and wider. From its seed.
static func _soft(of: Dictionary) -> Basis:
	var rng := RandomNumberGenerator.new()
	rng.seed = int(of.get("seed", 1)) * 2749 + 5
	var lean: float = of.get("tilt", 0.35)
	var sag: float = float(of.get("squash", 0.35)) * rng.randf_range(0.3, 1.0) * 0.08
	sag = minf(sag, 0.6)
	var wide := 1.0 + sag * 0.4
	return Basis(Vector3(wide, 0.0, 0.0), Vector3(lean * rng.randf_range(-0.07, 0.07), 1.0 - sag, lean * rng.randf_range(-0.07, 0.07)),
			Vector3(0.0, 0.0, wide))


## What a kind of surface wears: [square, base, print, accent, shine kept, whether the paper scale applies].
static func _wears(kind: String, of: Dictionary) -> Array:
	var tie: Color = of.get("ribbon_colour", GOLD)
	var base: Color = of.get("paper_colour", RED)
	match kind:
		"paper":
			return [int(of.get("paper", Paper.DOTS)), base, of.get("print_colour", CREAM), of.get("accent_colour", GOLD), 1.0, true]
		"inside":
			return [SQUARE_PLAIN, Color(0.93, 0.91, 0.86), WHITE, WHITE, 1.0, false]
		"ribbon":
			if int(of.get("ribbon_finish", Finish.SATIN)) == Finish.FOIL:
				return [SQUARE_RIBBON_FOIL, tie, tie.lightened(0.65), WHITE, 1.0, false]
			return [SQUARE_SATIN, tie, tie.darkened(0.3), WHITE, 1.0, false]
		"twine":
			return [SQUARE_TWINE, JUTE, tie if not tie.is_equal_approx(JUTE) else DARK_BROWN, WHITE, 1.0, false]
		"rope":
			return [SQUARE_TWINE, tie, tie.darkened(0.35), WHITE, 1.0, false]
		"tissue":
			return [SQUARE_TISSUE, tie.lerp(WHITE, 0.72), Color.WHITE, WHITE, 1.0, false]
		"tag":
			return [SQUARE_PARTS, Color(0.94, 0.9, 0.8), tie if tie.get_luminance() < 0.6 else RED, Color(0.7, 0.55, 0.25), 1.0, false]
		"seal":
			return [SQUARE_PARTS, tie, tie.lightened(0.6), WHITE, 1.0, false]
		"tape":
			return [SQUARE_PARTS, base.lerp(Color(1.0, 0.97, 0.88), 0.5), base.lerp(Color.WHITE, 0.75), WHITE, 1.0, false]
	return [SQUARE_PLAIN, base, base, base, 1.0, false]


static func _add_piece(batch: Batch, surfaces: Array, place: Transform3D, of: Dictionary) -> void:
	var turn := place.basis.inverse().transposed()
	var mirrored := place.basis.determinant() < 0.0
	var repeat := 1.0 / maxf(float(of.get("paper_scale", 1.0)), 0.001)
	for surface: Dictionary in surfaces:
		var wears := _wears(surface["kind"], of)
		var square := float(wears[0])
		var base := (wears[1] as Color).srgb_to_linear()
		var printed := (wears[2] as Color).srgb_to_linear()
		var accent := (wears[3] as Color).srgb_to_linear()
		var shine: float = wears[4]
		var scale_uv := repeat if wears[5] else 1.0
		var v: PackedVector3Array = surface["v"]
		var n: PackedVector3Array = surface["n"]
		var uv: PackedVector2Array = surface["uv"]
		var idx: PackedInt32Array = surface["idx"]
		var first := batch.v.size()
		var count := v.size()
		batch.v.resize(first + count)
		batch.n.resize(first + count)
		batch.uv.resize(first + count)
		batch.c0.resize((first + count) * 4)
		batch.c1.resize((first + count) * 4)
		batch.c2.resize((first + count) * 4)
		for i in count:
			var at := first + i
			batch.v[at] = place * v[i]
			batch.n[at] = (turn * n[i]).normalized()
			batch.uv[at] = uv[i] * scale_uv
			var o := at * 4
			batch.c0[o] = base.r
			batch.c0[o + 1] = base.g
			batch.c0[o + 2] = base.b
			batch.c0[o + 3] = square
			batch.c1[o] = printed.r
			batch.c1[o + 1] = printed.g
			batch.c1[o + 2] = printed.b
			batch.c1[o + 3] = shine
			batch.c2[o] = accent.r
			batch.c2[o + 1] = accent.g
			batch.c2[o + 2] = accent.b
			batch.c2[o + 3] = 1.0
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
func _set_shape(value: Shape) -> void:
	shape = value
	_rebuild()


func _set_size(value: float) -> void:
	size = maxf(value, 0.0001)
	_rebuild()


func _set_low_detail(value: bool) -> void:
	low_detail = value
	_rebuild()


func _set_seed(value: int) -> void:
	seed = value
	_rebuild()


func _set_paper(value: Paper) -> void:
	paper = value
	_rebuild()


func _set_paper_colour(value: Color) -> void:
	paper_colour = value
	_rebuild()


func _set_print_colour(value: Color) -> void:
	print_colour = value
	_rebuild()


func _set_accent_colour(value: Color) -> void:
	accent_colour = value
	_rebuild()


func _set_paper_scale(value: float) -> void:
	paper_scale = maxf(value, 0.001)
	_rebuild()


func _set_ribbon(value: Ribbon) -> void:
	ribbon = value
	_rebuild()


func _set_ribbon_colour(value: Color) -> void:
	ribbon_colour = value
	_rebuild()


func _set_ribbon_finish(value: Finish) -> void:
	ribbon_finish = value
	_rebuild()


func _set_bow(value: Bow) -> void:
	bow = value
	_rebuild()


func _set_bow_place(value: BowPlace) -> void:
	bow_place = value
	_rebuild()


func _set_bow_size(value: float) -> void:
	bow_size = maxf(value, 0.0)
	_rebuild()


func _set_tag(value: bool) -> void:
	tag = value
	_rebuild()


func _set_tilt(value: float) -> void:
	tilt = maxf(value, 0.0)
	_rebuild()


func _set_squash(value: float) -> void:
	squash = maxf(value, 0.0)
	_rebuild()


func _set_lid_ajar(value: float) -> void:
	lid_ajar = clampf(value, 0.0, 1.0)
	_rebuild()


func _set_collision(value: bool) -> void:
	collision = value
	_rebuild()


func _set_shadows(value: bool) -> void:
	shadows = value
	if _instance != null:
		_instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if shadows else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
