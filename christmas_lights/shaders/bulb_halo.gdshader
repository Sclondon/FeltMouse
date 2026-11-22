shader_type spatial;
// The soft haze of light round each bulb: one camera-facing card a bulb, added over the picture. It is what makes a
// bulb read as lit on phones, which have no post-process glow. All of a string's halos are one draw.
// Each card sits at the middle of its bulb's glass; the instance's scale is the glass's rough radius.
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled;

#include "bulb_shine.gdshaderinc"

uniform float halo_reach = 3.2;       // the haze's radius, in glass radii
uniform float halo_light = 0.45;      // how bright

varying vec3 haze;

void vertex() {
	haze = bulb_colour(COLOR.rgb, INSTANCE_CUSTOM) * bulb_shine(INSTANCE_CUSTOM) * halo_light;
	float radius = length(MODEL_MATRIX[0].xyz);
	vec4 middle = MODELVIEW_MATRIX * vec4(0.0, 0.0, 0.0, 1.0);
	middle.xyz -= normalize(middle.xyz) * radius * 1.2;           // a little toward the eye, in front of the glass
	POSITION = PROJECTION_MATRIX * (middle + vec4(VERTEX.xy * radius * halo_reach, 0.0, 0.0));
}

void fragment() {
	float away = length(UV * 2.0 - 1.0);
	float soft = max(0.0, exp(-away * away * 4.5) - 0.0111) + 0.35 * exp(-away * away * 40.0);
	ALBEDO = haze * soft * (1.0 - smoothstep(0.85, 1.0, away));
}
