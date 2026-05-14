#ifndef COLLISION_H
#define COLLISION_H

#include <glm/glm.hpp>
#include <vector>
#include <cmath>

enum GroundType {
    FLAT_GROUND,
    HEIGHT_MAP,
    SPHERE,
    BOX
};

struct CollisionResult {
    bool hasCollided;
    glm::vec3 contactPoint;
    glm::vec3 normal;
    float penetrationDepth;
};

struct GroundParams {
    GroundType type;
    float flatY;
    float sphereRadius;
    glm::vec3 sphereCenter;
    glm::vec3 boxMin;
    glm::vec3 boxMax;
    float heightScale;
    float heightFrequency;
};

class CollisionSystem {
public:
    CollisionSystem();
    
    CollisionResult checkGroundCollision(const glm::vec3& position, float radius);
    void resolveCollision(glm::vec3& position, glm::vec3& velocity, const CollisionResult& result, float restitution, float friction);
    
    void setGroundType(GroundType type);
    void setFlatGroundY(float y);
    void setSphere(const glm::vec3& center, float radius);
    void setBox(const glm::vec3& min, const glm::vec3& max);
    void setHeightMapParams(float scale, float freq);
    
    glm::vec3 getGroundNormal(const glm::vec3& position);
    float getGroundHeight(float x, float z);
    
private:
    GroundParams ground;
    
    CollisionResult checkFlatGround(const glm::vec3& pos, float radius);
    CollisionResult checkSphere(const glm::vec3& pos, float radius);
    CollisionResult checkBox(const glm::vec3& pos, float radius);
    CollisionResult checkHeightMap(const glm::vec3& pos, float radius);
    
    float heightNoise(float x, float z);
};

#endif
