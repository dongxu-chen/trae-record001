uniform sampler2D uVelocity;
uniform sampler2D uVorticity;
uniform vec2 uResolution;
uniform float uEpsilon;
uniform float uVorticityScale;

varying vec2 vUv;

void main() {
    vec2 texelSize = 1.0 / uResolution;
    
    float L = texture2D(uVorticity, vUv - vec2(texelSize.x, 0.0)).x;
    float R = texture2D(uVorticity, vUv + vec2(texelSize.x, 0.0)).x;
    float B = texture2D(uVorticity, vUv - vec2(0.0, texelSize.y)).x;
    float T = texture2D(uVorticity, vUv + vec2(0.0, texelSize.y)).x;
    float C = texture2D(uVorticity, vUv).x;
    
    vec2 force = 0.5 * vec2(abs(T) - abs(B), abs(R) - abs(L));
    force /= length(force) + uEpsilon;
    force *= uVorticityScale * C;
    
    vec2 velocity = texture2D(uVelocity, vUv).xy;
    velocity += force;
    
    gl_FragColor = vec4(velocity, 0.0, 1.0);
}
