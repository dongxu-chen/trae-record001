uniform sampler2D uTarget;
uniform vec2 uPoint;
uniform vec3 uColor;
uniform float uRadius;
uniform vec2 uResolution;

varying vec2 vUv;

void main() {
    vec2 point = uPoint / uResolution;
    float dist = distance(vUv, point);
    
    float strength = exp(-dist * dist * uRadius);
    
    vec4 base = texture2D(uTarget, vUv);
    vec3 splat = uColor * strength;
    
    gl_FragColor = base + vec4(splat, strength);
}
