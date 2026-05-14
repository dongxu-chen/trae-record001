#ifndef WIND_H
#define WIND_H

#include <glm/glm.hpp>
#include <cmath>

class WindField {
public:
    WindField();
    WindField(const glm::vec3& baseDirection, float strength, float turbulence);

    glm::vec3 getWindVelocity(const glm::vec3& position, float time) const;

    void setBaseDirection(const glm::vec3& direction);
    void setStrength(float strength);
    void setTurbulence(float turbulence);

private:
    glm::vec3 baseDirection;
    float strength;
    float turbulence;

    float noise(float x, float y, float z, float time) const;
};

#endif
