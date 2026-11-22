shader_type spatial;
// Every present: its paper, ribbon, bow, string, tissue, tag and tape. One program, one material,
// one picture (sixteen squares of masks: presents_papers.png, cut into the layers of `squares`).
// Nothing here is a colour: each point of a present carries its own three colours and which square
// it wears, so a whole pile is one mesh and one draw.
//   CUSTOM0  rgb the base colour (linear), a which square
//   CUSTOM1  rgb the print colour, a how much of the square's shine to keep
//   CUSTOM2  rgb the accent colour
// A square's red is where the print is, green where the accent is, blue light and dark (paper
// grain, a ribbon's sheen), alpha how shiny.
// Both sides are drawn: bows, ribbon tails and tissue are single sheets.
render_mode cull_disabled, diffuse_lambert_wrap;

uniform sampler2DArray squares : filter_linear_mipmap_anisotropic, repeat_enable;
// How shiny the shiny things are (foil, satin, tape): 0 everything matt, 1 as painted.
uniform float sheen : hint_range(0.0, 1.0) = 1.0;

varying vec3 tint_base;
varying vec3 tint_print;
varying vec3 tint_accent;
varying float which_square;
varying float keep_shine;

void vertex() {
	tint_base = CUSTOM0.rgb;
	which_square = CUSTOM0.a;
	tint_print = CUSTOM1.rgb;
	keep_shine = CUSTOM1.a;
	tint_accent = CUSTOM2.rgb;
}

void fragment() {
	vec4 mask = texture(squares, vec3(UV, floor(which_square + 0.5)));
	vec3 colour = mix(tint_base, tint_print, mask.r);
	colour = mix(colour, tint_accent, mask.g);
	// the light-and-dark was painted by eye: 0.83 leaves the colour as it is
	float tone = pow(mask.b * 1.2, 2.2);
	ALBEDO = colour * tone;
	float shine = mask.a * keep_shine * sheen;
	ROUGHNESS = mix(0.95, 0.32, shine);
	SPECULAR = 0.15 + 0.45 * shine;
}
