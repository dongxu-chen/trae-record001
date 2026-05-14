#version 330 core
out vec4 FragColor;

in vec3 fragPos;

uniform vec3 particleColor;

void main()
{
    vec2 coord = gl_PointCoord - vec2(0.5);
    float dist = length(coord);
    if (dist > 0.5)
        discard;
    
    float alpha = 1.0 - smoothstep(0.3, 0.5, dist);
    FragColor = vec4(particleColor, alpha);
}
