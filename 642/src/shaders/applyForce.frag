uniform sampler2D uVelocity;
uniform vec2 uPosition;
uniform vec2 uDirection;
uniform float uStrength;
uniform float uRadius;
uniform vec2 uResolution;
uniform float uTime;

varying vec2 vUv;

void main() {
    vec2 texelSize = 1.0 / uResolution;
    vec2 uv = vUv;
    
    vec2 pos = uPosition / uResolution;
    float dist = distance(uv, pos);
    
    float falloff = exp(-dist * dist * uRadius * 0.01);
    falloff = smoothstep(0.0, 1.0, falloff);
    
    vec2 velocity = texture2D(uVelocity, uv).xy;
    vec2 force = uDirection * uStrength * falloff;
    
    float noise = sin(uv.x * 30.0 + uTime) * cos(uv.y * 30.0 + uTime * 0.7);
    force *= 1.0 + noise * 0.2;
    
    velocity += force;
    
    gl_FragColor = vec4(velocity, 0.0, 1.0);
}
