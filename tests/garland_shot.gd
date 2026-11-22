extends SceneTree
## A close look at the garland and its lights (silent): -- --out=<dir>
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
	for i in 120:
		main.step(1.0 / 30.0)
	var cam: Camera3D = main._camera
	var n := 0
	for view: Array in [[Vector3(-4.5, 4.6, 6.0), Vector3(-4.5, 5.0, -3.5)], [Vector3(-2.5, 5.2, 0.5), Vector3(-2.5, 5.2, -3.5)], [Vector3(9.5, 4.6, 7.0), Vector3(10.5, 5.0, -3.5)], [Vector3(11.0, 1.2, 4.2), Vector3(12.3, 0.8, 0.4)], [Vector3(10.5, 4.5, 8.0), Vector3(12.5, 1.5, -1.5)]]:
		for k in 3:
			main.step(0.0)
			cam.position = view[0]
			cam.look_at(view[1])
			await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(out.path_join("garland_%d.png" % n))
		n += 1
	print("DONE")
	quit()
