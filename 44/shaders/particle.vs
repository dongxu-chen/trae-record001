#version 330 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in float aSize;

uniform mat4 projection;
uniform mat4 view;
uniform vec3 cameraPos;

out vec3 fragPos;

void main()
{
    fragPos = aPos;
    gl_Position = projection * view * vec4(aPos, 1.0);
    float dist = length(aPos - cameraPos);
    gl_PointSize = aSize * 50.0 / dist;
}
