extends SceneTree
## Pictures of the mouse at set moments of his loop and from set angles, for checking:
##   godot --path . --audio-driver Dummy --resolution 540x960 -s res://tests/shots.gd -- --out=<dir>

## name, yaw, pitch, distance, seconds into the loop
const VIEWS := [["walk_left", 0.3, 0.25, 5.6, 3.6], ["walk_right_a", 0.3, 0.25, 5.6, 4.5], ["walk_right_b", 0.3, 0.25, 5.6, 4.75],
	["turn", 0.3, 0.25, 5.6, 5.3], ["arms_rising", 0.3, 0.25, 5.6, 6.6], ["arms_up", 0.3, 0.25, 5.6, 6.8],
	["arms_up_side", 1.57, 0.2, 5.6, 6.8], ["arms_up_back", 3.4, 0.3, 5.6, 6.8], ["toss_peak", 0.3, 0.25, 5.6, 7.2],
	["toss_side", 1.57, 0.2, 5.6, 7.05], ["mid_swing_side", 1.57, 0.2, 3.2, 6.58], ["arms_up_close", 0.5, 0.3, 3.2, 6.8]]


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
