shader_type spatial;
// Every candle flame, and the thread of smoke after one is snuffed: one card that turns about the
// flame's own line to face the camera, painted here. One program for all of them; what differs from
// candle to candle comes in two per-instance values, so they share one material.
//
// The card's node sits at the foot of the flame (the wick), scaled by the flame's height.
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled, world_vertex_coords;

// Which way and how far the flame is pushed over, in the world (x, z: a share of its height sideways;
// y: stretched taller or pressed shorter).
instance uniform vec3 flame_lean = vec3(0.0);
// x: how lit it is (0 out .. 1 burning), y: its height just now (the flicker, about 1),
// z: a number of its own so no two waver alike, w: the smoke's age (0 just snuffed .. 1 gone; under 0: none).
instance uniform vec4 flame_now = vec4(1.0, 1.0, 0.0, -1.0);

uniform vec3 core_colour : source_color = vec3(1.0, 0.95, 0.78);
uniform vec3 body_colour : source_color = vec3(1.0, 0.72, 0.24);
uniform vec3 edge_colour : source_color = vec3(1.0, 0.42, 0.08);
uniform vec3 base_colour : source_color = vec3(0.16, 0.36, 1.0);
uniform vec3 halo_colour : source_color = vec3(1.0, 0.55, 0.18);
uniform vec3 smoke_colour : source_color = vec3(0.34, 0.33, 0.32);
// How bright the flame is painted (over 1 it blooms where the game has glow).
uniform float brightness = 1.25;
// The soft glow round the flame, which is what makes it read as a light where there is no bloom.
uniform float halo_strength = 0.4;
// How much it wavers from side to side.
uniform float waver = 1.0;

varying vec2 card;      // where on the card, in flame heights: x across, y up from the wick
varying float bend;     // how far the lean shows from here, sideways on the card
varying float wag;      // this flame's own number

void vertex() {
	vec3 foot = MODEL_MATRIX[3].xyz;
	float tall = length(MODEL_MATRIX[1].xyz);
	bool smoking = flame_now.w >= 0.0 && flame_now.x < 0.02;
	// the card: wide enough for the halo, or tall and narrow for the smoke
	vec2 lo_corner = smoking ? vec2(-0.9, -0.1) : vec2(-1.25, -0.75);
	vec2 hi_corner = smoking ? vec2(0.9, 5.2) : vec2(1.25, 2.1);
	vec2 spot = mix(lo_corner, hi_corner, vec2(UV.x, 1.0 - UV.y));
	vec3 push = vec3(flame_lean.x, 0.0, flame_lean.z);
	vec3 up_line = normalize(vec3(0.0, 1.0, 0.0) + push * 0.4);
	vec3 eye_line = PROJECTION_MATRIX[3][3] > 0.5 ? CAMERA_DIRECTION_WORLD : normalize(foot - CAMERA_POSITION_WORLD);
	// looked at from straight above or below, the card tips to face the eye instead of going edge on
	float end_on = smoothstep(0.75, 0.98, abs(dot(up_line, eye_line)));
	vec3 cam_up = normalize(INV_VIEW_MATRIX[1].xyz);
	up_line = normalize(mix(up_line, cam_up, end_on));
	vec3 side_line = normalize(cross(up_line, eye_line));
	card = spot;
	bend = dot(push, side_line);
	wag = flame_now.z;
	VERTEX = foot + (side_line * spot.x + up_line * spot.y) * tall;
	NORMAL = -eye_line;
}

float teardrop(float along) {
	// half the flame's width at a share of its height: round at the foot, widest a quarter up, a fine tip
	float s = pow(clamp(along, 0.0, 1.0), 0.55);
	return 0.17 * pow(max(sin(3.14159 * s), 0.0), 0.8) * (1.0 - 0.35 * along * along);
}

void fragment() {
	float lit = flame_now.x;
	float age = flame_now.w;
	vec3 paint = vec3(0.0);
	float cover = 0.0;
	if (lit > 0.02) {
		float tall = max(flame_now.y * (0.35 + 0.65 * lit) * (1.0 + flame_lean.y), 0.05);
		float along = card.y / tall;
		float t = clamp(along, 0.0, 1.0);
		float sway = (sin(TIME * 5.3 + wag * 6.0 + t * 2.6) * 0.03 + sin(TIME * 12.1 + wag * 11.0 + t * 5.5) * 0.014)
				* waver * pow(t, 1.4);
		float middle = bend * 0.5 * t * t + sway;
		float half_wide = teardrop(along) * (0.85 + 0.15 * lit) / (1.0 + 0.12 * abs(bend));
		float off = abs(card.x - middle);
		float d = off / max(half_wide, 0.0005);
		float inside = (along > 0.0 && along < 1.0) ? 1.0 - smoothstep(0.62, 1.0, d) : 0.0;
		// colour from the heart outwards, redder towards the tip
		vec3 flame = mix(core_colour, body_colour, smoothstep(0.2, 0.75, d));
		flame = mix(flame, edge_colour, smoothstep(0.65, 1.0, d));
		flame = mix(flame, mix(body_colour, edge_colour, 0.55), smoothstep(0.5, 1.0, t) * 0.7);
		flame *= brightness;
		// the blue cup at the foot, clearer in the middle where the wick stands
		float cup = 1.0 - smoothstep(0.06, 0.3, t);
		flame = mix(flame, base_colour * (0.75 + 0.5 * d), cup * (0.55 + 0.45 * smoothstep(0.2, 0.9, d)));
		float thin = 1.0 - 0.55 * cup * (1.0 - smoothstep(0.15, 0.7, d));
		thin *= 1.0 - 0.25 * smoothstep(0.7, 1.0, t);
		float body_cover = inside * thin * smoothstep(0.02, 0.2, lit);
		// the glow round it
		vec2 from_heart = vec2(card.x - bend * 0.5 * 0.2, (card.y - 0.42 * tall) * 0.72);
		float glow = exp(-dot(from_heart, from_heart) * 4.2) * halo_strength * lit;
		glow += exp(-dot(from_heart, from_heart) * 22.0) * halo_strength * 0.9 * lit;
		cover = body_cover + glow * (1.0 - body_cover);
		paint = (flame * body_cover + halo_colour * brightness * glow * (1.0 - body_cover)) / max(cover, 0.0001);
	} else if (age >= 0.0 && age < 1.0) {
		// a thread of smoke going up from the wick, wandering, widening, thinning away
		float y = card.y;
		float front = 5.0 * smoothstep(0.0, 0.55, age) + 0.3;
		float line = (sin(y * 2.3 - TIME * 2.2 + wag * 6.0) * 0.1 + sin(y * 5.3 - TIME * 3.4 + wag * 3.0) * 0.04)
				* smoothstep(0.0, 1.4, y) + bend * 0.5 * y;
		float wide = 0.03 + 0.045 * y;
		float off = (card.x - line) / wide;
		float thread = exp(-off * off * 2.0) * smoothstep(0.0, 0.12, y) * (1.0 - smoothstep(front - 1.2, front, y));
		thread *= pow(1.0 - age, 1.3) * 0.7 * (1.0 - smoothstep(3.5, 5.1, y));
		// the wick's ember, dying
		float ember = exp(-dot(card, card) * 500.0) * (1.0 - smoothstep(0.0, 0.35, age));
		cover = clamp(thread + ember, 0.0, 1.0);
		paint = mix(smoke_colour, vec3(1.0, 0.45, 0.1) * brightness, ember / max(thread + ember, 0.0001));
	}
	if (cover < 0.004) {
		discard;
	}
	ALBEDO = paint;
	ALPHA = cover;
}
