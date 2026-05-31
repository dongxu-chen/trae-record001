uniform sampler2D uVelocity;
uniform sampler2D uSource;
uniform vec2 uResolution;
uniform float uTimeStep;
uniform float uDissipation;

varying vec2 vUv;

void main() {
    vec2 texelSize = 1.0 / uResolution;
    vec2 velocity = texture2D(uVelocity, vUv).xy;
    
    vec2 pastCoord = vUv - velocity * uTimeStep * texelSize;
    
    vec4 result = texture2D(uSource, pastCoord) * uDissipation;
    
    gl_FragColor = result;
}
