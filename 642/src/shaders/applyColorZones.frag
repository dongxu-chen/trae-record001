uniform sampler2D uDensity;
uniform sampler2D uVelocity;
uniform vec2 uZonePositions[8];
uniform vec3 uZoneColors[8];
uniform float uZoneRadii[8];
uniform int uZoneCount;
uniform vec2 uResolution;
uniform float uBlendFactor;

varying vec2 vUv;

void main() {
    vec4 density = texture2D(uDensity, vUv);
    vec4 result = density;
    
    vec2 uv = vUv;
    
    vec3 blendedColor = vec3(0.0);
    float totalWeight = 0.0;
    
    for (int i = 0; i < 8; i++) {
        if (i >= uZoneCount) break;
        
        vec2 zonePos = uZonePositions[i] / uResolution;
        float dist = distance(uv, zonePos);
        float radius = uZoneRadii[i] / uResolution.x;
        
        float weight = exp(-dist * dist / (radius * radius) * 4.0);
        weight = smoothstep(0.0, 1.0, weight);
        
        blendedColor += uZoneColors[i] * weight;
        totalWeight += weight;
    }
    
    if (totalWeight > 0.0) {
        blendedColor /= totalWeight;
        float blendAmount = min(totalWeight * uBlendFactor, 1.0);
        result.rgb = mix(density.rgb, blendedColor, blendAmount);
    }
    
    gl_FragColor = result;
}
