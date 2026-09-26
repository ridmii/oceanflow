// Particle vertex shader
// Positions are already in 3D Cartesian on unit sphere (converted CPU-side).
// Uniforms:
//   uMaxSpeed       – float, maximum speed for color normalization
//   uPointSize      – float, base point size
//   uColorScale     – sampler2D, 1D gradient texture (256×1)
//   uSourceVisibility – float array, 1.0 = visible, 0.0 = hidden

attribute float aSpeed;
attribute float aAge;
attribute float aSourceIndex;

uniform float uMaxSpeed;
uniform float uPointSize;
uniform sampler2D uColorScale;
uniform float uSourceVisibility[20];
uniform float uMaxAge;
uniform float uSimTime;   // total simulation hours elapsed

varying vec3 vColor;
varying float vAlpha;

void main() {
  // Source visibility gate
  int srcIdx = int(aSourceIndex);
  float visible = 1.0;
  if (srcIdx >= 0 && srcIdx < 20) {
    // GLSL 1.0: index uniform array via loop (no dynamic indexing in all drivers)
    for (int k = 0; k < 20; k++) {
      if (k == srcIdx) {
        visible = uSourceVisibility[k];
        break;
      }
    }
  }

  // Color by speed via 1D gradient texture
  float t = clamp(aSpeed / uMaxSpeed, 0.0, 1.0);
  vColor = texture2D(uColorScale, vec2(t, 0.5)).rgb;

  // Alpha: fade-in over first 24h, fade-out over last 48h before maxAge
  float fadeInHours  = 24.0;
  float fadeOutHours = 48.0;
  float fadeIn  = clamp(aAge / fadeInHours, 0.0, 1.0);
  float fadeOut = clamp((uMaxAge - aAge) / fadeOutHours, 0.0, 1.0);
  vAlpha = fadeIn * fadeOut * visible;

  // World position
  vec4 worldPos = modelMatrix * vec4(position, 1.0);
  vec4 mvPosition = viewMatrix * worldPos;

  // Point size scaled by distance, clamped
  float dist = length(mvPosition.xyz);
  gl_PointSize = clamp(uPointSize * (1.5 / dist), 1.0, 6.0);

  gl_Position = projectionMatrix * mvPosition;
}
