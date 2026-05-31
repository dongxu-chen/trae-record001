uniform sampler2D uTarget;
uniform vec2 uPosition;
uniform vec2 uDirection;
uniform float uRate;
uniform vec3 uColor;
uniform float uTime;
uniform vec2 uResolution;

varying vec2 vUv;

float random(vec2 st) {
    return fract(sin(dot(st.xy, vec2(12.9898, 78.233))) * 43758.5453123);
}

void main() {
    vec4 base = texture2D(uTarget, vUv);
    
    vec2 pos = uPosition / uResolution;
    float dist = distance(vUv, pos);
    
    float spawnRadius = 0.02;
    float spawnChance = uRate * 0.1;
    
    float rand = random(vUv * 100.0 + fract(uTime) * 10.0);
    
    if (dist < spawnRadius && rand < spawnChance) {
        float speed = 2.0 + random(vUv + uTime) * 2.0;
        vec2 velocity = uDirection * speed;
        
        vec3 jitterColor = uColor;
        jitterColor += vec3(random(vUv.yx) * 0.2 - 0.1);
        
        base.rgb = mix(base.rgb, jitterColor, 0.5);
        base.xy = mix(base.xy, velocity, 0.3);
        base.a += 0.8;
    }
    
    gl_FragColor = base;
}
