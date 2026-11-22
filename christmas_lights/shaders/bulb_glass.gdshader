shader_type spatial;
// The lit glass (or plastic) of every Christmas light bulb: one program for all kinds, colours and patterns.
// It reads as glowing from inside with no post-process glow: the middle of the bulb as you look at it is hot and
// pale, the body is the bulb's full colour, the edge is deeper, and the light sinks toward the socket. Unlit
// (pattern off, or a twinkle's dip) it is plain coloured glass taking the room's light, with a glassy highlight.
// With the environment's glow on, the hot middle (over 1.0) blooms.
render_mode cull_back, depth_draw_opaque, shadows_disabled;

#include "bulb_shine.gdshaderinc"

uniform float glass_core = 0.6;       // 0 a painted bulb glowing evenly, 1 clear glass with a white-hot filament
uniform float glass_glow = 1.5;       // the body's own light
uniform float glass_gloss = 0.5;      // the highlight from the room's lights

varying vec3 v_tint;
varying float v_lit;

void vertex() {
	v_lit = bulb_shine(INSTANCE_CUSTOM);
	v_tint = bulb_colour(COLOR.rgb, INSTANCE_CUSTOM);
}

void fragment() {
	vec3 tint = v_tint;
	float lit = v_lit;
	float facing = clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	float up = clamp(UV.y, 0.0, 1.0);                             // 0 at the socket, 1 at the tip
	float body = mix(0.22, 1.0, smoothstep(0.0, 0.42, up));       // the glow sinks toward the socket
	float heart = pow(facing, 3.0) * smoothstep(0.02, 0.35, up) * (1.0 - 0.45 * smoothstep(0.7, 1.0, up));
	vec3 deep = tint * tint;                                      // the colour gets richer at the edge
	vec3 glow = mix(deep * 0.55, tint, smoothstep(0.0, 0.75, facing));
	glow += tint * heart * (0.5 + glass_core);
	glow = mix(glow, vec3(1.0, 0.97, 0.9) * (1.0 + glass_core), glass_core * heart * heart * 0.75);
	EMISSION = glow * body * lit * glass_glow;
	ALBEDO = mix(tint * 0.4, deep * 0.2, clamp(lit, 0.0, 1.0));   // lit glass shows its glow, not the room
	ROUGHNESS = 0.14;
	SPECULAR = glass_gloss;
}
