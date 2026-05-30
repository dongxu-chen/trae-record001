export const vertexShaderSource = `#version 300 es
in vec2 aPosition;
in vec2 aTexCoord;
out vec2 vTexCoord;
void main() {
  vTexCoord = aTexCoord;
  gl_Position = vec4(aPosition, 0.0, 1.0);
}
`;

export const dreamyFragmentSource = `#version 300 es
precision highp float;
in vec2 vTexCoord;
out vec4 fragColor;
uniform sampler2D uTexture;
uniform vec2 uResolution;
uniform float uIntensity;
uniform float uBlurRadius;
uniform vec3 uGlowColor;

vec4 blur9(vec2 uv, vec2 resolution, vec2 direction) {
  vec4 color = vec4(0.0);
  vec2 off1 = vec2(1.3846153846) * direction;
  vec2 off2 = vec2(3.2307692308) * direction;
  color += texture(uTexture, uv) * 0.2270270270;
  color += texture(uTexture, uv + (off1 / resolution)) * 0.3162162162;
  color += texture(uTexture, uv - (off1 / resolution)) * 0.3162162162;
  color += texture(uTexture, uv + (off2 / resolution)) * 0.0702702703;
  color += texture(uTexture, uv - (off2 / resolution)) * 0.0702702703;
  return color;
}

void main() {
  vec2 uv = vTexCoord;
  vec4 original = texture(uTexture, uv);
  
  vec2 dirH = vec2(uBlurRadius * 8.0, 0.0);
  vec2 dirV = vec2(0.0, uBlurRadius * 8.0);
  vec4 blurH = blur9(uv, uResolution, dirH);
  vec4 blurV = blur9(uv, uResolution, dirV);
  vec4 blurred = (blurH + blurV) * 0.5;
  
  vec3 colorShift = vec3(
    texture(uTexture, uv + vec2(0.005, 0.0)).r,
    texture(uTexture, uv).g,
    texture(uTexture, uv - vec2(0.005, 0.0)).b
  );
  
  float dist = length(uv - 0.5);
  float vignette = smoothstep(0.6, 0.1, dist);
  
  vec3 glow = uGlowColor * (1.0 - dist) * vignette * 0.3;
  
  vec3 result = mix(original.rgb, colorShift, uIntensity * 0.3);
  result = mix(result, blurred.rgb, uIntensity * 0.5);
  result += glow * uIntensity;
  result = mix(original.rgb, result, uIntensity);
  
  fragColor = vec4(result, original.a);
}
`;

export const backlightFragmentSource = `#version 300 es
precision highp float;
in vec2 vTexCoord;
out vec4 fragColor;
uniform sampler2D uTexture;
uniform vec2 uResolution;
uniform float uIntensity;
uniform vec2 uLightPos;
uniform float uFlareSize;

void main() {
  vec2 uv = vTexCoord;
  vec4 original = texture(uTexture, uv);
  
  vec2 lightCenter = uLightPos;
  float dist = distance(uv, lightCenter);
  
  float radialGrad = exp(-dist * uFlareSize * 3.0);
  
  float rays = 0.0;
  float angle = atan(uv.y - lightCenter.y, uv.x - lightCenter.x);
  for (float i = 0.0; i < 8.0; i++) {
    float rayAngle = (i * 3.14159 / 4.0);
    float rayWidth = abs(sin(angle - rayAngle));
    rayWidth = pow(rayWidth, 20.0);
    rays += rayWidth * exp(-dist * uFlareSize * 1.5);
  }
  rays /= 8.0;
  
  vec3 flareColor = vec3(1.0, 0.8, 0.4) * radialGrad * 0.5;
  flareColor += vec3(1.0, 0.9, 0.6) * rays * 0.3;
  
  vec2 ghostPos = lightCenter + (uv - lightCenter) * 0.5;
  float ghostDist = distance(uv, ghostPos);
  float ghost = exp(-ghostDist * uFlareSize * 5.0) * 0.2;
  flareColor += vec3(0.8, 0.9, 1.0) * ghost;
  
  float contrast = 1.0 + uIntensity * 0.3;
  vec3 contrasted = (original.rgb - 0.5) * contrast + 0.5;
  
  vec3 result = mix(original.rgb, contrasted, uIntensity * 0.3);
  result += flareColor * uIntensity;
  result = mix(original.rgb, result, uIntensity);
  
  fragColor = vec4(result, original.a);
}
`;

export const neonFragmentSource = `#version 300 es
precision highp float;
in vec2 vTexCoord;
out vec4 fragColor;
uniform sampler2D uTexture;
uniform vec2 uResolution;
uniform float uIntensity;
uniform float uGlowWidth;
uniform vec3 uNeonColor;

float luminance(vec3 color) {
  return dot(color, vec3(0.299, 0.587, 0.114));
}

float sobel(vec2 uv, vec2 texel) {
  float tl = luminance(texture(uTexture, uv - texel).rgb);
  float tr = luminance(texture(uTexture, uv + vec2(texel.x, -texel.y)).rgb);
  float bl = luminance(texture(uTexture, uv + vec2(-texel.x, texel.y)).rgb);
  float br = luminance(texture(uTexture, uv + texel).rgb);
  float t = luminance(texture(uTexture, uv - vec2(0.0, texel.y)).rgb);
  float b = luminance(texture(uTexture, uv + vec2(0.0, texel.y)).rgb);
  float l = luminance(texture(uTexture, uv - vec2(texel.x, 0.0)).rgb);
  float r = luminance(texture(uTexture, uv + vec2(texel.x, 0.0)).rgb);
  
  float gx = (-tl + tr - 2.0 * l + 2.0 * r - bl + br) / 4.0;
  float gy = (-tl - 2.0 * t - tr + bl + 2.0 * b + br) / 4.0;
  
  return sqrt(gx * gx + gy * gy);
}

void main() {
  vec2 uv = vTexCoord;
  vec4 original = texture(uTexture, uv);
  
  vec2 texel = uGlowWidth / uResolution;
  
  float edge = sobel(uv, texel);
  edge = smoothstep(0.05, 0.5, edge);
  
  vec3 glow = uNeonColor * edge;
  
  for (float i = 1.0; i <= 4.0; i++) {
    float e1 = sobel(uv + vec2(texel.x * i, 0.0), texel);
    float e2 = sobel(uv - vec2(texel.x * i, 0.0), texel);
    float e3 = sobel(uv + vec2(0.0, texel.y * i), texel);
    float e4 = sobel(uv - vec2(0.0, texel.y * i), texel);
    glow += uNeonColor * (e1 + e2 + e3 + e4) * (0.25 / i);
  }
  
  float saturation = 1.0 + uIntensity * 0.5;
  float gray = luminance(original.rgb);
  vec3 saturated = vec3(gray) + (original.rgb - vec3(gray)) * saturation;
  
  vec3 result = mix(original.rgb, saturated, uIntensity * 0.4);
  result += glow * uIntensity * 1.5;
  result = mix(original.rgb, result, uIntensity);
  
  fragColor = vec4(result, original.a);
}
`;

export const starburstFragmentSource = `#version 300 es
precision highp float;
in vec2 vTexCoord;
out vec4 fragColor;
uniform sampler2D uTexture;
uniform vec2 uResolution;
uniform float uIntensity;
uniform float uRayCount;
uniform float uRayLength;
uniform vec2 uBrightCenter;
uniform float uBrightAngle;

float luminance(vec3 color) {
  return dot(color, vec3(0.299, 0.587, 0.114));
}

void main() {
  vec2 uv = vTexCoord;
  vec4 original = texture(uTexture, uv);
  
  vec2 center = uBrightCenter;
  vec2 toCenter = center - uv;
  float dist = length(toCenter);
  float baseAngle = atan(toCenter.y, toCenter.x);
  float angle = baseAngle - uBrightAngle * 0.3;
  
  float rays = 0.0;
  float rayAngle = 6.28318 / uRayCount;
  
  for (float i = 0.0; i < 64.0; i++) {
    if (i >= uRayCount) break;
    float ray = abs(mod(angle + rayAngle * i, rayAngle) - rayAngle * 0.5);
    ray = smoothstep(rayAngle * 0.3, 0.0, ray);
    ray *= exp(-dist * (3.0 / uRayLength));
    rays += ray;
  }
  rays /= uRayCount;
  
  float crossRays = 0.0;
  float crossAngle = 3.14159 / 2.0;
  for (float i = 0.0; i < 4.0; i++) {
    float adjustedCrossAngle = crossAngle + uBrightAngle * 0.2;
    float ray = abs(mod(angle + adjustedCrossAngle * i, crossAngle) - crossAngle * 0.5);
    ray = smoothstep(crossAngle * 0.2, 0.0, ray);
    ray *= exp(-dist * (2.0 / uRayLength));
    crossRays += ray;
  }
  crossRays *= 0.5;
  
  float directionalRays = 0.0;
  float dirRayWidth = 0.1;
  for (float i = -2.0; i <= 2.0; i++) {
    float testAngle = uBrightAngle + i * 0.15;
    float dirRay = abs(sin(baseAngle - testAngle));
    dirRay = pow(1.0 - dirRay, 50.0);
    dirRay *= exp(-dist * (1.5 / uRayLength));
    directionalRays += dirRay;
  }
  directionalRays *= 0.3;
  
  float brightness = luminance(original.rgb);
  vec3 rayColor = original.rgb * (1.0 + rays * 2.0 + crossRays + directionalRays);
  
  float sparkle = pow(brightness, 8.0) * (rays + crossRays + directionalRays) * 0.5;
  
  vec3 result = mix(original.rgb, rayColor, uIntensity * 0.5);
  result += vec3(sparkle) * uIntensity;
  result = mix(original.rgb, result, uIntensity);
  
  fragColor = vec4(result, original.a);
}
`;

export const customFragmentTemplate = `#version 300 es
precision highp float;
in vec2 vTexCoord;
out vec4 fragColor;
uniform sampler2D uTexture;
uniform vec2 uResolution;
uniform float uIntensity;

void main() {
  vec4 color = texture(uTexture, vTexCoord);
  fragColor = color;
}
`;
