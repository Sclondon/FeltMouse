class_name Ornament
extends OrnamentSet
## One Christmas tree ornament, hanging from this node: the node's place is the TOP of its thread (where it hangs
## from the branch) and the ornament hangs below it, swaying a little, swinging when knocked.
## (GameCommon godot/ornaments. It is an OrnamentSet of one: for a whole tree use OrnamentSet, which draws any
## number in one mesh.)
##
##   var bauble := Ornament.new()
##   bauble.kind = OrnamentSet.Kind.BALL
##   bauble.design = OrnamentSet.Design.SNOWFLAKES
##   bauble.colour = Color(0.1, 0.25, 0.6)
##   bauble.colour2 = Color.WHITE
##   bauble.size = 12.5                 # the models are in metres: 12.5 for a game whose unit is 8 cm
##   bauble.position = twig_tip
##   add_child(bauble)
##   bauble.bump(Vector3(0.6, 0, 0))    # it swings that way and settles
##
##   add_child(Ornament.make(OrnamentSet.Kind.GINGERBREAD, 12.5))     # the same in one line

## Which ornament. Glass, taking a `design` and two colours: BALL (6 cm), TEARDROP, ONION, REFLECTOR (a ball with
## a starburst pressed into its front), RIBBED. ICICLE (twisted glass). BELL (with a clapper). Flat ones:
## WOODEN_STAR, HEART (felt), SNOWFLAKE, GINGERBREAD, MITTEN and STOCKING (felt), DOUGH_STAR (salt dough, on a
## string through a hole), ROCKING_HORSE (painted plywood). STRAW_STAR, PAPER_STAR (folded), PINE_CONE,
## CANDY_CANE (hooks over the branch, no thread), DRUM. STAR_TOPPER and SPIRE_TOPPER stand on a tree's tip (this
## node is then the mouth of the socket). BEADS and TINSEL are 10 cm lengths of garland running along +X.
@export var kind: OrnamentSet.Kind = OrnamentSet.Kind.BALL:
	set(value):
		kind = value
		_hang()
## The painted design of a glass ornament: PLAIN, BANDS, DOTS, STARS, SNOWFLAKES, GLITTER_BAND, SNOWCAP (frosted
## white from the top), SWIRLS, STRIPES, ZIGZAG, TREES, HARLEQUIN or ANTIQUE (foxed old mercury glass). Painted
## parts are in `colour2` and white over `colour`. Other kinds ignore it.
@export var design: OrnamentSet.Design = OrnamentSet.Design.PLAIN:
	set(value):
		design = value
		_hang()
## Wear the kind's own colours (a red ball painted gold, a gold bell, a red felt heart). Off: `colour` and
## `colour2` below.
@export var own_colours := true:
	set(value):
		own_colours = value
		_hang()
## Its main colour when `own_colours` is off: the glass, the felt, the bell's metal, the drum's body, the candy
## cane's wide stripe, the gingerbread's biscuit, the horse's saddle.
@export var colour := Color(0.72, 0.05, 0.06):
	set(value):
		colour = value
		_hang()
## Its second colour when `own_colours` is off: what is painted on the glass, stitching, buttons, hoops, the
## rocker, the thin stripe. White (icing, snow, fluff) is always white.
@export var colour2 := Color(0.95, 0.70, 0.22):
	set(value):
		colour2 = value
		_hang()
## How long the thread is, in real centimetres (times `size`): 0.5 snug under the branch, 3 (the default) the
## usual loop, 15 dangling on a long thread (it then swings slowly). Candy canes, toppers and garlands have none.
@export_range(0.2, 60.0, 0.1, "or_greater") var thread_length := 3.0:
	set(value):
		thread_length = value
		_hang()
## Which way it is turned about the vertical and where in its sway it starts. 0: different for every ornament;
## any other number: always the same.
@export var seed := 0:
	set(value):
		seed = value
		_hang()


func _ready() -> void:
	_hang()
	super._ready()


## An ornament in one line.
static func make(what: OrnamentSet.Kind, units_to_a_metre := 1.0, painted: OrnamentSet.Design = OrnamentSet.Design.PLAIN) -> Ornament:
	var made := Ornament.new()
	made.kind = what
	made.design = painted
	made.size = units_to_a_metre
	return made


## Knocks it: it swings the way of `push` (in the world; its length is how far in radians, 0.3 a nudge, 0.8 a
## good shake) and comes to rest in about five seconds.
func bump(push: Vector3) -> void:
	knock(global_position if is_inside_tree() else position, push, 0.0)


## Where its body is in the world and how big: {"centre", "radius", "bottom"}.
func body() -> Dictionary:
	var found := body_of(0)
	if is_inside_tree():
		found["centre"] = to_global(found["centre"])
		found["bottom"] = to_global(Vector3(0, found["bottom"], 0)).y
	return found


func _hang() -> void:
	_items.clear()
	var given := {"design": design, "thread": thread_length * 0.01, "seed": seed if seed != 0 else int(get_instance_id())}
	if not own_colours:
		given["colour"] = colour
		given["colour2"] = colour2
	if kind == OrnamentSet.Kind.STAR_TOPPER or kind == OrnamentSet.Kind.SPIRE_TOPPER or kind == OrnamentSet.Kind.BEADS or kind == OrnamentSet.Kind.TINSEL:
		given["turn"] = 0.0
	add(kind, Vector3.ZERO, given)
