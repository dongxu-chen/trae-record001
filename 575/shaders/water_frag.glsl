#version 330 core

in vec3 fragNormal;
in vec3 fragPos;
in vec2 fragTexCoord;
in float fragFoam;
in vec3 viewDir;
in vec4 screenPos;

out vec4 finalColor;

uniform vec3 lightDir;
uniform vec3 lightColor;
uniform vec3 waterColor;
uniform float specularStrength;
uniform float shininess;
uniform float reflectivity;
uniform float time;
uniform float foamIntensity;
uniform vec2 screenSize;
uniform int underwater;

const float PI = 3.14159265359;

float DistributionGGX(vec3 N, vec3 H, float roughness) {
    float a = roughness * roughness;
    float a2 = a * a;
    float NdotH = max(dot(N, H), 0.0);
    float NdotH2 = NdotH * NdotH;
    
    float nom = a2;
    float denom = (NdotH2 * (a2 - 1.0) + 1.0);
    denom = PI * denom * denom;
    
    return nom / denom;
}

float GeometrySchlickGGX(float NdotV, float roughness) {
    float r = (roughness + 1.0);
    float k = (r * r) / 8.0;
    
    float nom = NdotV;
    float denom = NdotV * (1.0 - k) + k;
    
    return nom / denom;
}

float GeometrySmith(vec3 N, vec3 V, vec3 L, float roughness) {
    float NdotV = max(dot(N, V), 0.0);
    float NdotL = max(dot(N, L), 0.0);
    float ggx2 = GeometrySchlickGGX(NdotV, roughness);
    float ggx1 = GeometrySchlickGGX(NdotL, roughness);
    
    return ggx1 * ggx2;
}

vec3 fresnelSchlick(float cosTheta, vec3 F0) {
    return F0 + (1.0 - F0) * pow(clamp(1.0 - cosTheta, 0.0, 1.0), 5.0);
}

vec3 getSkyColor(vec3 dir) {
    float t = max(dir.y, 0.0);
    vec3 horizon = vec3(0.6, 0.75, 0.85);
    vec3 zenith = vec3(0.3, 0.5, 0.8);
    vec3 sky = mix(horizon, zenith, pow(t, 0.5));
    
    vec3 sunDir = normalize(-lightDir);
    float sunDot = max(dot(dir, sunDir), 0.0);
    vec3 sunColor = vec3(1.0, 0.95, 0.8) * pow(sunDot, 256.0) * 2.0;
    sunColor += vec3(1.0, 0.9, 0.7) * pow(sunDot, 32.0) * 0.5;
    
    return sky + sunColor;
}

float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    
    return mix(
        mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x),
        mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x),
        f.y
    );
}

float fbm(vec2 p) {
    float value = 0.0;
    float amplitude = 0.5;
    for(int i = 0; i < 5; i++) {
        value += amplitude * noise(p);
        p *= 2.0;
        amplitude *= 0.5;
    }
    return value;
}

vec3 underwaterFog(vec3 color, vec3 viewDir) {
    float depth = max(-fragPos.y, 0.1);
    
    float fogDensity = 0.03;
    float fogFactor = 1.0 - exp(-depth * fogDensity);
    
    vec3 fogColorDeep = vec3(0.0, 0.08, 0.15);
    vec3 fogColorShallow = vec3(0.0, 0.2, 0.3);
    vec3 fogColor = mix(fogColorShallow, fogColorDeep, min(depth * 0.05, 1.0));
    
    vec3 scatterLight = vec3(0.0, 0.3, 0.4) * max(dot(viewDir, -lightDir), 0.0) * 0.3;
    fogColor += scatterLight;
    
    float causticSpeed = time * 0.5;
    vec2 causticUV = fragPos.xz * 0.1 + vec2(causticSpeed, causticSpeed * 0.7);
    float caustic = fbm(causticUV) * fbm(causticUV * 1.5 + vec2(3.7, 1.2));
    caustic = pow(caustic, 2.0) * 1.5;
    
    vec3 causticColor = vec3(0.1, 0.4, 0.5) * caustic * max(-lightDir.y, 0.0);
    
    color = mix(color, fogColor, fogFactor);
    color += causticColor * (1.0 - fogFactor) * 0.5;
    
    return color;
}

void main() {
    vec3 N = normalize(fragNormal);
    vec3 V = normalize(viewDir);
    vec3 L = normalize(-lightDir);
    vec3 H = normalize(V + L);
    
    if (underwater == 1) {
        float roughness_uw = 0.05;
        vec3 deepColor = vec3(0.0, 0.05, 0.12);
        vec3 shallowColor = vec3(0.0, 0.15, 0.25);
        
        float depthFactor = exp(-abs(fragPos.y) * 0.05);
        vec3 baseWater = mix(deepColor, shallowColor, depthFactor);
        
        float NdotL = max(dot(N, L), 0.0);
        vec3 diffuse = baseWater * NdotL * lightColor * 0.5;
        
        float spec_uw = pow(max(dot(N, H), 0.0), 256.0);
        vec3 specular = spec_uw * lightColor * 0.3;
        
        vec3 result = diffuse + specular;
        result = underwaterFog(result, V);
        
        result = result / (result + vec3(1.0));
        result = pow(result, vec3(1.0 / 2.2));
        
        finalColor = vec4(result, 1.0);
        return;
    }
    
    float roughness = 0.15;
    float metallic = 0.0;
    
    vec3 F0 = vec3(0.02);
    F0 = mix(F0, vec3(0.04), metallic);
    
    float NdotL = max(dot(N, L), 0.0);
    float NdotV = max(dot(N, V), 0.0);
    
    float NDF = DistributionGGX(N, H, roughness);
    float G = GeometrySmith(N, V, L, roughness);
    vec3 F = fresnelSchlick(max(dot(H, V), 0.0), F0);
    
    vec3 numerator = NDF * G * F;
    float denominator = 4.0 * NdotV * NdotL + 0.0001;
    vec3 specular = numerator / denominator;
    
    vec3 kS = F;
    vec3 kD = vec3(1.0) - kS;
    kD *= 1.0 - metallic;
    
    vec3 R = reflect(-V, N);
    vec3 reflectedSky = getSkyColor(R);
    
    float fresnelFactor = pow(1.0 - NdotV, 4.0);
    fresnelFactor = mix(0.02, 1.0, fresnelFactor);
    
    vec3 deepColor = vec3(0.0, 0.15, 0.25);
    vec3 shallowColor = vec3(0.0, 0.35, 0.45);
    float depthFactor = exp(-abs(fragPos.y) * 0.1);
    vec3 baseWater = mix(deepColor, shallowColor, depthFactor);
    
    vec3 finalSpecular = specular * specularStrength * lightColor * NdotL;
    
    vec3 refractedColor = baseWater * (0.3 + 0.7 * NdotL);
    vec3 finalReflection = mix(refractedColor, reflectedSky, fresnelFactor * reflectivity);
    
    vec3 final = finalReflection + finalSpecular;
    
    vec2 foamOffset = fragTexCoord * 8.0 + vec2(time * 0.1, time * 0.05);
    float foamNoise = fbm(foamOffset);
    float foamAmount = smoothstep(0.3, 0.8, fragFoam) * foamNoise;
    
    vec2 foamVelocity = vec2(
        noise(fragTexCoord * 4.0 + time * 0.1),
        noise(fragTexCoord * 4.0 + time * 0.1 + 100.0)
    ) * 0.01;
    vec2 advectedUV = fragTexCoord + foamVelocity;
    float advectedFoam = fbm(advectedUV * 6.0) * smoothstep(0.2, 0.7, fragFoam);
    
    foamAmount = max(foamAmount, advectedFoam * 0.6);
    
    vec3 foamColor = vec3(1.0, 1.0, 1.0) * foamIntensity;
    float foamAlpha = smoothstep(0.2, 0.9, foamAmount);
    
    vec3 foamHighlight = foamColor * (0.7 + 0.3 * dot(N, L));
    final = mix(final, foamHighlight, foamAlpha * 0.8);
    
    final = final / (final + vec3(1.0));
    
    float gamma = 2.2;
    final = pow(final, vec3(1.0 / gamma));
    
    finalColor = vec4(final, 0.98);
}
