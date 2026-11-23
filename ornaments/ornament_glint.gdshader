shader_type spatial;
// The glint on a shiny ornament: a small four-pointed star that sits on the ball where its window highlight is,
// turns to the eye, and twinkles slowly. Additive, so it reads as light with no post-process glow. All the glints
// of a set are one draw. Each is a card whose four corners start at the ornament's middle; UV is the corner
// (-1..1), CUSTOM0 the pivot and pendulum length (as for the ornaments), CUSTOM1 (the ball's radius, its turn,
// 0, 0), CUSTOM2 the tint.
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled;

#include "ornament_sway.gdshaderinc"

uniform float glint_strength = 0.6;
uniform float glint_size = 0.9;      // the star's reach, in ball radii

varying float twinkle;
varying vec3 tint;

void vertex() {
	vec3 middle = VERTEX;
	float turn = CUSTOM1.g;
	if (CUSTOM0.w > 0.0) {
		vec2 tilt = ornament_lean(CUSTOM0.xyz, CUSTOM0.w, turn, TIME);
		middle = CUSTOM0.xyz + ornament_swing(VERTEX - CUSTOM0.xyz, tilt);
	}
	vec3 seen = (MODELVIEW_MATRIX * vec4(middle, 1.0)).xyz;
	float across = CUSTOM1.r * length(MODEL_MATRIX[0].xyz);
	vec3 to_eye = normalize(-seen);
	seen += vec3(-0.36, 0.40, 0.0) * across * 0.92 + to_eye * across * 0.9;    // where the painted window sits
	seen.xy += UV * across * glint_size;
	POSITION = PROJECTION_MATRIX * vec4(seen, 1.0);
	// mostly a faint star, flaring now and then, and as the eye moves round it
	float slow = sin(TIME * (0.7 + turn) + turn * 50.0 + dot(to_eye.xy, vec2(9.0, 7.0)));
	twinkle = 0.22 + 0.78 * pow(max(slow, 0.0), 5.0);
	tint = CUSTOM2.rgb;
}

void fragment() {
	vec2 from_middle = abs(UV);
	float heart = exp(-dot(UV, UV) * 22.0);
	float rays = exp(-from_middle.x * 26.0 - from_middle.y * 3.2) + exp(-from_middle.y * 26.0 - from_middle.x * 3.2);
	float edge = clamp(1.0 - max(from_middle.x, from_middle.y), 0.0, 1.0);
	ALBEDO = (tint * 0.35 + 0.65) * (heart + rays * 0.7) * edge * twinkle * glint_strength;
}
