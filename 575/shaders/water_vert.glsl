#version 330 core

layout(location = 0) in vec3 position;
layout(location = 1) in vec3 normal;
layout(location = 2) in vec2 texCoord;
layout(location = 3) in float foam;

out vec3 fragNormal;
out vec3 fragPos;
out vec2 fragTexCoord;
out float fragFoam;
out vec3 viewDir;
out vec4 screenPos;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;
uniform vec3 cameraPos;

void main() {
    vec4 worldPos = model * vec4(position, 1.0);
    fragPos = worldPos.xyz;
    fragNormal = mat3(transpose(inverse(model))) * normal;
    fragTexCoord = texCoord;
    fragFoam = foam;
    
    viewDir = normalize(cameraPos - fragPos);
    
    vec4 clipPos = projection * view * worldPos;
    screenPos = clipPos;
    
    gl_Position = clipPos;
}
