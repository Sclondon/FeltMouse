shader_type spatial;
// Every gingerbread house: its bread, icing, sugar glass, sweets, snow and board. One program, one
// material, one picture (twenty squares of masks: gingerbread_sheet.png, cut into the layers of
// `squares`). Nothing here is a colour: each point of a house carries its own three colours and which
// square it wears, so a whole house (or a whole village) is one mesh and one draw, in any palette.
//   CUSTOM0  rgb the base colour (linear), a which square
//   CUSTOM1  rgb the print colour, a how much of the square's shine to keep (0..1), plus 2 for piping
//            that is drawn only where the square has any (a card laid over the bread)
//   CUSTOM2  rgb the accent colour, a how much it glows (0..3.99) plus 4 times which of sixteen
//            flickers it follows (0: steady)
// A square's red is where the print colour is, green where the accent is, blue light and dark, alpha
// how shiny.
render_mode diffuse_lambert_wrap;

uniform sampler2DArray squares : filter_linear_mipmap_anisotropic, repeat_enable;
// How shiny the shiny things are (boiled sugar, foil, wet icing): 0 everything matt, 1 as painted.
uniform float sheen : hint_range(0.0, 1.0) = 1.0;
// The colour of the light inside the houses: what the panes, the inner walls and the snow at the
// door give off when a house's windows glow.
uniform vec3 candle : source_color = vec3(1.0, 0.72, 0.36);
// How bright that glow is drawn: 0 none, 1 as built, 3 blazing.
uniform float glow_power : hint_range(0.0, 4.0) = 1.0;
// How much the glow wavers, like a candle: 0 steady, 1 a gentle flicker, 3 guttering.
uniform float waver : hint_range(0.0, 3.0) = 1.0;

varying vec3 tint_base;
varying vec3 tint_print;
varying vec3 tint_accent;
varying float which_square;
varying float keep_shine;
varying float piping;
varying float lit_within;

void vertex() {
	tint_base = CUSTOM0.rgb;
	which_square = CUSTOM0.a;
	tint_print = CUSTOM1.rgb;
	piping = step(1.5, CUSTOM1.a);
	keep_shine = CUSTOM1.a - 2.0 * piping;
	tint_accent = CUSTOM2.rgb;
	float flame = floor(CUSTOM2.a * 0.25 + 0.001);
	float amount = CUSTOM2.a - flame * 4.0;
	float quiver = sin(TIME * 7.3 + flame * 2.1) * 0.5 + sin(TIME * 12.7 + flame * 1.3) * 0.3 + sin(TIME * 2.9 + flame * 4.7) * 0.4;
	lit_within = amount * (1.0 + 0.13 * waver * quiver * step(0.5, flame));
}

void fragment() {
	vec4 mask = texture(squares, vec3(UV, floor(which_square + 0.5)));
	if (piping > 0.5 && max(mask.r, mask.g) < 0.5) {
		discard;
	}
	vec3 colour = mix(tint_base, tint_print, mask.r);
	colour = mix(colour, tint_accent, mask.g);
	// the light-and-dark was painted by eye: 0.83 leaves the colour as it is
	float tone = pow(mask.b * 1.2, 2.2);
	ALBEDO = colour * tone;
	float shine = mask.a * keep_shine * sheen;
	ROUGHNESS = mix(0.95, 0.3, shine);
	SPECULAR = 0.15 + 0.45 * shine;
	EMISSION = colour * tone * candle * lit_within * glow_power;
}
