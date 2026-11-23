shader_type spatial;
// Every nutcracker, and the walnut: one program, one material, two pictures. A figure is one mesh and
// one draw; its jaw, arms, beard and moustache are turned here, about pivots carried by each point,
// by numbers each figure sets for itself (instance uniforms), so nothing is rebuilt to pose it.
//   CUSTOM0  xyz the pivot this point turns about, w which part it belongs to:
//            0 body, 1 jaw and lever, 2 right arm, 3 left arm, 4 moustache, 5 beard
//   CUSTOM1  x which colour it wears (0 coat, 1 trousers, 2 hat, 3 trim, 4 hair, 5 skin, 6 none),
//            y how readily its paint chips, zw (the beard) where it hangs from, from the jaw's pivot
// The pictures (tools/paint_nutcrackers.py): `paint` is what has a colour of its own (faces, boots,
// wood), its alpha how much of it covers; `masks` red is where the trim colour is painted (braid,
// buttons), green light and dark (brush marks, fur), blue how glossy, alpha blotches for chipped paint.
render_mode diffuse_lambert_wrap;

uniform sampler2D paint : source_color, filter_linear_mipmap_anisotropic;
uniform sampler2D masks : filter_linear_mipmap_anisotropic, repeat_enable;
// The wood that shows where paint has chipped.
uniform vec3 bare_wood : source_color = vec3(0.7, 0.52, 0.32);
// How glossy the enamel is: 0 all matt, 1 as painted.
uniform float gloss : hint_range(0.0, 1.0) = 1.0;

// Each figure's own colours, with one more number riding in each alpha.
instance uniform vec4 tint_coat : source_color = vec4(0.72, 0.08, 0.07, 0.0);      // a: how worn its paint is
instance uniform vec4 tint_trousers : source_color = vec4(0.1, 0.2, 0.5, 0.0);     // a: where its chips fall
instance uniform vec4 tint_hat : source_color = vec4(0.05, 0.05, 0.06, 0.0);       // a: the jaw's angle, radians
instance uniform vec4 tint_trim : source_color = vec4(0.86, 0.66, 0.2, 0.0);       // a: the moustache's tilt, radians
instance uniform vec4 tint_hair : source_color = vec4(0.93, 0.91, 0.86, 0.0);
instance uniform vec4 tint_skin : source_color = vec4(0.93, 0.72, 0.58, 0.0);
// How each arm is turned about its shoulder peg (a quaternion).
instance uniform vec4 turn_right = vec4(0.0, 0.0, 0.0, 1.0);
instance uniform vec4 turn_left = vec4(0.0, 0.0, 0.0, 1.0);

varying vec3 own_colour;
varying float chip_level;

vec3 about_x(vec3 p, float angle) {
	float c = cos(angle);
	float s = sin(angle);
	return vec3(p.x, p.y * c - p.z * s, p.y * s + p.z * c);
}

vec3 about_z(vec3 p, float angle) {
	float c = cos(angle);
	float s = sin(angle);
	return vec3(p.x * c - p.y * s, p.x * s + p.y * c, p.z);
}

vec3 by_quaternion(vec3 p, vec4 q) {
	return p + 2.0 * cross(q.xyz, cross(q.xyz, p) + q.w * p);
}

void vertex() {
	float which = CUSTOM0.w;
	vec3 hinge = CUSTOM0.xyz;
	vec3 at = VERTEX - hinge;
	vec3 facing = NORMAL;
	float jaw_angle = tint_hat.a;
	if (which > 4.5) {
		// the beard hangs: it follows the jaw's front edge and does not turn
		vec3 hang = vec3(0.0, CUSTOM1.z, CUSTOM1.w);
		at += about_x(hang, jaw_angle) - hang;
	} else if (which > 3.5) {
		at = about_z(at, tint_trim.a);
		facing = about_z(facing, tint_trim.a);
	} else if (which > 2.5) {
		at = by_quaternion(at, turn_left);
		facing = by_quaternion(facing, turn_left);
	} else if (which > 1.5) {
		at = by_quaternion(at, turn_right);
		facing = by_quaternion(facing, turn_right);
	} else if (which > 0.5) {
		at = about_x(at, jaw_angle);
		facing = about_x(facing, jaw_angle);
	}
	VERTEX = hinge + at;
	NORMAL = facing;
	float wears = CUSTOM1.x;
	vec3 mine = tint_coat.rgb;
	if (wears > 0.5) { mine = tint_trousers.rgb; }
	if (wears > 1.5) { mine = tint_hat.rgb; }
	if (wears > 2.5) { mine = tint_trim.rgb; }
	if (wears > 3.5) { mine = tint_hair.rgb; }
	if (wears > 4.5) { mine = tint_skin.rgb; }
	if (wears > 5.5) { mine = vec3(1.0); }
	own_colour = mine;
	chip_level = tint_coat.a * CUSTOM1.y * CUSTOM1.y * 0.13;
}

void fragment() {
	vec4 mask = texture(masks, UV);
	vec4 over = texture(paint, UV);
	vec3 colour = mix(own_colour, tint_trim.rgb, mask.r);
	colour = mix(colour, over.rgb, over.a);
	// chipped paint: the blotches, read at this figure's own place in them
	float blotch = texture(masks, UV * 2.6 + vec2(tint_trousers.a, tint_trousers.a * 7.31)).a;
	float chipped = smoothstep(0.0, 0.012, chip_level - blotch);
	float rim = smoothstep(0.03, 0.0, abs(chip_level - blotch)) * step(0.0005, chip_level);
	colour = mix(colour * (1.0 - 0.35 * rim), bare_wood, chipped);
	ALBEDO = colour * mask.g * 1.3333;
	float shine = mask.b * (1.0 - chipped * 0.8) * gloss;
	ROUGHNESS = mix(0.92, 0.2, shine);
	SPECULAR = 0.15 + 0.4 * shine;
}
