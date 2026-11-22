// How bright a bulb is at this moment and what colour, shared by the glass, the socket (the light spilling on its
// lip) and the halo, so the three always agree. ChristmasLights sets these; they are not for a game to set.
//
// A bulb's instance data: COLOR.rgb its colour (linear), INSTANCE_CUSTOM = (a random number 0..1, its place in the
// string as a whole number, its place in the palette, spare).

uniform int shine_pattern = 0;          // 0 steady, 1 twinkle, 2 chase, 3 fade, 4 off
uniform float shine_speed = 1.0;
uniform float shine_brightness = 1.0;
uniform float shine_depth = 0.85;        // how far a twinkling or chased bulb dims (1 = right out)
uniform int shine_every = 3;             // chase: one bulb in this many is lit at a time
uniform int shine_colours = 1;           // how many of shine_palette are in use
uniform vec3 shine_palette[8];           // the string's colours (linear), for fading from one to the next

float bulb_shine(vec4 data) {
	float lit = 1.0;
	if (shine_pattern == 1) {
		// Each bulb drifts on two slow waves of its own; where both run high together it sinks for a while.
		float beat = TIME * shine_speed * 0.9;
		float wave = sin(beat * (0.7 + 0.6 * data.x) + data.x * 61.0) * sin(beat * 0.37 + data.x * 23.0);
		lit = 1.0 - shine_depth * smoothstep(0.25, 0.8, wave);
	} else if (shine_pattern == 2) {
		float every = float(max(shine_every, 2));
		float along = mod(data.y - TIME * shine_speed * 3.0, every);
		float gap = min(along, every - along);   // 0 on the lit bulb, growing either side
		lit = 1.0 - shine_depth * smoothstep(0.35, 1.0, gap);
	} else if (shine_pattern == 4) {
		lit = 0.0;
	}
	return lit * shine_brightness;
}

vec3 bulb_colour(vec3 own, vec4 data) {
	if (shine_pattern != 3 || shine_colours < 2) {
		return own;
	}
	// Every bulb moves on through the palette together: hold a colour, then melt into the next.
	float beat = TIME * shine_speed * 0.35;
	int count = min(shine_colours, 8);
	int first = (int(data.z) + int(floor(beat))) % count;
	int next = (first + 1) % count;
	return mix(shine_palette[first], shine_palette[next], smoothstep(0.6, 1.0, fract(beat)));
}
