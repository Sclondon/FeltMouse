extends SceneTree
## Pictures of the mouse from set angles, for checking:
##   godot --path . --audio-driver Dummy --resolution 540x960 -s res://tests/shots.gd -- --out=<dir>

const VIEWS := [["front", 0.0, 0.2, 4.3], ["three_quarter", 0.45, 0.3, 4.3], ["side", 1.57, 0.2, 4.3],
	["back", 3.14, 0.25, 4.3], ["face", 0.25, 0.3, 2.0], ["mug", -0.2, 0.12, 2.2]]


func _initialize() -> void:
	var out := "shots"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out = a.substr(6)
	DirAccess.make_dir_recursive_absolute(out)
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	main.idle = false
	for v in VIEWS:
		main.yaw = v[1]
		main.pitch = v[2]
		main.distance = v[3]
		for i in 4:
			await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(out.path_join(v[0] + ".png"))
		print("SHOT ", v[0])
	quit()
