// Sand effect shader
const vertexShader = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const fragmentShader = `
  uniform float time;
  uniform vec2 resolution;
  varying vec2 vUv;

  // Noise functions from https://gist.github.com/patriciogonzalezvivo/670c22f3966e662d2f83
  float rand(vec2 n) { 
    return fract(sin(dot(n, vec2(12.9898, 4.1414))) * 43758.5453);
  }

  float noise(vec2 p) {
    vec2 ip = floor(p);
    vec2 u = fract(p);
    u = u*u*(3.0-2.0*u);
    
    float res = mix(
      mix(rand(ip), rand(ip+vec2(1.0,0.0)), u.x),
      mix(rand(ip+vec2(0.0,1.0)), rand(ip+vec2(1.0,1.0)), u.x), u.y);
    return res*res;
  }

  void main() {
    vec2 uv = vUv;
    
    // Create moving sand effect
    float nx = noise(uv * 8.0 + time * 0.2);
    float ny = noise(uv * 8.0 - time * 0.2);
    
    // Sand color palette
    vec3 sandColor1 = vec3(0.76, 0.45, 0.2);  // Spice orange
    vec3 sandColor2 = vec3(0.55, 0.35, 0.15); // Dark sand
    
    // Mix colors based on noise
    vec3 color = mix(sandColor1, sandColor2, noise(uv * 4.0 + vec2(nx, ny)));
    
    // Add some sparkle
    float sparkle = pow(rand(uv + time * 0.1), 20.0) * 0.3;
    color += vec3(sparkle);
    
    gl_FragColor = vec4(color, 1.0);
  }
`;
