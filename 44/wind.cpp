#include "wind.h"

WindField::WindField() 
    : baseDirection(glm::vec3(1.0f, 0.0f, 0.0f)), 
      strength(5.0f), 
      turbulence(0.5f) {}

WindField::WindField(const glm::vec3& baseDirection, float strength, float turbulence)
    : baseDirection(glm::normalize(baseDirection)), 
      strength(strength), 
      turbulence(turbulence) {}

glm::vec3 WindField::getWindVelocity(const glm::vec3& position, float time) const {
    glm::vec3 baseWind = baseDirection * strength;
    
    float freq = 2.0f;
    float amp = turbulence * strength;
    
    float nx = noise(position.x * freq, position.y * freq, position.z * freq, time * 0.5f);
    float ny = noise(position.x * freq + 100.0f, position.y * freq + 100.0f, position.z * freq + 100.0f, time * 0.5f);
    float nz = noise(position.x * freq + 200.0f, position.y * freq + 200.0f, position.z * freq + 200.0f, time * 0.5f);
    
    glm::vec3 turbulenceWind = glm::vec3(nx, ny, nz) * amp;
    
    return baseWind + turbulenceWind;
}

void WindField::setBaseDirection(const glm::vec3& direction) {
    baseDirection = glm::normalize(direction);
}

void WindField::setStrength(float strength) {
    this->strength = strength;
}

void WindField::setTurbulence(float turbulence) {
    this->turbulence = turbulence;
}

float WindField::noise(float x, float y, float z, float time) const {
    float value = 0.0f;
    
    value += sin(x + time);
    value += sin(y * 0.5f + time * 0.7f);
    value += sin(z * 0.3f + time * 0.4f);
    value += sin((x + y) * 0.8f + time * 0.6f);
    value += sin((x - z) * 1.2f + time * 0.9f);
    
    return value / 5.0f;
}
