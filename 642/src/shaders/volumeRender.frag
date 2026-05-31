uniform sampler2D uFluidData;
uniform vec3 uColor;
uniform float uTransparency;
uniform vec3 uLightPos;
uniform vec2 uResolution;
uniform float uTime;

varying vec2 vUv;

float noise(vec2 p) {
    return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void main() {
    vec4 fluid = texture2D(uFluidData, vUv);
    
    float density = length(fluid.rgb) * 0.333;
    density += fluid.a * 0.5;
    
    float n = noise(vUv * 100.0 + uTime * 0.1);
    density += n * 0.1;
    
    vec3 baseColor = uColor;
    float hueShift = sin(uTime * 0.2 + vUv.x * 3.14159) * 0.05;
    baseColor = hsv2rgb(vec3(0.55 + hueShift, 0.8, 1.0));
    
    float lightDist = distance(vUv, uLightPos.xy * 0.5 + 0.5);
    float lightAtten = 1.0 / (1.0 + lightDist * 2.0);
    vec3 finalColor = baseColor * (1.0 + lightAtten * 0.5);
    
    float alpha = density * uTransparency;
    alpha = smoothstep(0.0, 0.5, alpha);
    
    vec3 glow = baseColor * density * 0.5;
    finalColor += glow;
    
    gl_FragColor = vec4(finalColor, alpha);
}
