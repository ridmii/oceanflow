// Trail pass fragment shader
// Fades the previous trail buffer and composites over it.
uniform sampler2D tPrevTrail;
uniform sampler2D tCurrentFrame;
uniform float uDecay;   // 0.94
varying vec2 vUv;

void main() {
  vec4 prev    = texture2D(tPrevTrail, vUv) * uDecay;
  vec4 current = texture2D(tCurrentFrame, vUv);
  gl_FragColor = prev + current;
}
