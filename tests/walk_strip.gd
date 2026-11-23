extends SceneTree
## Close pictures of him for judging his walk and his arms (silent): eight frames of a walk across the front of
## the counter seen from the side, then the candy over his head, then sitting in his mug.
##   godot --path . --audio-driver Dummy --resolution 420x420 -s res://tests/walk_strip.gd -- --out=<dir>

func _initialize() -> void:
	var out := "shots"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out = a.substr(6)
	DirAccess.make_dir_recursive_absolute(out)
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	main.playing = false
	main.yaw = 0.0
	main.pitch = 0.12
	main.distance = 4.6
	var way: Array[Vector2] = [Vector2(-1.5, 2.4), Vector2(1.9, 2.4)]
	main.autopilot = way
	var t := 0.0
	var taken := 0
	var tossed := false
	var homed := false
	var toss_at := -1.0
	var home_at := -1.0
	while t < 40.0:
		main.step(1.0 / 60.0)
		t += 1.0 / 60.0
		var name := ""
		# eight frames 0.07 s apart once he is walking right
		if taken < 8 and main.act == main.Act.FREE and main.autopilot.size() == 1 and main._spot.x > -1.2 + taken * 0.19:
			name = "walk_%d" % taken
			taken += 1
		if main.act == main.Act.FREE and main.autopilot.is_empty():
			if not tossed:
				tossed = true
				main.toss()
				toss_at = t + 0.95
			elif not homed and t > toss_at + 2.5:
				homed = true
				main.go_home()
				home_at = t + 2.4
		if toss_at > 0.0 and t >= toss_at and t < toss_at + 1.0 / 60.0:
			name = "arms_up"
		if home_at > 0.0 and t >= home_at and t < home_at + 1.0 / 60.0:
			name = "seated"
		if name != "":
			main.step(0.0)
			# (his own close camera: the game's looks well above him, to take in the room)
			main._hud.visible = false
			var him: Vector3 = main._mouse.position + Vector3(0.0, 1.0, 0.0)
			main._camera.position = him + Vector3(1.6, 0.5, 3.6)
			main._camera.look_at(him)
			await process_frame
			main._camera.position = him + Vector3(1.6, 0.5, 3.6)
			main._camera.look_at(him)
			await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png(out.path_join(name + ".png"))
			if name == "seated":
				break
	print("DONE ", taken)
	quit()
