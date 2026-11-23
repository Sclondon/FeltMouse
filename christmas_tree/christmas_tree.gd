class_name ChristmasTree
extends Node3D
## A Christmas tree: six kinds grown from settings and a seed (the needles are GameCommon's PineTree), standing in
## a pot, bucket, basket, metal stand, plank cross or burlap root ball (Blender models), with a cloth skirt, and
## dressed by the sibling components when they are installed: a string of ChristmasLights wound round it, an
## OrnamentSet hung on its branches with a topper and a garland, a heap of presents (PresentPile), snow.
## (GameCommon godot/christmas-tree. This node is on the floor, or the table, under the middle of the stand.)
##
##   var tree := ChristmasTree.dressed(ChristmasTree.Kind.TABLETOP, ChristmasTree.Palette.CLASSIC, 7, 12.5)
##   tree.position = on_the_counter               # 12.5: this game's units to a metre (Felt Mouse: 1 unit = 8 cm)
##   add_child(tree)                              # it builds itself here; call rebuild() after changing settings
##   var keep_out := tree.footprint()             # the pot only: a small player walks under the boughs
##   tree.shake(1.0, mouse.global_position)       # boughs bob, ornaments swing, a few needles fall
##
## Bare: ChristmasTree.make(kind, size, seed). Every layer of the dressing is a setting and can be switched off.
## Settings take effect at the next rebuild() (the tree is built when it enters the scene).

enum Kind {
	TABLETOP,  ## a little bushy tree for a table or a counter, 45 cm, in a pot
	FIR,       ## the full room-sized tree: wide, dense, sheared to a cone, 2.1 m
	PENCIL,    ## tall and slim, for a corner or a hallway, 2.2 m
	SAPLING,   ## a sparse scraggly sapling whose top bows over under one ornament, 75 cm
	FLOCKED,   ## a full tree sprayed white with flock, snow lying on its boughs, 1.9 m
	FEATHER,   ## the old-fashioned feather tree: a few sparse tiers of thin wire branches with a berry at each tip, 90 cm
}
enum Stand {
	USUAL,        ## the one that suits the kind (pot, metal stand, basket, plank cross, bucket, pot)
	NONE,         ## nothing: the trunk comes out of the floor
	POT,          ## a terracotta pot on a saucer, soil in it
	BUCKET,       ## a galvanised bucket of pebbles, its handle dropped to one side
	BASKET,       ## a wicker basket with a burlap liner
	METAL_STAND,  ## the classic: a green water bowl on four red legs, with eye bolts
	PLANK_CROSS,  ## two sawn planks nailed across each other
	ROOT_BALL,    ## the tree's own root ball wrapped in burlap and tied with twine
}
enum Skirt {
	NONE,
	FELT,     ## red felt with a cream blanket-stitched scalloped trim
	QUILTED,  ## a patchwork quilt in red, green and cream wedges with a bound edge
}
enum Palette {
	CLASSIC,      ## many-coloured lights; red, gold and green ornaments; red and green presents
	WARM_GOLD,    ## warm white lights; gold, red and cream ornaments
	SILVER_BLUE,  ## cool white lights; silver and blue ornaments; tinsel; blue and silver presents
	PASTEL,       ## warm white lights; pink, mint, sky and lemon ornaments and presents
	HANDMADE,     ## warm white lights; wooden, felt, dough and gingerbread ornaments; brown paper presents
}
enum Topper { NONE, STAR, SPIRE }
enum Garland { NONE, BEADS, TINSEL }
enum LightKind { USUAL, MINI, C7, C9, FACETED, GLOBE, STAR, ICICLE }
enum LightPattern { STEADY, TWINKLE, CHASE, FADE, OFF }

## Each kind's recipe. "height" in real metres; the PineTree settings it starts from; "wild": its wildness at
## neatness 0 and at 1; "trunk": the trunk's thickness against a full tree's; "ornaments", "presents": how many a
## dressed one gets.
const KINDS := [
	{"name": "tabletop", "height": 0.45, "stand": Stand.POT, "whorls": 9, "branches": 10, "spread": 0.68, "droop": 0.22, "lift": 0.34,
		"taper": 0.95, "fullness": 0.74, "sprigs": 3, "crown_base": 0.13, "inner": 0.8, "wood": 0.0, "wild": [0.7, 0.06], "lean": 0.02,
		"bend": 0.0, "trunk": 1.0, "ornaments": 14, "presents": 3},
	{"name": "fir", "height": 2.1, "stand": Stand.METAL_STAND, "whorls": 16, "branches": 12, "spread": 0.62, "droop": 0.3, "lift": 0.3,
		"taper": 1.0, "fullness": 0.66, "sprigs": 3, "crown_base": 0.1, "inner": 0.85, "wood": 0.0, "wild": [0.75, 0.05], "lean": 0.015,
		"bend": 0.0, "trunk": 1.0, "ornaments": 46, "presents": 9},
	{"name": "pencil", "height": 2.2, "stand": Stand.BASKET, "whorls": 17, "branches": 8, "spread": 0.27, "droop": 0.25, "lift": 0.5,
		"taper": 0.8, "fullness": 0.7, "sprigs": 3, "crown_base": 0.09, "inner": 0.8, "wood": 0.0, "wild": [0.7, 0.05], "lean": 0.01,
		"bend": 0.0, "trunk": 0.8, "ornaments": 30, "presents": 5},
	{"name": "sapling", "height": 0.75, "stand": Stand.PLANK_CROSS, "whorls": 4, "branches": 4, "spread": 0.6, "droop": 0.25, "lift": 0.12,
		"taper": 0.8, "fullness": 0.26, "sprigs": 0, "crown_base": 0.3, "inner": 0.0, "wood": 0.0035, "wild": [1.0, 0.6], "lean": 0.06,
		"bend": 0.3, "trunk": 0.6, "ornaments": 1, "presents": 0},
	{"name": "flocked", "height": 1.9, "stand": Stand.BUCKET, "whorls": 13, "branches": 11, "spread": 0.6, "droop": 0.36, "lift": 0.26,
		"taper": 1.05, "fullness": 0.68, "sprigs": 3, "crown_base": 0.11, "inner": 0.85, "wood": 0.0, "wild": [0.75, 0.08], "lean": 0.015,
		"bend": 0.0, "trunk": 1.0, "ornaments": 38, "presents": 7},
	{"name": "feather", "height": 0.9, "stand": Stand.POT, "whorls": 5, "branches": 8, "spread": 0.6, "droop": 0.0, "lift": 0.14,
		"taper": 0.9, "fullness": 0.17, "sprigs": 0, "crown_base": 0.2, "inner": 0.0, "wood": 0.0032, "wild": [0.5, 0.03], "lean": 0.0,
		"bend": 0.0, "trunk": 0.7, "ornaments": 14, "presents": 3},
]
## Each stand, as modelled for a tree one metre tall: its model's name, the radius and height a player is kept
## out of, how high in it the trunk's foot sits, and how far the tree's foot is from a skirt's middle.
const STANDS := {
	Stand.POT: {"name": "pot", "radius": 0.141, "height": 0.2, "seat": 0.168},
	Stand.BUCKET: {"name": "bucket", "radius": 0.137, "height": 0.215, "seat": 0.18},
	Stand.BASKET: {"name": "basket", "radius": 0.142, "height": 0.2, "seat": 0.185},
	Stand.METAL_STAND: {"name": "metal_stand", "radius": 0.263, "height": 0.216, "seat": 0.03},
	Stand.PLANK_CROSS: {"name": "plank_cross", "radius": 0.253, "height": 0.07, "seat": 0.046},
	Stand.ROOT_BALL: {"name": "root_ball", "radius": 0.14, "height": 0.243, "seat": 0.19},
}
const RED := Color(0.72, 0.05, 0.06)
const GOLD := Color(0.95, 0.70, 0.22)
const GREEN := Color(0.06, 0.36, 0.14)
const CREAM := Color(0.96, 0.92, 0.82)
const SILVER := Color(0.80, 0.83, 0.88)
## What each palette asks of the sibling components (by name, so nothing here breaks if they renumber), and the
## colours of the stand-in baubles used when the ornaments component is not installed.
const PALETTES := {
	Palette.CLASSIC: {"lights": "CLASSIC", "ornaments": "CLASSIC", "presents": "CLASSIC", "garland": [RED, GOLD],
		"baubles": [RED, GOLD, GREEN, Color(0.16, 0.30, 0.72)]},
	Palette.WARM_GOLD: {"lights": "WARM_WHITE", "ornaments": "CUSTOM", "presents": "CLASSIC", "garland": [GOLD, CREAM],
		"baubles": [GOLD, Color(0.60, 0.04, 0.06), CREAM], "colours": [GOLD, Color(0.60, 0.04, 0.06), CREAM], "accents": [CREAM, GOLD]},
	Palette.SILVER_BLUE: {"lights": "COOL_WHITE", "ornaments": "SILVER_BLUE", "presents": "BLUE_AND_SILVER", "garland": [SILVER, Color.WHITE],
		"baubles": [SILVER, Color(0.08, 0.22, 0.60), Color(0.42, 0.66, 0.90), Color(0.93, 0.95, 1.0)]},
	Palette.PASTEL: {"lights": "WARM_WHITE", "ornaments": "PASTEL", "presents": "PASTEL", "garland": [Color(0.95, 0.58, 0.68), Color.WHITE],
		"baubles": [Color(0.95, 0.58, 0.68), Color(0.56, 0.86, 0.72), Color(0.58, 0.76, 0.95), Color(0.98, 0.88, 0.56)]},
	Palette.HANDMADE: {"lights": "WARM_WHITE", "ornaments": "HANDMADE", "presents": "KRAFT_AND_RED", "garland": [RED, CREAM],
		"baubles": [RED, Color(0.10, 0.38, 0.16), CREAM]},
}

@export_group("Tree")
## Which tree (see Kind). Each has its own shape, usual height and usual stand.
@export var kind: Kind = Kind.TABLETOP
## How tall the tree is from its foot to its tip, in real metres. 0 (the default) uses the kind's own (tabletop
## 0.45, fir 2.1, pencil 2.2, sapling 0.75, flocked 1.9, feather 0.9). 0.2 is a toy; 4 fills a hall. The stand,
## trunk, needles and dressing all follow it.
@export_range(0.0, 8.0, 0.01, "or_greater") var height := 0.0
## The game's units to a real metre: everything is built real size and multiplied by this. 1 in a game counted in
## metres; 12.5 in Felt Mouse, where 1 unit is 8 cm.
@export_range(0.01, 200.0, 0.01, "or_greater") var size := 1.0
## How thickly it is branched, against the kind's own: 0.4 thin and gappy, with the trunk showing between the
## tiers; 1 (the default) as the kind is; 1.6 bushy and solid (and more triangles).
@export_range(0.2, 2.5, 0.01, "or_greater") var fullness := 1.0
## How neatly it has been sheared: 0 as it grew, branches of every length and tiers out of line; 0.8 (the default)
## a tidy cone with a little life in it; 1 clipped like a hedge.
@export_range(0.0, 1.0, 0.01) var neatness := 0.8
## The colour of the needles in the body of each bough. Default a deep fir green. (Inside the tree they are drawn
## darker than this by themselves.)
@export var needle_colour := Color(0.20, 0.46, 0.26)
## The colour of the newest needles at the tips of the boughs. Default a lighter, yellower green.
@export var tip_colour := Color(0.46, 0.66, 0.34)
## The trunk's colour, and the branches' on the sapling and the feather tree.
@export var bark_colour := Color(0.36, 0.25, 0.18)
## How big the needles are drawn, against the usual for the tree's height: 0.5 fine, like a spruce seen from across
## the room; 1 (the default); 2 chunky toy needles.
@export_range(0.2, 5.0, 0.01, "or_greater") var needle_size := 1.0
## Snow lying on the upper side of the boughs: 0 (the default) none, 0.5 a dusting, 1 loaded. The flocked kind is
## white already and this adds to it.
@export_range(0.0, 1.0, 0.01) var snow := 0.0
## Fewer, plainer branches (about a fifth of the needles' triangles), the low models of the
## stand, bulbs, ornaments and presents: for phones, and for trees seen from across a room.
@export var low_detail := false
## The low models for the dressing only (bulbs, a plain wire, ornaments, presents) while the needles and the stand
## stay full: for a tree the player gets close to on a phone. `low_detail` already includes it.
@export var low_dressing := false
## The same settings and seed always give the same tree, dressed the same way; another seed, another tree.
@export var seed := 1

@export_group("Stand")
## What it stands in (see Stand). USUAL (the default) is the kind's own.
@export var stand: Stand = Stand.USUAL
## How big the stand is against the usual for the tree's height: 0.7 a pot it has outgrown, 1 (the default), 1.5 a
## tub. The footprint follows it.
@export_range(0.3, 4.0, 0.01, "or_greater") var stand_size := 1.0
## A cloth skirt laid round the foot (see Skirt). Default none.
@export var skirt: Skirt = Skirt.NONE
## How far the skirt reaches, against the width of the lowest boughs: 0.5 a mat under the stand, 1 (the default) out
## to the boughs' tips, 1.5 well past them.
@export_range(0.2, 3.0, 0.01, "or_greater") var skirt_size := 1.0
## How high the middle of the skirt is drawn up round the trunk, as a share of its radius: 0 (the default) flat on
## the floor with the stand standing on it; 0.3 a low tent that hides a small stand (use with Stand.NONE, or the
## stand's top will poke through the cloth); 0.6 a steep cone.
@export_range(0.0, 1.0, 0.01) var skirt_rise := 0.0

@export_group("Dressing")
## The colours of everything hung on it and laid under it (see Palette).
@export var palette: Palette = Palette.CLASSIC
## A string of lights wound round the tree in a spiral on the outside of the boughs (needs godot/christmas-lights).
@export var lights := false
## Which bulbs (see ChristmasLights). USUAL: mini bulbs, the ones real trees wear.
@export var light_kind: LightKind = LightKind.USUAL
## How many times the string goes round the tree from bottom to top. 0 (the default) picks it from the height
## (about 4 on the tabletop tree, 7 on the fir); 2 a single lazy loop; 12 tightly wound.
@export_range(0.0, 30.0, 0.1, "or_greater") var light_turns := 0.0
## The gap between bulbs in real metres. 0 (the default) picks it from the height (5 cm on the tabletop tree, 13 cm
## on the fir: about 30 and 100 bulbs). Smaller, more bulbs and more triangles.
@export_range(0.0, 1.0, 0.005, "or_greater") var light_spacing := 0.0
## How big the bulbs and their wire are against real ones. 0 (the default) follows the tree: real size on a room
## tree, about half on the tabletop one (real bulbs look like lanterns on a tree that small).
@export_range(0.0, 4.0, 0.01, "or_greater") var light_scale := 0.0
## How strongly the real lights shine. 0 (the default) follows the tree: 0.6 for a room tree, about 0.3 for the
## tabletop one. (ChristmasLights multiplies it by `size`, so the glow looks alike at any scale.)
@export_range(0.0, 8.0, 0.01, "or_greater") var light_energy := 0.0
## How the bulbs behave: steady, twinkling, chasing, fading through the colours, or off (unlit glass).
@export var light_pattern: LightPattern = LightPattern.STEADY
## How many real lights (OmniLight3D) the string carries so the room picks up its glow: 2 by default, spread up the
## tree; 0 for none (the bulbs still glow by themselves). GL Compatibility lights one object with 8 at most.
@export_range(0, 8) var real_lights := 2
## How many ornaments hang on it (needs godot/ornaments; without it plain stand-in baubles are hung). -1 (the
## default) the kind's own number (14 on the tabletop tree, 46 on the fir, 1 on the sapling); 0 none.
@export_range(-1, 200, 1, "or_greater") var ornaments := 0
## Hang the plain stand-in baubles (and star, and beads) from this component's own models even when godot/ornaments
## is installed: one colour each, no designs, no swinging, but a single draw. Default off.
@export var stand_in_ornaments := false
## How big the ornaments, topper and garland are against real ones. 0 (the default) follows the tree: real size on
## a room tree, under half on the tabletop one. 1 real size (a ball 6 cm across) whatever the tree.
@export_range(0.0, 4.0, 0.01, "or_greater") var ornament_scale := 0.0
## What sits on the tip.
@export var topper: Topper = Topper.NONE
## A garland of beads or tinsel hung in swags round the tree.
@export var garland: Garland = Garland.NONE
## How many swag rings of garland, from the lowest boughs up. Default 2.
@export_range(1, 8) var garland_rings := 2
## How many wrapped presents are heaped round the foot (needs godot/presents). 0 none (the default).
@export_range(0, 60, 1, "or_greater") var presents := 0
## How big the presents are against real ones. 0 (the default) follows the tree (real size under a room tree, under
## half under the tabletop one).
@export_range(0.0, 4.0, 0.01, "or_greater") var present_scale := 0.0

@export_group("Movement")
## How much the boughs stir by themselves: 0 dead still; 0.15 (the default) barely breathing, as in a warm room;
## 1 as a pine outdoors in a breeze.
@export_range(0.0, 3.0, 0.01, "or_greater") var sway := 0.15
## How many needles fall at a full shake (strength 1). 0 none; 24 by default; 100 a tree that has dried out.
@export_range(0, 200, 1, "or_greater") var needle_fall := 24

const MODELS := preload("models/tree_stands.glb")
const PICTURE := preload("textures/tree_stands.png")

static var _meshes := {}
static var _stand_material: StandardMaterial3D
static var _tint_material: StandardMaterial3D
static var _needle_fall_material: StandardMaterial3D

var _pine: PineTree
var _fronds: Array[Dictionary] = []
var _needles: ShaderMaterial
var _rock: Node3D
var _made: Array[Node] = []
var _lights_node: Node3D
var _ornaments_node: Node3D
var _piles: Array[Node3D] = []
var _fall: CPUParticles3D
var _stand_in := false
var _h := 1.0            # the height in real metres
var _s := 1.0            # the stand's and trunk's scale: metres of model to a 1 m tree's
var _seat := 0.0         # how high the trunk's foot is, real metres
var _k := 1.0            # the needle scale given to PineTree
var _bands: Array[Vector2] = []    # the crown's outline: (height above the trunk's foot, radius), real metres
var _axis: Array[Vector3] = []     # the trunk's line, where each whorl leaves it
var _tip := Vector3.ZERO           # the leader's tip and the way it points, in the crown's own space, real metres
var _tip_way := Vector3.UP
var _shake_time := -1.0
var _shake_power := 0.0
var _shake_way := Vector3.RIGHT


## A bare tree of a kind, ready to add: ChristmasTree.make(ChristmasTree.Kind.FIR, 1.0, 3).
static func make(of_kind: Kind, of_size := 1.0, of_seed := 1) -> ChristmasTree:
	var tree := ChristmasTree.new()
	tree.kind = of_kind
	tree.size = of_size
	tree.seed = of_seed
	return tree


## A fully dressed tree, ready to add: lights, ornaments, a topper, a garland, presents and (for the trees that
## stand on a floor) a skirt, all from the palette and the seed. Switch a layer off by clearing its setting before
## adding the tree. ChristmasTree.dressed(ChristmasTree.Kind.TABLETOP, ChristmasTree.Palette.CLASSIC, 7, 12.5).
static func dressed(of_kind: Kind, of_palette := Palette.CLASSIC, of_seed := 1, of_size := 1.0) -> ChristmasTree:
	var tree := make(of_kind, of_size, of_seed)
	tree.dress(of_palette)
	return tree


## Turns on every layer of dressing that suits this kind (the sapling gets its one ornament and nothing else; the
## feather tree ornaments and a star but no lights; the tabletop tree no garland or skirt: set them if wanted). Call rebuild() if the tree is already in the scene.
func dress(of_palette := Palette.CLASSIC) -> void:
	palette = of_palette
	ornaments = -1
	match kind:
		Kind.SAPLING:
			lights = false
			topper = Topper.NONE
			garland = Garland.NONE
			presents = 0
			skirt = Skirt.NONE
		Kind.FEATHER:
			lights = false
			topper = Topper.STAR
			garland = Garland.NONE
			presents = int(KINDS[kind]["presents"])
			skirt = Skirt.NONE
		_:
			lights = true
			topper = Topper.SPIRE if of_palette == Palette.SILVER_BLUE else Topper.STAR
			garland = Garland.NONE if kind == Kind.TABLETOP else (Garland.TINSEL if of_palette == Palette.SILVER_BLUE else Garland.BEADS)
			presents = int(KINDS[kind]["presents"])
			skirt = Skirt.NONE if kind == Kind.TABLETOP else (Skirt.QUILTED if of_palette == Palette.HANDMADE or of_palette == Palette.PASTEL else Skirt.FELT)


func _ready() -> void:
	set_process(false)
	rebuild()


# ------------------------------------------------------------------------------------------------ what a game asks
## Where the player may not walk: the stand (or pot) only, as a circle on the floor with its height, in the world,
## in the same form as a Present's footprint: {centre: Vector3, round: true, radius, half: Vector2, turn, height}.
## A player shorter than `clearance()` walks under the boughs. With Stand.NONE it is the trunk alone.
func footprint() -> Dictionary:
	var grown := global_basis.get_scale()
	var radius := _stand_radius() * size * maxf(grown.x, grown.z)
	return {"centre": global_position, "round": true, "radius": radius, "half": Vector2(radius, radius), "turn": 0.0,
		"height": _stand_height() * size * grown.y}


## The stand's footprint and one for every present standing on the floor round it.
func footprints() -> Array[Dictionary]:
	var out: Array[Dictionary] = [footprint()]
	for pile in _piles:
		if is_instance_valid(pile) and pile.has_method("footprints"):
			out.append_array(pile.call("footprints"))
	return out


## Whether a point on the floor is inside the stand (grown by `margin`, the player's own radius).
func blocks(point: Vector3, margin := 0.0) -> bool:
	var print_ := footprint()
	var centre: Vector3 = print_["centre"]
	return Vector2(point.x - centre.x, point.z - centre.z).length() < float(print_["radius"]) + margin


## The point moved out of the stand if it is inside it (and out of the presents): set a walker's position to this
## each step and it slides round the foot of the tree.
func push_out(point: Vector3, margin := 0.0) -> Vector3:
	var print_ := footprint()
	var centre: Vector3 = print_["centre"]
	var d := Vector2(point.x - centre.x, point.z - centre.z)
	var keep := float(print_["radius"]) + margin
	if d.length() < keep:
		d = (d.normalized() if d.length() > 0.00001 else Vector2.RIGHT) * (keep + 0.0001)
		point = Vector3(centre.x + d.x, point.y, centre.z + d.y)
	for pile in _piles:
		if is_instance_valid(pile) and pile.has_method("push_out"):
			point = pile.call("push_out", point, margin)
	return point


## How high above the floor the lowest boughs' tips hang, in the game's units (this node's own scale not counted):
## anything shorter walks under them.
func clearance() -> float:
	var low := INF
	for frond in _fronds:
		if not frond["leader"] and float(frond["up_tree"]) < 0.25:
			low = minf(low, minf((frond["tip"] as Vector3).y, (frond["line"][2] as Vector3).y) - float(frond["half"]) * 0.4)
	return (_seat + (low if low < INF else 0.0)) * size


## The tree's tip, in this node's own space: the origin is the very top of the leader and +Y points the way the
## leader does (straight up, except on the bowed sapling). A topper's socket goes over it.
func tip() -> Transform3D:
	var y := _tip_way.normalized()
	var x := y.cross(Vector3.BACK).normalized() if absf(y.dot(Vector3.BACK)) < 0.95 else Vector3.RIGHT
	return Transform3D(Basis(x, y, x.cross(y)), _from_crown(_tip))


## Places to hang things, in this node's own space, spread evenly round and up the tree at the outside of the
## boughs: for each {"position": where a thread is tied, just under a bough near its tip, "out": the level way
## out from the trunk, "size": a suggested scale (bigger low down, smaller near the top), "up_tree": 0 at the lowest
## boughs .. 1 at the top}. `count` 0 gives every place there is (one per bough). The same seed, the same places.
func hanging_points(count := 0, of_seed := -1) -> Array[Dictionary]:
	var all: Array[Dictionary] = []
	for frond in _fronds:
		if frond["leader"] or float(frond["up_tree"]) > 0.9:
			continue
		var line: Array = frond["line"]
		var at := 0.84 * (line.size() - 1)
		var p: Vector3 = (line[int(at)] as Vector3).lerp(line[mini(int(at) + 1, line.size() - 1)], at - int(at))
		p.y -= float(frond["half"]) * 0.12
		all.append({"position": _from_crown(p), "out": frond["out"], "size": lerpf(1.15, 0.8, frond["up_tree"]), "up_tree": frond["up_tree"]})
	if count <= 0 or count >= all.size():
		return all
	# each as far as can be from those already taken
	var rng := RandomNumberGenerator.new()
	rng.seed = hash([seed if of_seed < 0 else of_seed, 77])
	var taken: Array[Dictionary] = []
	var nearest := PackedFloat32Array()
	nearest.resize(all.size())
	nearest.fill(INF)
	var pick := rng.randi() % all.size()
	while taken.size() < count:
		taken.append(all[pick])
		var last: Vector3 = all[pick]["position"]
		var best := -1.0
		for i in all.size():
			nearest[i] = minf(nearest[i], (all[i]["position"] as Vector3).distance_squared_to(last))
			var scored := nearest[i] * rng.randf_range(0.8, 1.0)
			if scored > best:
				best = scored
				pick = i
	return taken


## The tip of every bough, in this node's own space: {"position", "out", "up_tree"} for each.
func branch_tips() -> Array[Dictionary]:
	var out: Array[Dictionary] = []
	for frond in _fronds:
		if not frond["leader"]:
			out.append({"position": _from_crown(frond["tip"]), "out": frond["out"], "up_tree": frond["up_tree"]})
	return out


## How far out the boughs reach at a height above the floor (both in the game's units).
func crown_radius_at(y: float) -> float:
	return _radius_at(y / size - _seat) * size


## A line wound round the outside of the boughs from the lowest to near the top, `turns` times, in this node's own
## space: what the lights are hung on. `inset` 1 at the tips of the boughs, 0.86 (the default) nestled just inside them.
func spiral(turns: float, inset := 0.86, step_degrees := 18.0) -> PackedVector3Array:
	var line := PackedVector3Array()
	if _bands.is_empty():
		return line
	var low := _bands[0].x
	var high := lerpf(_bands[_bands.size() - 1].x, _tip.y, 0.55)
	var steps := maxi(int(turns * 360.0 / step_degrees), 2)
	var rng := RandomNumberGenerator.new()
	rng.seed = hash([seed, 31])
	var start := rng.randf() * TAU
	for i in steps + 1:
		var f := float(i) / steps
		# (even gaps up the slope: the turns crowd a little towards the top, where the tree is narrow)
		var y := lerpf(low, high, pow(f, 0.9))
		var angle := start + turns * TAU * f
		var centre := _axis_at(y)
		var r := _radius_at(y) * inset
		line.append(_from_crown(Vector3(centre.x + cos(angle) * r, y, centre.z + sin(angle) * r)))
	return line


## Bumps the tree: the boughs bob, the whole crown rocks on its foot and comes to rest, its ornaments swing, and a
## few needles fall (snow, on a snowy tree). `strength` 0.3 a brush past, 1 a good knock, 2 someone fell into it.
## `from` is where the bump came from, in the world (zero: any way).
func shake(strength := 1.0, from := Vector3.ZERO) -> void:
	if _rock == null:
		return
	var away := global_position - from
	away.y = 0.0
	if from == Vector3.ZERO or away.length() < 0.0001:
		away = Vector3.RIGHT.rotated(Vector3.UP, float(Time.get_ticks_msec() % 6283) * 0.001)
	_shake_way = (global_basis.inverse() * away).normalized()
	_shake_power = clampf(maxf(strength, _shake_power * exp(-2.4 * maxf(_shake_time, 0.0))), 0.0, 3.0)
	_shake_time = 0.0
	set_process(true)
	if _ornaments_node and _ornaments_node.has_method("knock"):
		_ornaments_node.call("knock", global_position, away.normalized() * minf(0.45 * strength, 1.2), 0.0)
	if _fall and needle_fall > 0:
		_fall.amount = clampi(int(needle_fall * strength), 1, 600)
		_fall.restart()
		_fall.emitting = true


## The ChristmasLights node (null without lights): to change its pattern, speed or brightness while the game runs.
func lights_node() -> Node3D:
	return _lights_node


## The OrnamentSet node (null without ornaments, or when the stand-in baubles are used).
func ornaments_node() -> Node3D:
	return _ornaments_node


## The PresentPile nodes round the foot.
func present_piles() -> Array[Node3D]:
	return _piles


## The PineTree the needles were grown from (its `fronds()` lists every bough).
func pine() -> PineTree:
	return _pine


## Whether plain stand-in baubles were hung because godot/ornaments is not installed.
func uses_stand_in_ornaments() -> bool:
	return _stand_in


## How many triangles the whole tree is drawn with as it stands, dressing and presents included.
func triangle_count() -> int:
	return _count(self)[0]


## How many draws (surfaces of visible meshes) it takes.
func draw_count() -> int:
	return _count(self)[1]


## How many real lights (OmniLight3D) it carries.
func real_light_count() -> int:
	return find_children("*", "OmniLight3D", true, false).size()


## The tree's measurements in the game's units: {height: floor to tip, radius: the widest boughs, clearance,
## stand_radius, stand_height, trunk_foot: how high the trunk's foot is}.
func measure() -> Dictionary:
	var wide := 0.0
	for band in _bands:
		wide = maxf(wide, band.y)
	return {"height": (_seat + _tip.y) * size, "radius": wide * size, "clearance": clearance(), "stand_radius": _stand_radius() * size,
		"stand_height": _stand_height() * size, "trunk_foot": _seat * size}


## Forgets the shared models and materials (the next tree reads them again).
static func clear_cache() -> void:
	_meshes.clear()
	_stand_material = null
	_tint_material = null
	_needle_fall_material = null


# ------------------------------------------------------------------------------------------------ building
## Builds the tree again from its settings (it is built by itself when it enters the scene; before that this does
## nothing, and the helpers above have nothing to tell).
func rebuild() -> void:
	if not is_inside_tree():
		return
	for node in _made:
		if is_instance_valid(node):
			node.get_parent().remove_child(node)
			node.queue_free()
	_made.clear()
	_piles.clear()
	_lights_node = null
	_ornaments_node = null
	_fall = null
	_stand_in = false
	_shake_time = -1.0
	_shake_power = 0.0
	set_process(false)
	var recipe: Dictionary = KINDS[kind]
	_h = height if height > 0.0 else float(recipe["height"])
	_s = pow(_h, 0.8) * stand_size
	var which := _stand_kind()
	_seat = 0.0 if which == Stand.NONE else float(STANDS[which]["seat"]) * _s
	_grow(recipe)
	_stand_and_skirt(which)
	_rock = Node3D.new()
	_rock.name = "Crown"
	_rock.position = Vector3(0.0, _seat * size, 0.0)
	_keep(_rock, self)
	var crown := MeshInstance3D.new()
	crown.name = "Needles"
	crown.mesh = _pine.mesh(0)
	crown.material_override = _needles
	crown.scale = Vector3.ONE * size
	_rock.add_child(crown)
	if lights:
		_string_lights()
	_hang_ornaments()
	if presents > 0:
		_heap_presents()
	_falling_needles()


func _keep(node: Node, parent: Node) -> void:
	parent.add_child(node)
	_made.append(node)


## The crown's own space (real metres, the trunk's foot at the origin) into this node's.
func _from_crown(p: Vector3) -> Vector3:
	return Vector3(p.x, p.y + _seat, p.z) * size


func _stand_kind() -> Stand:
	return (KINDS[kind]["stand"] as Stand) if stand == Stand.USUAL else stand


func _stand_radius() -> float:
	var which := _stand_kind()
	return _pine.trunk_radius * 1.6 if which == Stand.NONE else float(STANDS[which]["radius"]) * _s


func _stand_height() -> float:
	var which := _stand_kind()
	return _h * 0.1 if which == Stand.NONE else float(STANDS[which]["height"]) * _s


## Grows the needles: PineTree with this kind's recipe, and what the rest needs to know of its shape.
func _grow(recipe: Dictionary) -> void:
	var pine_ := PineTree.new()
	pine_.height = _h
	pine_.trunk_radius = 0.022 * pow(_h, 0.8) * float(recipe["trunk"])
	pine_.crown_base = recipe["crown_base"]
	pine_.whorls = maxi(int(round(float(recipe["whorls"]) * lerpf(0.8, 1.15, clampf(fullness - 0.4, 0.0, 1.2) / 1.2))), 3)
	pine_.branches = clampi(int(round(float(recipe["branches"]) * lerpf(0.7, 1.25, clampf(fullness - 0.4, 0.0, 1.2) / 1.2))), 3, 16)
	pine_.spread = recipe["spread"]
	pine_.droop = recipe["droop"]
	pine_.lift = recipe["lift"]
	pine_.taper = recipe["taper"]
	pine_.fullness = clampf(float(recipe["fullness"]) * lerpf(0.75, 1.2, clampf(fullness - 0.4, 0.0, 1.2) / 1.2), 0.08, 0.8)
	pine_.sprigs = recipe["sprigs"]
	pine_.inner = float(recipe["inner"]) * clampf(fullness, 0.5, 1.3)
	pine_.branch_wood = float(recipe["wood"]) * pow(_h, 0.8)
	var wild: Array = recipe["wild"]
	pine_.wildness = lerpf(wild[0], wild[1], neatness)
	pine_.lean = float(recipe["lean"]) * (1.0 - neatness * 0.6)
	pine_.bend = recipe["bend"]
	_k = 0.3 * pow(_h, 0.3) * needle_size
	pine_.needle_scale = _k
	var flock := 0.74 if kind == Kind.FLOCKED else 0.0
	var white := Color(0.93, 0.95, 0.98)
	var body := needle_colour
	var ends := tip_colour
	if kind == Kind.FEATHER:   # (dyed goose feather: darker and bluer than a living tree)
		body = needle_colour.lerp(Color(0.08, 0.36, 0.3), 0.45)
		ends = body.lightened(0.18)
	pine_.needles_inner = body.darkened(0.32).lerp(white, flock * 0.3)
	pine_.needles_outer = body.lerp(white, flock)
	pine_.tips = ends.lerp(white, flock * 1.15)
	pine_.bark = bark_colour
	pine_.snow = clampf(snow + (0.4 if kind == Kind.FLOCKED else 0.0), 0.0, 1.0)
	pine_.seed = seed
	if low_detail:
		# (PineTree's plain self, but with more of its whorls and branches kept: indoors a tree is never so far
		# off that the bare cone inside may show between them)
		var full_whorls := pine_.whorls
		var full_branches := pine_.branches
		pine_ = pine_.simple()
		pine_.whorls = maxi(int(full_whorls * 0.62), mini(full_whorls, 5))
		pine_.branches = maxi(int(full_branches * 0.7), mini(full_branches, 5))
	if _needles == null:
		_needles = PineTree.needle_material()
	# (the shader moves a frond by its length in shader-metres, which are 1 / needle_scale real ones)
	_needles.set_shader_parameter(&"sway", 0.04 * sway * _k)
	_needles.set_shader_parameter(&"bob", Vector3.ZERO)
	pine_.material = _needles
	_pine = pine_
	_fronds = _pine.fronds(0)
	# the crown's outline, in bands of height: the furthest tip in each
	_bands.clear()
	_axis.clear()
	var lows := INF
	var highs := -INF
	for frond in _fronds:
		if frond["leader"]:
			_tip = frond["tip"]
			_tip_way = (frond["tip"] as Vector3) - (frond["base"] as Vector3)
			continue
		_axis.append(frond["base"])
		lows = minf(lows, (frond["tip"] as Vector3).y)
		highs = maxf(highs, (frond["tip"] as Vector3).y)
	_axis.sort_custom(func(a: Vector3, b: Vector3) -> bool: return a.y < b.y)
	var count := clampi(_pine.whorls, 3, 12)
	# (the usual reach of the tips in each band, not the longest: a string wound at this radius lies on the boughs)
	var reach := PackedFloat32Array()
	var tips_in := PackedInt32Array()
	reach.resize(count)
	tips_in.resize(count)
	for frond in _fronds:
		if frond["leader"]:
			continue
		var p: Vector3 = frond["tip"]
		var band := clampi(int((p.y - lows) / maxf(highs - lows, 0.0001) * count), 0, count - 1)
		var centre := _axis_at(p.y)
		reach[band] += Vector2(p.x - centre.x, p.z - centre.z).length()
		tips_in[band] += 1
	for band in count:
		if tips_in[band] > 0:
			_bands.append(Vector2(lows + (band + 0.5) / count * (highs - lows), reach[band] / tips_in[band]))


## Where the trunk is at a height (it leans, and on the sapling bows over).
func _axis_at(y: float) -> Vector3:
	if _axis.is_empty():
		return Vector3(0.0, y, 0.0)
	if y <= _axis[0].y:
		return Vector3(_axis[0].x * y / maxf(_axis[0].y, 0.0001), y, _axis[0].z * y / maxf(_axis[0].y, 0.0001))
	for i in range(1, _axis.size()):
		if y <= _axis[i].y:
			var t := (y - _axis[i - 1].y) / maxf(_axis[i].y - _axis[i - 1].y, 0.0001)
			return Vector3(lerpf(_axis[i - 1].x, _axis[i].x, t), y, lerpf(_axis[i - 1].z, _axis[i].z, t))
	var last := _axis[_axis.size() - 1]
	var t2 := clampf((y - last.y) / maxf(_tip.y - last.y, 0.0001), 0.0, 1.0)
	return Vector3(lerpf(last.x, _tip.x, t2), y, lerpf(last.z, _tip.z, t2))


func _radius_at(y: float) -> float:
	if _bands.is_empty():
		return 0.0
	if y <= _bands[0].x:
		return _bands[0].y
	for i in range(1, _bands.size()):
		if y <= _bands[i].x:
			return lerpf(_bands[i - 1].y, _bands[i].y, (y - _bands[i - 1].x) / maxf(_bands[i].x - _bands[i - 1].x, 0.0001))
	var last := _bands[_bands.size() - 1]
	return lerpf(last.y, 0.0, clampf((y - last.x) / maxf(_tip.y - last.x, 0.0001), 0.0, 1.0))


## The stand and the skirt as one mesh and one draw.
func _stand_and_skirt(which: Stand) -> void:
	if which == Stand.NONE and skirt == Skirt.NONE:
		return
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var lifted := 0.0
	if skirt != Skirt.NONE:
		var wide := 0.0
		for band in _bands:
			wide = maxf(wide, band.y)
		var radius := maxf(wide * 0.95 * skirt_size, _stand_radius() * 1.12)
		var cloth := _risen(_mesh(("skirt_felt" if skirt == Skirt.FELT else "skirt_quilted") + ("_lo" if low_detail else "")), skirt_rise)
		var turn := Basis(Vector3.UP, float(hash([seed, 5]) % 628) * 0.01)
		st.append_from(cloth, 0, Transform3D(turn.scaled(Vector3.ONE * radius * size), Vector3.ZERO))
		lifted = 0.011 * radius   # (the stand stands on the cloth)
	if which != Stand.NONE:
		var turn := Basis(Vector3.UP, float(hash([seed, 6]) % 628) * 0.01)
		st.append_from(_mesh(String(STANDS[which]["name"]) + ("_lo" if low_detail else "")), 0,
				Transform3D(turn.scaled(Vector3.ONE * _s * size), Vector3(0.0, lifted * size, 0.0)))
		_seat += lifted
	var base := MeshInstance3D.new()
	base.name = "Stand"
	base.mesh = st.commit()
	base.material_override = _material()
	_keep(base, self)


## A skirt's mesh with its middle drawn up by `rise` (its "rise" shape key, worked into a plain mesh once).
func _risen(source: ArrayMesh, rise: float) -> ArrayMesh:
	if rise <= 0.0 or source.get_blend_shape_count() == 0:
		return source
	var arrays := source.surface_get_arrays(0)
	var shapes := source.surface_get_blend_shape_arrays(0)
	var from: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var to: PackedVector3Array = shapes[0][Mesh.ARRAY_VERTEX]
	var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
	var to_normals: PackedVector3Array = shapes[0][Mesh.ARRAY_NORMAL] if shapes[0][Mesh.ARRAY_NORMAL] != null else normals
	for i in from.size():
		from[i] = from[i].lerp(to[i], rise)
		normals[i] = normals[i].lerp(to_normals[i], minf(rise, 1.0)).normalized()
	var plain := []
	plain.resize(Mesh.ARRAY_MAX)
	plain[Mesh.ARRAY_VERTEX] = from
	plain[Mesh.ARRAY_NORMAL] = normals
	plain[Mesh.ARRAY_TEX_UV] = arrays[Mesh.ARRAY_TEX_UV]
	plain[Mesh.ARRAY_INDEX] = arrays[Mesh.ARRAY_INDEX]
	var made := ArrayMesh.new()
	made.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, plain)
	return made


static func _mesh(named: String) -> ArrayMesh:
	if _meshes.is_empty():
		var scene: Node = MODELS.instantiate()
		for found in scene.find_children("*", "MeshInstance3D", true, false):
			_meshes[String(found.name)] = (found as MeshInstance3D).mesh
		scene.free()
	return _meshes[named]


## The one material of every stand, skirt and stand-in: the picture, plainly lit.
static func _material() -> StandardMaterial3D:
	if _stand_material == null:
		_stand_material = StandardMaterial3D.new()
		_stand_material.albedo_texture = PICTURE
		_stand_material.roughness = 0.85
		_stand_material.metallic_specular = 0.25
	return _stand_material


## The same, coloured by each instance (the stand-in baubles and the berries).
static func _tinted() -> StandardMaterial3D:
	if _tint_material == null:
		_tint_material = _material().duplicate()
		_tint_material.vertex_color_use_as_albedo = true
		_tint_material.roughness = 0.35
		_tint_material.metallic_specular = 0.6
	return _tint_material


## A sibling component's script by its class name, or null if that component is not in the project.
static func _sibling(named: StringName) -> Script:
	for entry: Dictionary in ProjectSettings.get_global_class_list():
		if entry["class"] == named:
			return load(entry["path"])
	return null


## A value of a sibling's enum by name (so nothing here depends on its numbering).
static func _named(script: Script, list: String, value: String) -> int:
	var lists := script.get_script_constant_map()
	if lists.has(list) and (lists[list] as Dictionary).has(value):
		return lists[list][value]
	push_warning("ChristmasTree: %s has no %s.%s" % [script.resource_path, list, value])
	return 0


func _dress_scale(asked: float) -> float:
	return asked if asked > 0.0 else clampf(_h, 0.42, 1.0)


func _string_lights() -> void:
	var script := _sibling(&"ChristmasLights")
	if script == null:
		push_warning("ChristmasTree: lights asked for, but godot/christmas-lights is not installed")
		return
	var turns := light_turns if light_turns > 0.0 else clampf(((_tip.y - _bands[0].x) if not _bands.is_empty() else _h) / (0.16 * pow(_h, 0.6)), 2.0, 14.0)
	var line := spiral(turns)
	for i in line.size():
		line[i] -= _rock.position
	var string: Node3D = script.new()
	string.name = "Lights"
	string.set("kind", _named(script, "Kind", LightKind.keys()[light_kind] if light_kind != LightKind.USUAL else "MINI"))
	string.set("palette", _named(script, "Palette", PALETTES[palette]["lights"]))
	string.set("pattern", _named(script, "Pattern", LightPattern.keys()[light_pattern]))
	var bulb := light_scale if light_scale > 0.0 else clampf(_h / 1.1, 0.5, 1.0)
	string.set("size", size)
	string.set("bulb_size", bulb)
	string.set("wire_thickness", 0.0035 * bulb)
	string.set("light_energy", light_energy if light_energy > 0.0 else 0.6 * clampf(sqrt(_h / 2.0), 0.4, 1.0))
	string.set("low_detail", low_detail or low_dressing)
	string.set("spacing", light_spacing if light_spacing > 0.0 else maxf(0.085 * pow(_h, 0.6), 0.04))
	string.set("droop", 0.35)
	string.set("wire_wander", 0.004)
	string.set("wire_twist", 0.0)   # (on a tree the wire is half buried: two plain strands, a third of the triangles)
	string.set("lights", real_lights)
	string.set("light_range", maxf(_h * 1.3, 0.8))
	string.set("light_offset", Vector3.ZERO)
	string.set("seed", seed)
	_keep(string, _rock)
	string.call("hang", line)
	_lights_node = string


func _hang_ornaments() -> void:
	var count := int(KINDS[kind]["ornaments"]) if ornaments < 0 else ornaments
	var berries := kind == Kind.FEATHER
	if count <= 0 and topper == Topper.NONE and garland == Garland.NONE and not berries:
		return
	var grown := _dress_scale(ornament_scale)
	var places: Array[Dictionary] = []
	var back := -_rock.position
	if kind == Kind.SAPLING and count > 0:
		# its one ornament, on the bowed tip
		places.append({"position": _from_crown(_tip - _tip_way.normalized() * 0.012 * _h) + back, "out": Vector3(_tip_way.x, 0, _tip_way.z).normalized(), "size": 1.0})
	elif count > 0:
		for place in hanging_points(count):
			place["position"] = (place["position"] as Vector3) + back
			places.append(place)
	var swags: Array[PackedVector3Array] = []
	if garland != Garland.NONE and _bands.size() >= 2:
		var low := _bands[0].x
		var high := _bands[_bands.size() - 1].x
		for ring in garland_rings:
			var y := lerpf(low, high, (ring + 0.35) / (garland_rings + 0.4))
			var r := _radius_at(y) * 0.97
			var hooks := maxi(int(round(TAU * r / maxf(0.22 * pow(_h, 0.75), 0.02))), 4)
			var sag := TAU * r / hooks * 0.22
			var line := PackedVector3Array()
			var turn := ring * 1.3 + float(hash([seed, 9]) % 628) * 0.01
			for i in hooks * 8 + 1:
				var f := float(i) / 8.0
				var centre := _axis_at(y)
				var angle := turn + f * TAU / hooks
				line.append(_from_crown(Vector3(centre.x + cos(angle) * r, y - sag * sin(PI * fposmod(f, 1.0)), centre.z + sin(angle) * r)) + back)
			swags.append(line)
	var tip_at := _from_crown(_tip) + back
	var colours: Array = PALETTES[palette]["garland"]
	var script: Script = null if stand_in_ornaments else _sibling(&"OrnamentSet")
	if script != null:
		var hung: Node3D = script.new()
		hung.name = "Ornaments"
		hung.set("size", size * grown)
		hung.set("low_detail", low_detail or low_dressing)
		_keep(hung, _rock)
		if kind == Kind.SAPLING and not places.is_empty():
			hung.call("add", _named(script, "Kind", "BALL"), places[0]["position"], {"colour": RED, "colour2": GOLD, "scale": 1.1 / grown * clampf(_h * 0.9, 0.3, 1.0), "thread": 0.02})
		elif not places.is_empty():
			var options := {"palette": _named(script, "Palette", PALETTES[palette]["ornaments"]), "seed": seed}
			if PALETTES[palette].has("colours"):
				options["colours"] = PALETTES[palette]["colours"]
				options["accents"] = PALETTES[palette]["accents"]
			hung.call("decorate", places, options)
		if topper != Topper.NONE:
			hung.call("top", _named(script, "Kind", "STAR_TOPPER" if topper == Topper.STAR else "SPIRE_TOPPER"), tip_at,
					{"colour": colours[0] if topper == Topper.SPIRE else GOLD, "colour2": colours[1] if topper == Topper.SPIRE else RED})
		for line in swags:
			hung.call("drape", _named(script, "Kind", "BEADS" if garland == Garland.BEADS else "TINSEL"), line, {"colour": colours[0], "colour2": colours[1]})
		_ornaments_node = hung
		places.clear()
		swags.clear()
	else:
		_stand_in = count > 0 or topper != Topper.NONE
		swags.clear()   # (there is no stand-in garland)
		if topper != Topper.NONE:
			# STAND-IN topper: the plain folded star from this component's own models
			var star := MeshInstance3D.new()
			star.name = "StandInStar"
			star.mesh = _mesh("star_lo" if low_detail or low_dressing else "star")
			star.material_override = _material()
			var seat := tip()
			star.transform = Transform3D(seat.basis.scaled(Vector3.ONE * size * grown * 1.3), seat.origin + back - seat.basis.y * 0.03 * size * grown)
			_keep(star, _rock)
	# STAND-IN baubles and beads (only when godot/ornaments is not installed), and the feather tree's berries:
	# one MultiMesh of the plain ball from this component's own models, coloured by instance.
	var balls: Array = []   # [Transform3D, Color]
	var rng := RandomNumberGenerator.new()
	rng.seed = hash([seed, 41])
	var shades: Array = PALETTES[palette]["baubles"]
	for i in places.size():
		var big := float(places[i].get("size", 1.0)) * rng.randf_range(0.85, 1.1) * size * grown
		balls.append([Transform3D(Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3.ONE * big), places[i]["position"]), shades[i % shades.size()]])
	if berries:
		for frond in _fronds:
			if frond["leader"]:
				continue
			var berry := 0.2 * pow(_h, 0.8) * size
			balls.append([Transform3D(Basis.IDENTITY.scaled(Vector3.ONE * berry), _from_crown(frond["tip"]) + back + Vector3(0, 0.045 * berry, 0)), Color(0.78, 0.05, 0.07)])
	if balls.is_empty():
		return
	var many := MultiMesh.new()
	many.transform_format = MultiMesh.TRANSFORM_3D
	many.use_colors = true
	many.mesh = _mesh("bauble_lo" if low_detail or low_dressing or places.is_empty() else "bauble")
	many.instance_count = balls.size()
	for i in balls.size():
		many.set_instance_transform(i, balls[i][0])
		many.set_instance_color(i, balls[i][1])
	var shown := MultiMeshInstance3D.new()
	shown.name = "Berries" if places.is_empty() else "StandInBaubles"
	shown.multimesh = many
	shown.material_override = _tinted()
	shown.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_keep(shown, _rock)


func _heap_presents() -> void:
	var script := _sibling(&"Present")
	if script == null:
		push_warning("ChristmasTree: presents asked for, but godot/presents is not installed")
		return
	var grown := _dress_scale(present_scale)
	var heaps := 1 if presents <= 3 else (2 if presents <= 6 else 3)
	var rng := RandomNumberGenerator.new()
	rng.seed = hash([seed, 53])
	var turn := rng.randf() * TAU
	var left := presents
	for i in heaps:
		var share := int(ceil(float(left) / (heaps - i)))
		left -= share
		var heap: Node3D = script.call("pile", share, _named(script, "Palette", PALETTES[palette]["presents"]), seed * 31 + i, size * grown)
		heap.name = "Presents%d" % (i + 1)
		heap.set("low_detail", low_detail or low_dressing)
		_keep(heap, self)
		_piles.append(heap)
		# (a heap is planned as it enters the scene: only then is its reach known)
		var reach := 0.3 * size * grown
		if heap.has_method("reach") and heap.is_inside_tree():
			reach = float(heap.call("reach")["radius"]) / maxf(global_basis.get_scale().x, 0.0001)
		var angle := turn + i * TAU / heaps + rng.randf_range(-0.3, 0.3)
		var away := _stand_radius() * size + reach * 0.85
		heap.position = Vector3(cos(angle) * away, (0.012 * size * _radius_at(0.0)) if skirt != Skirt.NONE else 0.0, sin(angle) * away)
		heap.rotation.y = rng.randf() * TAU


## The needles that fall when the tree is shaken: a burst of little cards from the boughs (CPU particles, which GL
## Compatibility draws). They are not drawn until the first shake.
func _falling_needles() -> void:
	if needle_fall <= 0 or _fronds.is_empty():
		return
	var points := PackedVector3Array()
	for frond in _fronds:
		if frond["leader"]:
			continue
		var line: Array = frond["line"]
		points.append((line[line.size() - 1] as Vector3) * size)
		points.append((line[line.size() / 2] as Vector3) * size)
	var snowy := _pine.snow > 0.3
	var fall := CPUParticles3D.new()
	fall.name = "FallingNeedles"
	fall.emitting = false
	fall.one_shot = true
	fall.explosiveness = 0.8
	fall.amount = needle_fall
	fall.local_coords = false
	fall.emission_shape = CPUParticles3D.EMISSION_SHAPE_POINTS
	fall.emission_points = points
	var drop := 2.2 * size
	fall.gravity = Vector3(0.0, -drop, 0.0)
	fall.lifetime = clampf(sqrt(2.0 * (_seat + _h * 0.55) * size / drop), 0.5, 2.5)
	fall.lifetime_randomness = 0.35
	fall.direction = Vector3.DOWN
	fall.spread = 80.0
	fall.initial_velocity_min = 0.02 * size
	fall.initial_velocity_max = 0.14 * size
	fall.angle_min = -180.0
	fall.angle_max = 180.0
	fall.angular_velocity_min = -240.0
	fall.angular_velocity_max = 240.0
	fall.scale_amount_min = 0.7
	fall.scale_amount_max = 1.3
	var fade := Curve.new()
	fade.add_point(Vector2(0.0, 1.0))
	fade.add_point(Vector2(0.8, 1.0))
	fade.add_point(Vector2(1.0, 0.0))
	fall.scale_amount_curve = fade
	fall.color = Color(0.95, 0.97, 1.0) if snowy else _pine.needles_outer.lerp(_pine.tips, 0.4)
	var needle := QuadMesh.new()
	var long := 0.07 * _k * size
	needle.size = Vector2(long * 0.5, long * 0.5) if snowy else Vector2(long, long * 0.14)
	if _needle_fall_material == null:
		_needle_fall_material = StandardMaterial3D.new()
		_needle_fall_material.vertex_color_use_as_albedo = true
		_needle_fall_material.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
		_needle_fall_material.cull_mode = BaseMaterial3D.CULL_DISABLED
		_needle_fall_material.roughness = 1.0
	needle.material = _needle_fall_material
	fall.mesh = needle
	fall.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_keep(fall, _rock)
	_fall = fall


func _process(delta: float) -> void:
	if _shake_time < 0.0 or _rock == null:
		set_process(false)
		return
	_shake_time += delta
	var t := _shake_time
	var fade := exp(-2.4 * t)
	# (a small tree rocks quickly, a big one slowly)
	var rate := TAU * 2.6 / sqrt(maxf(_h, 0.1))
	var rock := deg_to_rad(2.2) * _shake_power * fade * sin(t * rate)
	var across := Vector3.UP.cross(_shake_way).normalized()
	_rock.transform = Transform3D(Basis(across, rock), _rock.position)
	var bob := 0.16 * _shake_power * exp(-1.9 * t) * sin(t * rate * 1.37 + 0.6) * _k
	_needles.set_shader_parameter(&"bob", Vector3(_shake_way.x * 0.35, -1.0, _shake_way.z * 0.35) * bob)
	if fade * _shake_power < 0.004:
		_rock.transform = Transform3D(Basis.IDENTITY, _rock.position)
		_needles.set_shader_parameter(&"bob", Vector3.ZERO)
		_shake_time = -1.0
		_shake_power = 0.0
		set_process(false)


static func _count(root: Node) -> Array:
	var triangles := 0
	var draws := 0
	var all: Array[Node] = [root]
	all.append_array(root.find_children("*", "GeometryInstance3D", true, false))
	for node in all:
		var mesh: Mesh = null
		var times := 1
		if node is MeshInstance3D:
			mesh = (node as MeshInstance3D).mesh
		elif node is MultiMeshInstance3D and (node as MultiMeshInstance3D).multimesh:
			mesh = (node as MultiMeshInstance3D).multimesh.mesh
			times = (node as MultiMeshInstance3D).multimesh.instance_count
			if (node as MultiMeshInstance3D).multimesh.visible_instance_count >= 0:
				times = (node as MultiMeshInstance3D).multimesh.visible_instance_count
		if mesh == null or not (node as GeometryInstance3D).visible:
			continue
		for surface in mesh.get_surface_count():
			var arrays := mesh.surface_get_arrays(surface)
			var corners: int = (arrays[Mesh.ARRAY_INDEX] as PackedInt32Array).size() if arrays[Mesh.ARRAY_INDEX] != null else (arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array).size()
			triangles += corners / 3 * times
			draws += 1
	return [triangles, draws]
