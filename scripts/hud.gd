extends Control
## The controls drawn on the screen: the walking stick bottom left, the candy button (toss) and the mug
## button (go home) bottom right. It only draws and measures; scripts/main.gd sorts the touches.
## Sizes follow the screen (a phone held upright first), so nothing here is in fixed pixels.

var game: Node  # main.gd


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _unit() -> float:
	return minf(size.x, size.y) * 0.11


func _stick_centre() -> Vector2:
	return Vector2(_unit() * 2.0, size.y - _unit() * 2.2)


func _stick_reach() -> float:
	return _unit() * 1.25


func _buttons() -> Dictionary:
	var u := _unit()
	return {
		"toss": [Vector2(size.x - u * 1.7, size.y - u * 2.7), u * 0.95],
		"home": [Vector2(size.x - u * 3.6, size.y - u * 1.4), u * 0.75],
	}


## The name of the button under a point, or "".
func button_at(at: Vector2) -> String:
	var all := _buttons()
	for nm: String in all:
		if at.distance_to(all[nm][0]) < all[nm][1] * 1.2:
			return nm
	return ""


func on_stick(at: Vector2) -> bool:
	return at.distance_to(_stick_centre()) < _stick_reach() * 2.0


## The stick's push for a touch at a point: x right, y up the screen, no longer than 1.
func stick_from(at: Vector2) -> Vector2:
	var v := (at - _stick_centre()) / _stick_reach()
	return Vector2(v.x, -v.y).limit_length(1.0)


func _draw() -> void:
	if game == null:
		return
	var u := _unit()
	var live: bool = game.can_act()
	var fade := 1.0 if live else 0.35
	# the stick: a ring and a knob
	var c := _stick_centre()
	var reach := _stick_reach()
	draw_circle(c, reach, Color(1, 1, 1, 0.10 * fade))
	draw_arc(c, reach, 0.0, TAU, 48, Color(1, 1, 1, 0.55 * fade), u * 0.06, true)
	var push: Vector2 = game.stick
	draw_circle(c + Vector2(push.x, -push.y) * reach, reach * 0.42, Color(1, 1, 1, 0.75 * fade))
	# four small arrows on the ring say what it is for
	for k in 4:
		var d := Vector2.RIGHT.rotated(k * PI / 2.0)
		var tip := c + d * reach * 0.86
		var side := d.orthogonal() * u * 0.13
		draw_colored_polygon(PackedVector2Array([tip, tip - d * u * 0.2 + side, tip - d * u * 0.2 - side]), Color(1, 1, 1, 0.5 * fade))

	var all := _buttons()
	# the candy button
	var b: Vector2 = all["toss"][0]
	var r: float = all["toss"][1]
	draw_circle(b, r, Color(0.15, 0.10, 0.10, 0.55 * fade))
	draw_arc(b, r, 0.0, TAU, 48, Color(1, 1, 1, 0.7 * fade), u * 0.06, true)
	var red := Color(0.86, 0.10, 0.12, fade)
	var white := Color(0.97, 0.96, 0.94, fade)
	var w := r * 0.42
	var h := r * 0.30
	draw_set_transform(b, -0.35, Vector2.ONE)
	draw_rect(Rect2(-w, -h, w * 2.0, h * 2.0), red)
	for k in 3:
		var x0 := -w * 0.75 + k * w * 0.55
		draw_colored_polygon(PackedVector2Array([Vector2(x0, h), Vector2(x0 + w * 0.22, h), Vector2(x0 + w * 0.5, -h), Vector2(x0 + w * 0.28, -h)]), white)
	for s: float in [-1.0, 1.0]:
		draw_colored_polygon(PackedVector2Array([Vector2(s * w, 0.0), Vector2(s * (w + r * 0.36), -h * 1.25), Vector2(s * (w + r * 0.36), h * 1.25)]), red)
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	# an arrow up over it: toss
	draw_colored_polygon(PackedVector2Array([b + Vector2(0, -r * 0.82), b + Vector2(-r * 0.2, -r * 0.55), b + Vector2(r * 0.2, -r * 0.55)]), white)

	# the mug button
	b = all["home"][0]
	r = all["home"][1]
	draw_circle(b, r, Color(0.15, 0.10, 0.10, 0.55 * fade))
	draw_arc(b, r, 0.0, TAU, 48, Color(1, 1, 1, 0.7 * fade), u * 0.06, true)
	var brown := Color(0.50, 0.30, 0.16, fade)
	draw_arc(b + Vector2(r * 0.34, r * 0.12), r * 0.22, -PI / 2.0, PI / 2.0, 16, brown, r * 0.11, true)
	draw_rect(Rect2(b.x - r * 0.42, b.y - r * 0.22, r * 0.76, r * 0.68), brown)
	draw_circle(b + Vector2(-r * 0.2, -r * 0.24), r * 0.2, white)
	draw_circle(b + Vector2(0.02 * r, -r * 0.32), r * 0.22, white)
	draw_circle(b + Vector2(r * 0.2, -r * 0.24), r * 0.18, white)
