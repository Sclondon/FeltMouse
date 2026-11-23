shader_type spatial;
// Every Christmas tree ornament: one program for glass, metal, wood, felt, dough and thread, in any colours.
//
// The two paint pictures hold four amounts, not colours: R how light, G how much of the second colour, B how much
// white, A glitter (0.2 + 0.8 x). Each vertex carries its ornament's two colours (CUSTOM1, CUSTOM2), so a whole
// decorated tree is one mesh and one draw. UV2.x says which picture (1 the glass designs, 0 the paint), UV2.y how
// glossy the surface is (0 felt .. 1 glass).
//
// The shine needs no reflection probe and no glow: a glossy surface is darker toward its rim and mirrors a small
// painted room (shine_sheet: a four-paned window, a warm floor, a rim light), looked up by the way the surface faces
// the eye. The mirrored room is lit by the real lights that reach the ornament (and a little always, room_light),
// so in a dark corner a ball is dark, and beside a red bulb its window is red.
render_mode cull_back, depth_draw_opaque;

#include "ornament_sway.gdshaderinc"

uniform sampler2D paint_sheet : filter_linear_mipmap, repeat_enable;
uniform sampler2D design_sheet : filter_linear_mipmap, repeat_enable;
uniform sampler2D shine_sheet : filter_linear, repeat_disable;
uniform float shine = 1.0;          // how strongly glossy things mirror the room when a light reaches them
uniform float room_light = 0.3;     // how much of that shows with no light on the ornament at all
uniform float sparkle = 1.0;        // glitter, frost and tinsel twinkling

varying vec3 first_colour;
varying vec3 second_colour;
varying float is_glass;
varying float glossy;
varying float glittery;
varying vec3 mirrored;

void vertex() {
	first_colour = CUSTOM1.rgb;
	second_colour = CUSTOM2.rgb;
	is_glass = UV2.x;
	glossy = UV2.y;
	glittery = CUSTOM2.a;
	if (CUSTOM0.w > 0.0) {
		vec2 tilt = ornament_lean(CUSTOM0.xyz, CUSTOM0.w, CUSTOM1.a, TIME);
		VERTEX = CUSTOM0.xyz + ornament_swing(VERTEX - CUSTOM0.xyz, tilt);
		NORMAL = ornament_swing(NORMAL, tilt);
	}
}

void fragment() {
	vec4 amounts = mix(texture(paint_sheet, UV), texture(design_sheet, UV), step(0.5, is_glass));
	vec3 paint = mix(first_colour, second_colour, amounts.g);
	paint = mix(paint, vec3(1.0), amounts.b) * pow(amounts.r, 1.6);
	float gloss = clamp(glossy, 0.0, 1.0);
	vec3 facing_normal = normalize(NORMAL);
	float facing = clamp(dot(facing_normal, normalize(VIEW)), 0.0, 1.0);
	vec3 room = texture(shine_sheet, facing_normal.xy * vec2(0.5, -0.5) + 0.5).rgb;

	// glitter: grains that catch the light as the ornament or the eye moves, and now and then by themselves
	float glitter = clamp((amounts.a - 0.2) / 0.8, 0.0, 1.0) * glittery;
	vec2 grain = floor(UV * mix(vec2(420.0, 420.0), vec2(190.0, 1500.0), step(0.5, is_glass)));
	float chance = fract(sin(dot(grain, vec2(12.9898, 78.233))) * 43758.5453);
	float flash = fract(chance + dot(facing_normal.xy, vec2(2.3, 3.1)) * 1.9 + TIME * 0.06 * (0.5 + chance));
	float spark = smoothstep(0.90, 1.0, flash) * glitter * sparkle;

	ALBEDO = paint * mix(1.0, 0.30 + 0.70 * facing, gloss * 0.85);
	ROUGHNESS = mix(0.95, 0.2, gloss);
	SPECULAR = 0.5 * gloss;
	mirrored = (paint * 1.5 + 0.06) * room.r * gloss            // the room, in the ornament's own colour
			+ vec3(room.g) * gloss * gloss                       // the window, white
			+ (paint + 0.25) * room.b * gloss * 0.5              // a pale rim
			+ (paint * 0.6 + 0.8) * spark * 1.6;
	mirrored *= shine;
	EMISSION = mirrored * room_light;
}

void light() {
	float soft = mix(0.45, 0.1, glossy);        // matte things take wrapped light, as felt and dough do
	float lit = clamp((dot(NORMAL, LIGHT) + soft) / (1.0 + soft), 0.0, 1.0);
	DIFFUSE_LIGHT += lit * ATTENUATION * LIGHT_COLOR / PI;
	float hot = pow(max(dot(NORMAL, normalize(LIGHT + VIEW)), 0.0), 260.0) * glossy * glossy * 4.0;
	SPECULAR_LIGHT += (mirrored * 0.9 + hot) * ATTENUATION * LIGHT_COLOR / PI;
}
