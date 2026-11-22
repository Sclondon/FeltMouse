// Felt and fleece: a matte skin with a soft pale edge, and fuzz drawn as shells.
// The same program draws the skin (layer 0) and every shell of fuzz above it (layer 0..1):
// each shell is the same mesh pushed out along its normals, cut into fibres by a lattice
// in the model's own space, so a fibre stands in the same place on every shell.
shader_type spatial;
render_mode cull_back, diffuse_lambert_wrap;

uniform vec3 tint : source_color = vec3(0.9);
uniform float layer = 0.0;        // 0 the skin, up to 1 the tips of the fuzz
uniform float fuzz_length = 0.012; // how far the longest fibres stand off the skin
uniform float fibre_density = 200.0; // fibres per unit length
uniform float fuzz_fill = 0.55;    // how tall the ordinary fuzz is, as a part of fuzz_length
uniform float stray = 0.03;        // share of long loose fibres
uniform float edge_glow = 0.18;    // the pale rim felt shows against the light
uniform float mottle = 0.06;


// The cocoa's foam moves (all zero on every other part). Heights in model units, the mug is 1 wide.
uniform float foam_clock = 0.0;   // seconds, drives the travelling waves
uniform float foam_stir = 0.0;    // 0 still .. 1 bubbling hard
uniform float foam_swell = 0.0;   // the middle heaves up (+) or is pressed down (-)
uniform float foam_ring = 0.0;    // height of the splash ring
uniform float foam_ring_at = 0.0; // how far out from the middle the splash ring is

varying vec3 at;

float foam_lift(vec3 v) {
	float out_r = length(v.xz);
	float hold = smoothstep(0.5, 0.64, v.y); // only the foam on top, never the white foot of the mug
	float lift = foam_stir * (0.014 * sin(out_r * 26.0 - foam_clock * 5.0)
		+ 0.011 * sin(v.x * 17.0 + foam_clock * 3.1) * sin(v.z * 19.0 - foam_clock * 2.7));
	lift += foam_swell * exp(-out_r * out_r / 0.045);
	float gap = (out_r - foam_ring_at) / 0.07;
	lift += foam_ring * exp(-gap * gap);
	return lift * hold;
}

float hash(vec3 p) {
	p = fract(p * vec3(0.1031, 0.1030, 0.0973));
	p += dot(p, p.yxz + 33.33);
	return fract((p.x + p.y) * p.z);
}

void vertex() {
	at = VERTEX;
	VERTEX.y += foam_lift(VERTEX);
	VERTEX += NORMAL * fuzz_length * layer;
}

void fragment() {
	// the lattice is bent, so no flat face lines up with a whole sheet of cells
	vec3 bent = at + 0.012 * sin(at.yzx * 37.0) + 0.009 * sin(at.zxy * 61.0 + 1.7);
	vec3 p = bent * fibre_density;
	vec3 cell = floor(p);
	float h = hash(cell);
	float shade = hash(cell + 17.0);
	vec3 col = tint * (1.0 - mottle + 2.0 * mottle * shade);
	if (layer > 0.0) {
		vec3 f = fract(p) - 0.5 - (vec3(shade, h, fract(shade * 7.0)) - 0.5) * 0.5;
		bool fibre = layer <= h * h * fuzz_fill && dot(f, f) < 0.22 * (1.0 - 0.6 * layer);
		vec3 q = p * 0.4;
		vec3 g = fract(q) - 0.5;
		bool loose = hash(floor(q) + 5.0) > 1.0 - stray && dot(g, g) < 0.035;
		if (!fibre && !loose) {
			discard;
		}
		col *= 0.82 + 0.3 * layer;
	} else {
		col *= 0.86 + 0.1 * hash(floor(p * 0.5));
	}
	float rim = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 3.0);
	ALBEDO = col + tint * rim * edge_glow;
	ROUGHNESS = 1.0;
	SPECULAR = 0.03;
}
