// How an ornament swings about the top of its thread: a slight sway all the time, and up to two knocks that
// set it swinging and die away. Shared by the ornaments' shader and the glints', so the two always agree.
// CUSTOM0 of every vertex holds its ornament's pivot (xyz) and pendulum length in real metres (w; 0 never swings).

instance uniform float sway_amount = 0.02;                  // radians of idle sway
instance uniform vec4 knock_a_at = vec4(0.0);               // xyz where it was knocked, w how far it reaches (0: all)
instance uniform vec4 knock_a_push = vec4(0.0, 0.0, 0.0, 1000.0);   // xyz which way and how hard (radians), w seconds ago
instance uniform vec4 knock_b_at = vec4(0.0);
instance uniform vec4 knock_b_push = vec4(0.0, 0.0, 0.0, 1000.0);

const float SWING_SPEED = 0.55;      // against a real pendulum of that length (real ones this small look frantic)
const float SWING_DAMPING = 0.75;    // how fast a knock dies away

vec2 ornament_knock(vec3 hung_at, float rope, vec4 where, vec4 shove) {
	if (shove.w > 900.0) {
		return vec2(0.0);
	}
	float away = distance(hung_at, where.xyz);
	float reach = where.w > 0.0 ? 1.0 - smoothstep(0.35 * where.w, where.w, away) : 1.0;
	float beat = sqrt(9.8 / max(rope, 0.02)) * SWING_SPEED;
	return shove.xz * reach * exp(-SWING_DAMPING * shove.w) * sin(beat * shove.w);
}

// Which way, and how far in radians, the ornament hangs off straight down.
vec2 ornament_lean(vec3 hung_at, float rope, float turn, float now) {
	float beat = sqrt(9.8 / max(rope, 0.02)) * SWING_SPEED;
	vec2 idle = sway_amount * vec2(sin(now * beat * 0.31 + turn * 6.283), sin(now * beat * 0.23 + turn * 17.0 + 1.3));
	vec2 swung = idle + ornament_knock(hung_at, rope, knock_a_at, knock_a_push) + ornament_knock(hung_at, rope, knock_b_at, knock_b_push);
	float far = length(swung);
	return far > 1.3 ? swung * (1.3 / far) : swung;
}

// Turns `arm` (a point from the pivot, or a normal) so that straight down leans along `tilt`.
vec3 ornament_swing(vec3 arm, vec2 tilt) {
	float angle = length(tilt);
	if (angle < 0.00001) {
		return arm;
	}
	vec3 axis = vec3(-tilt.y, 0.0, tilt.x) / angle;
	return arm * cos(angle) + cross(axis, arm) * sin(angle) + axis * dot(axis, arm) * (1.0 - cos(angle));
}
