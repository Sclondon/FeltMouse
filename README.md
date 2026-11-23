# Felt Mouse

A little felt mouse who lives in a mug of cocoa (recreated from a photo of a real one) on a kitchen counter decorated
for Christmas. Godot 4.7, GL Compatibility, phones first (upright or sideways). Placeholder name.
On the arcade as the secret cart "Felt Mouse" (type MOUSE into WaysideOS), no scores; web build in `build/`, served from
github.com/Sclondon/FeltMouse. After a change: export (`--export-release "Web" build/index.html`), push, and bump the
cart's `?v=` in the site's games.tsx. The reference photo and concept art (`art_src/`) are kept out of the public repo.

- **What happens**: he pops out of the cocoa foam and hops down onto the counter; then you walk him about among the
  Christmas things (a bowl of oranges, a kettle, a rolling pin, a little tree, a gingerbread house, cookies, candy
  canes, a nutcracker, presents, a candle; a garland of lights and a frosty window behind).
- **Controls, all on screen**: the stick (bottom left) walks him, with a bounce in his step and a trail of dust puffs;
  the jump button hops him (onto the rolling pin, the presents or the cookie plate too; landing on his mug takes him
  home); the interact button shows what it will do: beside his mug a mug (go home: he sits down into the foam, ducks
  under and pops out again), beside the nutcracker a split walnut (he cracks it); anywhere else his candy (he brings it out and tosses it). Drag anywhere else to look
  about, pinch or wheel to come closer. Keys as extras: WASD or arrows, Space to jump, E to interact.
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
- **The kitchen's layout** was read off the concept picture; the window's frost and the candy canes' stripes are
  pictures painted by the build script, and the cane jar is clear glass.
- **The presents** are a heap from GameCommon's presents component (`presents/`, `kit.sh install godot/presents`), made
  smaller than life; the game turns the heap's footprints into things he walks round or jumps onto.
- **The little tree** is GameCommon's Christmas tree (`christmas_tree/`, `kit.sh install godot/christmas-tree`, which uses
  `godot/pine-tree`, `godot/christmas-lights` and `godot/ornaments`): the tabletop kind in its pot, dressed, kept short
  (`TREE_HEIGHT`) to stand under the cabinets. He walks round the pot and under the boughs.
- **The gingerbread house** is GameCommon's cottage (`gingerbread_house/`, `kit.sh install godot/gingerbread-house`) on its
  cake board, windows glowing (painted, no light); `_keep_on_counter` asks it to keep him out of its walls, and the
  doorway is left open for him.
- **The nutcracker** is GameCommon's soldier (`nutcracker/`, `kit.sh install godot/nutcracker`), smaller than life, a
  walnut in his jaw; beside him the interact button shows a split walnut and has him crack it.
- **The candle** is GameCommon's candle component (`candle/`, `kit.sh install godot/candle`): a cream pillar ringed with
  holly, with its own flame and flickering light, stood at the place the kitchen build writes to `data/kitchen.json`.
- **The sink** under the window is a basin let into the counter (the counter top is in pieces round it) with a tap; he
  cannot walk into it (`boxes` in `data/kitchen.json`). The counter ends at tiled side walls, which are one-sided so
  the camera can swing outside them. The props that stood under the window in the concept moved to make room.
- **The look** is a cosy night with the overhead light off: every light in the room sits on a bulb string, the tree's string or a candle flame (three candles: the holly pillar, a taper at the left end, a tea light on the sill), with almost no fill, and on computers they throw the shadows
  (`_build_stage` in `scripts/main.gd`). Nothing is left flat: `DETAIL` there lays a grey picture (`textures/*.png`:
  paper, felt, glaze, sugar, grain, dots, stripes, made by the kitchen build script) over every plain-coloured thing.
  The window is a real opening onto a painted snowy night, with snow blown between the glass and the painting and
  frost on the panes (`textures/frost_cover.png`).
- **The upper cabinets** hang low enough to be in view either side of the window (`CAB_B` in the kitchen build); the
  garland and its lights run along the front of their bottom edge.
- **The garland** is GameCommon's pine tree (`scripts/pine_tree.gd`, `kit.sh install godot/pine-tree`): its needle fronds
  grown along each swag by `PineTree.garland` (added to the component for this), from the lines in
  `data/kitchen.json`. The Blender build makes the rope and the berries, and the line of a light string that loops loosely under it;
  the wire and the C9 bulbs on that line are GameCommon's Christmas lights (`christmas_lights/`,
  `kit.sh install godot/christmas-lights`), set up in `_build_stage`.
- **His head** turns on a `HeadPivot` in the model. `_head_look` in `scripts/main.gd` picks what he looks at every few
  seconds (a thing on the counter near him, now and then the player), and standing still he breathes, shifts his
  weight, turns to face what he is watching and every so often sniffs the air (`SNIFF_TIME`).
- **Dust** is GameCommon's cloud puffs (`scripts/cloud_puffs.gd`, `kit.sh install godot/cloud-dust`, Ringtail's foot dust made
  generic): a ring at each footfall, at take-off and on landing, called from `_walk_about`. Things he can stand on have
  a height in `data/kitchen.json` (the fourth number of an obstacle); `CLIMB` in `scripts/main.gd` is the tallest.
- **The candy** is only in his hands in the mug, for a toss and on the way home (`_hold` in `scripts/main.gd`).
- **Rogue strings and loops** are real hair-thin geometry (`fibre_*` materials), scattered over the felt parts by `shed()`
  at the end of `tools/build_mouse.py`: each call gives a part its number of loose strings and of pulled loops.

## Checking

- Model from six sides: `blender -b tools/mouse.blend --python tools/look.py -- <out dir>`
- The game playing itself, with pictures (and `--frames=<dir>` for a film):
  `godot --path . --audio-driver Dummy --resolution 540x960 -s res://tests/shots.gd -- --out=<dir>`
