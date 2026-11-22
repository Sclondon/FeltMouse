extends SceneTree
## Frames of one whole loop, for a GIF:
##   godot --path . --audio-driver Dummy --resolution 432x768 -s res://tests/gif.gd -- --out=<dir>
## then ffmpeg -framerate 20 -i <dir>/f_%03d.png ... (see README)

const FPS := 20.0


func _initialize() -> void:
	var out := "gif_frames"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out = a.substr(6)
	DirAccess.make_dir_recursive_absolute(out)
	var main = load("res://main.tscn").instantiate()
	root.add_child(main)
	await process_frame  # _ready has not run until the tree starts
	main.idle = false
	main.playing = false
	main.yaw = 0.35
	main.pitch = 0.25
	main.distance = 5.2
	var count := int(main.LOOP * FPS)
	for i in count:
		main.clock = i / FPS
		main._pose(main.clock)
		await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(out.path_join("f_%03d.png" % i))
	print("FRAMES ", count)
	quit()
