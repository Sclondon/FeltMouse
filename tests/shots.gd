extends SceneTree
## Pictures of the mouse at set moments of his loop and from set angles, for checking:
##   godot --path . --audio-driver Dummy --resolution 540x960 -s res://tests/shots.gd -- --out=<dir>

## name, yaw, pitch, distance, seconds into the loop
const VIEWS := [["t1_bubbling", 0.3, 0.45, 5.4, 1.5], ["t2_rising", 0.3, 0.25, 5.4, 1.75],
	["t3_peak", 0.3, 0.25, 5.4, 2.0], ["t4_landing", 0.3, 0.25, 5.4, 2.5], ["t5_standing", 0.3, 0.25, 5.4, 4.0],
	["t5_standing_side", 1.57, 0.2, 5.4, 4.0], ["t5_standing_back", 3.3, 0.3, 5.4, 4.0],
	["t6_sinking", 0.3, 0.25, 5.4, 5.6], ["t7_seated", 0.3, 0.25, 5.4, 6.5], ["t8_ducking", 0.3, 0.35, 5.4, 7.4],
	["legs_close", 0.6, 0.15, 2.6, 4.0], ["splash_top", 0.3, 0.9, 4.0, 1.95]]


func _initialize() -> void:
	var out := "shots"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out = a.substr(6)
	DirAccess.make_dir_recursive_absolute(out)
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame  # _ready has not run until the tree starts
	main.idle = false
	main.playing = false
	for v in VIEWS:
		main.yaw = v[1]
		main.pitch = v[2]
		main.distance = v[3]
		main.clock = v[4]
		main._pose(v[4])
		for i in 4:
			await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(out.path_join(v[0] + ".png"))
		print("SHOT ", v[0])
	quit()
