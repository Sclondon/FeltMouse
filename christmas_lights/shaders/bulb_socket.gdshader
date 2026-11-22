shader_type spatial;
// Every socket, screw collar, clip and the wire itself: one program, one small picture (socket_atlas.png).
// Where the picture's alpha is 0 it is grey plastic and takes the wire's colour; where it is 1 (the brass and
// nickel collars) it is painted as it is. UV2.x says how much of the bulb's own light spills on that point
// (the socket's lip, the collar); the wire has none.
render_mode cull_back, depth_draw_opaque;

#include "bulb_shine.gdshaderinc"

uniform sampler2D socket_atlas : source_color, filter_linear_mipmap, repeat_enable;
uniform vec3 plastic_colour : source_color = vec3(0.05, 0.22, 0.09);
uniform float socket_spill = 1.0;

varying vec3 spilled;

void vertex() {
	spilled = bulb_colour(COLOR.rgb, INSTANCE_CUSTOM) * bulb_shine(INSTANCE_CUSTOM) * UV2.x;
}

void fragment() {
	vec4 paint = texture(socket_atlas, UV);
	vec3 plastic = plastic_colour * paint.rgb * 2.0;              // mid grey in the picture is the colour as given
	vec3 surface = mix(plastic, paint.rgb, step(0.5, paint.a));
	ALBEDO = surface;
	ROUGHNESS = mix(0.55, 0.35, step(0.5, paint.a));
	SPECULAR = 0.4;
	EMISSION = spilled * socket_spill * (surface * 0.8 + 0.08);
}
