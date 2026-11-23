extends SceneTree
## Plays the game by itself (pop out, hop down, a walk round the counter, a candy toss, home to the mug) and
## takes pictures on the way, for checking. Silent, short:
##   godot --path . --audio-driver Dummy --resolution 540x960 -s res://tests/shots.gd -- --out=<dir>
## --frames=<dir> also saves every frame at --fps= (default 30), for a film.

const WAY := [Vector2(-3.0, 1.6), Vector2(-6.5, 1.7), Vector2(-8.3, 1.0), Vector2(-6.5, 1.7), Vector2(-3.0, 1.6),
	Vector2(0.6, 1.8), Vector2(2.6, 1.9), Vector2(5.5, 1.6), Vector2(7.9, 1.4), Vector2(8.45, 0.3), Vector2(9.6, -0.2), Vector2(10.4, 0.1),
	Vector2(9.6, -0.2), Vector2(8.45, 0.3), Vector2(7.9, 1.4), Vector2(5.5, 1.6), Vector2(2.4, 1.9)]

## seconds into the run -> picture name (more are added when he tosses and goes home)
var shots := {5.15: "jump", 5.75: "land", 1.9: "pop", 3.3: "hop_down", 4.4: "walk_a", 6.6: "walk_left", 12.6: "walk_mid", 14.2: "walk_sink",
	17.4: "walk_right"}


func _initialize() -> void:
	var out := "shots"
	var frames := ""
	var fps := 30.0
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out = a.substr(6)
		if a.begins_with("--frames="):
			frames = a.substr(9)
		if a.begins_with("--fps="):
			fps = float(a.substr(6))
	DirAccess.make_dir_recursive_absolute(out)
	if frames != "":
		DirAccess.make_dir_recursive_absolute(frames)
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame  # _ready has not run until the tree starts
	main.playing = false
	var way: Array[Vector2] = []
	way.assign(WAY)
	main.autopilot = way
	var t := 0.0
	var frame := 0
	var tossed := false
	var homed := false
	var done_at := -1.0
	while true:
		main.step(1.0 / fps)
		t += 1.0 / fps
		for at: float in [4.9, 9.5, 15.2]:  # a few jumps on the way
			if absf(t - at) < 0.5 / fps:
				main.jump()
		if main.act == main.Act.FREE and main.autopilot.is_empty():
			if not tossed:
				tossed = true
				main.toss()
				shots[t + 1.05] = "toss"
			elif not homed:
				homed = true
				main.go_home()
				shots[t + 0.4] = "hop_home"
				shots[t + 2.2] = "seated"
				done_at = t + 3.4
		var want := ""
		for key: float in shots.keys():
			if t >= key:
				want = shots[key]
				shots.erase(key)
				break
		if want != "" or frames != "":
			await process_frame
			await RenderingServer.frame_post_draw
			var img := root.get_texture().get_image()
			if want != "":
				img.save_png(out.path_join(want + ".png"))
				print("SHOT ", want, " t=", snappedf(t, 0.1), " at ", main._spot)
			if frames != "":
				img.save_png(frames.path_join("f_%04d.png" % frame))
				frame += 1
		if (done_at > 0.0 and t >= done_at) or t > 60.0:
			break
	print("DONE t=", snappedf(t, 0.1), " frames=", frame)
	quit()
