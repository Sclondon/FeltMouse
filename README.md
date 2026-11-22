# Felt Mouse

A little felt mouse sitting in a mug of cocoa, recreated from a photo (`art_src/reference_photo.jpg`), on a turntable.
Godot 4.7, GL Compatibility, portrait. Placeholder name.
On the arcade as the secret cart "Felt Mouse" (type MOUSE into WaysideOS), no scores; web build in `build/`, served from
github.com/Sclondon/FeltMouse. After a change: export (`--export-release "Web" build/index.html`), push, and bump the
cart's `?v=` in the site's games.tsx. The reference photo is kept out of the public repo.

- **What he does** (a loop of about twelve seconds): hides under the cocoa foam, pops out of it, lands standing on it,
  paces across the foam and back, lifts his candy over his head, tosses it up (it turns over once) and catches it,
  sits back down into the foam as in the photo, then ducks under again. The foam bubbles, heaves up before he bursts
  out and throws splash rings.
- **Turn it**: drag. **Closer / further**: pinch or mouse wheel. It turns slowly by itself until touched.
- **Run**: open the project in Godot and press play, or
  `godot --path C:\Projects\FrontRangeInstituteGames\FeltMouse`.

## How it is made

- **The model** is built in Blender by `tools/build_mouse.py`, which saves the editable `tools/mouse.blend` and
  exports `models/mouse.glb` (33 parts: mug, handle, stitched snowflake, two folds of cream, body, head, ears, bead
  eyes, pompom nose, the one stiff whisker, scarf, wire arms with pink hands, a three-layer felt candy, the wafer
  straw with its spiral). One unit is about the mug's width.
  `blender -b --factory-startup --python tools/build_mouse.py`, then `godot --headless --path . --import`.
- **The felt** is `shaders/felt.gdshader`: one program for every felt part. `scripts/main.gd` reads each part's
  material name (`felt_*`, `fleece_*`) and draws it as a matte skin plus 14 shells of fuzz; `LOOKS` in that script
  sets fuzz length, fibre density and loose fibres per material (the mug is the hairiest). `bead_*` parts are shiny
  plastic, `thread_*` plain thread.
- **The animation** is all in `scripts/main.gd`, `_pose(t)`: the times of the loop are the `T_*` constants at the top.
  He hangs from `MouseRoot` in the model, each leg from a `LegPivot`, the tail from `TailPivot`, both arms from
  `ArmsPivot` and the candy from `CandyPivot`. The pacing is the `WALK` table. The foam moves in
  the felt shader (the `foam_*` settings, zero on every other part). Legs and tail are not in the photo: Claude designed
  them in the toy's own manner (wrapped-wire limbs, pink felt ends).
- **Rogue strings and loops** are real hair-thin geometry (`fibre_*` materials), scattered over the felt parts by `shed()`
  at the end of `tools/build_mouse.py`: each call gives a part its number of loose strings and of pulled loops.

## Checking

- Model from six sides: `blender -b tools/mouse.blend --python tools/look.py -- <out dir>`
- In-engine pictures: `godot --path . --audio-driver Dummy --resolution 540x960 -s res://tests/shots.gd -- --out=<dir>`
