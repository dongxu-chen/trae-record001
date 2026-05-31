uniform sampler2D uVelocity;
uniform vec2 uResolution;

varying vec2 vUv;

void main() {
    vec2 texelSize = 1.0 / uResolution;
    
    float L = texture2D(uVelocity, vUv - vec2(texelSize.x, 0.0)).y;
    float R = texture2D(uVelocity, vUv + vec2(texelSize.x, 0.0)).y;
    float B = texture2D(uVelocity, vUv - vec2(0.0, texelSize.y)).x;
    float T = texture2D(uVelocity, vUv + vec2(0.0, texelSize.y)).x;
    
    float vorticity = R - L - T + B;
    
    gl_FragColor = vec4(0.5 * vorticity, 0.0, 0.0, 1.0);
}
