#include "collision.h"

CollisionSystem::CollisionSystem() {
    ground.type = FLAT_GROUND;
    ground.flatY = 0.0f;
    ground.sphereRadius = 5.0f;
    ground.sphereCenter = glm::vec3(0.0f, 2.5f, 0.0f);
    ground.boxMin = glm::vec3(-3.0f, 0.0f, -3.0f);
    ground.boxMax = glm::vec3(3.0f, 2.0f, 3.0f);
    ground.heightScale = 1.0f;
    ground.heightFrequency = 0.3f;
}

float CollisionSystem::heightNoise(float x, float z) {
    float value = 0.0f;
    value += sin(x * ground.heightFrequency) * cos(z * ground.heightFrequency);
    value += sin(x * ground.heightFrequency * 2.1f + 1.0f) * 0.5f;
    value += cos(z * ground.heightFrequency * 1.8f + 2.0f) * 0.5f;
    return value * ground.heightScale;
}

float CollisionSystem::getGroundHeight(float x, float z) {
    switch (ground.type) {
        case FLAT_GROUND:
            return ground.flatY;
        case HEIGHT_MAP:
            return heightNoise(x, z);
        case SPHERE: {
            float dx = x - ground.sphereCenter.x;
            float dz = z - ground.sphereCenter.z;
            float dist = sqrt(dx * dx + dz * dz);
            if (dist < ground.sphereRadius) {
                float h = sqrt(ground.sphereRadius * ground.sphereRadius - dist * dist);
                return ground.sphereCenter.y + h;
            }
            return 0.0f;
        }
        case BOX:
            if (x >= ground.boxMin.x && x <= ground.boxMax.x &&
                z >= ground.boxMin.z && z <= ground.boxMax.z) {
                return ground.boxMax.y;
            }
            return 0.0f;
        default:
            return 0.0f;
    }
}

glm::vec3 CollisionSystem::getGroundNormal(const glm::vec3& position) {
    switch (ground.type) {
        case FLAT_GROUND:
            return glm::vec3(0.0f, 1.0f, 0.0f);
        case HEIGHT_MAP: {
            float eps = 0.01f;
            float h00 = heightNoise(position.x, position.z);
            float h10 = heightNoise(position.x + eps, position.z);
            float h01 = heightNoise(position.x, position.z + eps);
            glm::vec3 vx = glm::vec3(eps, h10 - h00, 0.0f);
            glm::vec3 vz = glm::vec3(0.0f, h01 - h00, eps);
            return glm::normalize(glm::cross(vz, vx));
        }
        case SPHERE: {
            glm::vec3 dir = position - ground.sphereCenter;
            return glm::normalize(dir);
        }
        case BOX: {
            return glm::vec3(0.0f, 1.0f, 0.0f);
        }
        default:
            return glm::vec3(0.0f, 1.0f, 0.0f);
    }
}

CollisionResult CollisionSystem::checkFlatGround(const glm::vec3& pos, float radius) {
    CollisionResult result;
    result.hasCollided = false;
    
    float groundY = ground.flatY;
    float diff = pos.y - radius - groundY;
    
    if (diff < 0.0f) {
        result.hasCollided = true;
        result.contactPoint = glm::vec3(pos.x, groundY, pos.z);
        result.normal = glm::vec3(0.0f, 1.0f, 0.0f);
        result.penetrationDepth = -diff;
    }
    
    return result;
}

CollisionResult CollisionSystem::checkHeightMap(const glm::vec3& pos, float radius) {
    CollisionResult result;
    result.hasCollided = false;
    
    float groundY = heightNoise(pos.x, pos.z);
    float diff = pos.y - radius - groundY;
    
    if (diff < 0.0f) {
        result.hasCollided = true;
        result.contactPoint = glm::vec3(pos.x, groundY, pos.z);
        result.normal = getGroundNormal(pos);
        result.penetrationDepth = -diff;
    }
    
    return result;
}

CollisionResult CollisionSystem::checkSphere(const glm::vec3& pos, float radius) {
    CollisionResult result;
    result.hasCollided = false;
    
    glm::vec3 toCenter = pos - ground.sphereCenter;
    float dist = glm::length(toCenter);
    float minDist = ground.sphereRadius + radius;
    
    if (dist < minDist) {
        result.hasCollided = true;
        result.normal = dist > 0.001f ? glm::normalize(toCenter) : glm::vec3(0.0f, 1.0f, 0.0f);
        result.contactPoint = ground.sphereCenter + result.normal * ground.sphereRadius;
        result.penetrationDepth = minDist - dist;
    }
    
    return result;
}

CollisionResult CollisionSystem::checkBox(const glm::vec3& pos, float radius) {
    CollisionResult result;
    result.hasCollided = false;
    
    glm::vec3 clampedPos(
        glm::clamp(pos.x, ground.boxMin.x, ground.boxMax.x),
        glm::clamp(pos.y, ground.boxMin.y, ground.boxMax.y),
        glm::clamp(pos.z, ground.boxMin.z, ground.boxMax.z)
    );
    
    glm::vec3 diff = pos - clampedPos;
    float dist = glm::length(diff);
    
    if (dist < radius) {
        result.hasCollided = true;
        result.contactPoint = clampedPos;
        result.normal = dist > 0.001f ? glm::normalize(diff) : glm::vec3(0.0f, 1.0f, 0.0f);
        result.penetrationDepth = radius - dist;
    }
    
    return result;
}

CollisionResult CollisionSystem::checkGroundCollision(const glm::vec3& position, float radius) {
    CollisionResult groundCollision;
    
    switch (ground.type) {
        case FLAT_GROUND:
            groundCollision = checkFlatGround(position, radius);
            break;
        case HEIGHT_MAP:
            groundCollision = checkHeightMap(position, radius);
            break;
        case SPHERE:
            groundCollision = checkSphere(position, radius);
            break;
        case BOX:
            groundCollision = checkBox(position, radius);
            break;
        default:
            groundCollision = checkFlatGround(position, radius);
            break;
    }
    
    return groundCollision;
}

void CollisionSystem::resolveCollision(glm::vec3& position, glm::vec3& velocity, 
                                       const CollisionResult& result, float restitution, float friction) {
    if (!result.hasCollided) return;
    
    position += result.normal * result.penetrationDepth;
    
    float vn = glm::dot(velocity, result.normal);
    if (vn < 0.0f) {
        glm::vec3 velNormal = vn * result.normal;
        glm::vec3 velTangent = velocity - velNormal;
        
        velocity = -restitution * velNormal + (1.0f - friction) * velTangent;
    }
}

void CollisionSystem::setGroundType(GroundType type) {
    ground.type = type;
}

void CollisionSystem::setFlatGroundY(float y) {
    ground.flatY = y;
}

void CollisionSystem::setSphere(const glm::vec3& center, float radius) {
    ground.sphereCenter = center;
    ground.sphereRadius = radius;
}

void CollisionSystem::setBox(const glm::vec3& min, const glm::vec3& max) {
    ground.boxMin = min;
    ground.boxMax = max;
}

void CollisionSystem::setHeightMapParams(float scale, float freq) {
    ground.heightScale = scale;
    ground.heightFrequency = freq;
}
