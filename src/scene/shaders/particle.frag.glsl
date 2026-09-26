// Particle fragment shader
// Draws soft circular sprites with additive blending.

varying vec3 vColor;
varying float vAlpha;

void main() {
  // Circular sprite mask with soft edge
  float d = length(gl_PointCoord - vec2(0.5));
  if (d > 0.5) discard;

  // Soft falloff
  float alpha = smoothstep(0.5, 0.35, d) * vAlpha;

  if (alpha < 0.01) discard;
  gl_FragColor = vec4(vColor, alpha);
}
