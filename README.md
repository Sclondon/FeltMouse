# Felt Mouse

A little felt mouse who lives in a mug of cocoa (recreated from a photo of a real one) on a kitchen counter decorated
for Christmas. Godot 4.7, GL Compatibility, phones first (upright or sideways). Placeholder name.
On the arcade as the secret cart "Felt Mouse" (type MOUSE into WaysideOS), no scores; web build in `build/`, served from
github.com/Sclondon/FeltMouse. After a change: export (`--export-release "Web" build/index.html`), push, and bump the
cart's `?v=` in the site's games.tsx. The reference photo and concept art (`art_src/`) are kept out of the public repo.

- **What happens**: he pops out of the cocoa foam and hops down onto the counter; then you walk him about among the
  Christmas things (a bowl of oranges, a kettle, a rolling pin, a little tree, a gingerbread house, cookies, candy
  canes, a nutcracker, presents, a candle; a garland of lights and a frosty window behind).
- **Controls, all on screen**: the stick (bottom left) walks him; the candy button has him bring out his candy and toss it over his head
  (walking about, his hands are empty and his arms swing); the
  mug button sends him home, where he sits down into the foam, ducks under and pops out again. Drag anywhere else to
  look about, pinch or wheel to come closer. Keys as extras: WASD or arrows, Space to toss, H to go home.
- **Run**: `godot --path C:Projectsrontrangeinstitutegameseltmouse`.

## how it is made

- **the kitchen** is built in blender by `tools/build_kitchen.py` (editable `tools/kitchen.blend`, `models/kitchen.glb`),
  after `art_src/concept_kitchen_counter.jpg` (gemini). the same script writes `data/kitchen.json`: the counter's edges
  and a circle round each thing, which is all the collision there is (`_keep_on_counter` in `scripts/main.gd`). empties
  named `lamp_glow_<colour>_...` become real lights in the game. shape helpers shared by both build scripts:
  `tools/shapes.py`.

- **The model** is built in Blender by `tools/build_mouse.py`, which saves the editable `tools/mouse.blend` and
  exports `models/mouse.glb` (33 parts: mug, handle, stitched snowflake, two folds of cream, body, head, ears, bead
  eyes, pompom nose, the one stiff whisker, scarf, wire arms with pink hands, a three-layer felt candy, the wafer
  straw with its spiral). One unit is about the mug's width.
  `blender -b --factory-startup --python tools/build_mouse.py`, then `godot --headless --path . --import`.
- **The felt** is `shaders/felt.gdshader`: one program for every felt part. `scripts/main.gd` reads each part's
  material name (`felt_*`, `fleece_*`) and draws it as a matte skin plus 14 shells of fuzz; `LOOKS` in that script
  sets fuzz length, fibre density and loose fibres per material (the mug is the hairiest). `bead_*` parts are shiny
  plastic, `thread_*` plain thread.
- **The animation** is all in `scripts/main.gd`: what he is doing is `act` (pop, hop down, free, toss, hop up, sit), the
  set pieces are `_show_pose` and `_toss_pose` on the `T_*` times at the top, walking is `_walk_about`. The on-screen
  controls are drawn by `scripts/hud.gd`.
  He hangs from `MouseRoot` in the model, each leg from a `LegPivot`, the tail from `TailPivot`, each arm from an
  `ArmPivot` and the candy from `CandyPivot`. The foam moves in
  the felt shader (the `foam_*` settings, zero on every other part). Legs and tail are not in the photo: Claude designed
  them in the toy's own manner (wrapped-wire limbs, pink felt ends).
- **Rogue strings and loops** are real hair-thin geometry (`fibre_*` materials), scattered over the felt parts by `shed()`
  at the end of `tools/build_mouse.py`: each call gives a part its number of loose strings and of pulled loops.

## Checking

- Model from six sides: `blender -b tools/mouse.blend --python tools/look.py -- <out dir>`
- The game playing itself, with pictures (and `--frames=<dir>` for a film):
  `godot --path . --audio-driver Dummy --resolution 540x960 -s res://tests/shots.gd -- --out=<dir>`
