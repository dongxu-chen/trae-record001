#include "particle.h"
#include <iostream>
#include <glm/gtc/constants.hpp>

ParticleParams ParticleSystem::getDefaultParams(ParticleType type, Season season) {
    ParticleParams p;
    p.gravityScale = 1.0f;
    
    switch (type) {
        case SNOW:
            p.massMin = 0.000001f;
            p.massMax = 0.00001f;
            p.sizeMin = 0.03f;
            p.sizeMax = 0.08f;
            p.lifetimeMin = 15.0f;
            p.lifetimeMax = 30.0f;
            p.initialVelY = 0.0f;
            p.terminalVelocity = 1.5f;
            p.restitution = 0.0f;
            p.friction = 1.0f;
            p.swirlEffect = true;
            p.dieOnGround = false;
            p.color = glm::vec3(0.95f, 0.98f, 1.0f);
            break;
        case RAIN:
            p.massMin = 0.0002f;
            p.massMax = 0.001f;
            p.sizeMin = 0.02f;
            p.sizeMax = 0.05f;
            p.lifetimeMin = 3.0f;
            p.lifetimeMax = 8.0f;
            p.initialVelY = -5.0f;
            p.terminalVelocity = 9.0f;
            p.restitution = 0.0f;
            p.friction = 1.0f;
            p.swirlEffect = false;
            p.dieOnGround = true;
            p.color = glm::vec3(0.6f, 0.8f, 0.95f);
            break;
        case LEAF:
            p.massMin = 0.00005f;
            p.massMax = 0.0002f;
            p.sizeMin = 0.08f;
            p.sizeMax = 0.15f;
            p.lifetimeMin = 20.0f;
            p.lifetimeMax = 40.0f;
            p.initialVelY = 0.0f;
            p.terminalVelocity = 2.0f;
            p.restitution = 0.2f;
            p.friction = 0.8f;
            p.swirlEffect = true;
            p.dieOnGround = false;
            p.color = glm::vec3(0.8f, 0.5f, 0.2f);
            break;
        case HAIL:
            p.massMin = 0.001f;
            p.massMax = 0.005f;
            p.sizeMin = 0.04f;
            p.sizeMax = 0.12f;
            p.lifetimeMin = 2.0f;
            p.lifetimeMax = 5.0f;
            p.initialVelY = -10.0f;
            p.terminalVelocity = 15.0f;
            p.restitution = 0.6f;
            p.friction = 0.3f;
            p.swirlEffect = false;
            p.dieOnGround = false;
            p.color = glm::vec3(0.85f, 0.9f, 1.0f);
            break;
        case DUST:
            p.massMin = 0.0000001f;
            p.massMax = 0.000001f;
            p.sizeMin = 0.01f;
            p.sizeMax = 0.03f;
            p.lifetimeMin = 30.0f;
            p.lifetimeMax = 60.0f;
            p.initialVelY = 0.0f;
            p.terminalVelocity = 0.5f;
            p.restitution = 0.0f;
            p.friction = 0.9f;
            p.swirlEffect = true;
            p.dieOnGround = true;
            p.color = glm::vec3(0.7f, 0.65f, 0.55f);
            break;
        default:
            p.massMin = 0.00001f;
            p.massMax = 0.0001f;
            p.sizeMin = 0.03f;
            p.sizeMax = 0.08f;
            p.lifetimeMin = 10.0f;
            p.lifetimeMax = 20.0f;
            p.initialVelY = 0.0f;
            p.terminalVelocity = 3.0f;
            p.restitution = 0.0f;
            p.friction = 0.5f;
            p.swirlEffect = false;
            p.dieOnGround = true;
            p.color = glm::vec3(1.0f, 1.0f, 1.0f);
            break;
    }
    
    if (season == WINTER && type == LEAF) {
        p.lifetimeMin = 5.0f;
        p.lifetimeMax = 10.0f;
    }
    
    return p;
}

ParticleParams ParticleSystem::getSeasonalParams(Season season) {
    ParticleParams p;
    switch (season) {
        case WINTER:
            p.gravityScale = 0.8f;
            break;
        case SPRING:
            p.gravityScale = 1.0f;
            break;
        case SUMMER:
            p.gravityScale = 1.1f;
            break;
        case AUTUMN:
            p.gravityScale = 0.9f;
            break;
    }
    return p;
}

ParticleSystem::ParticleSystem(ParticleType type, unsigned int maxParticles, const glm::vec3& spawnArea)
    : particleType(type), maxParticles(maxParticles), spawnArea(spawnArea),
      spawnRate(100.0f), spawnTimer(0.0f), activeCount(0),
      currentSeason(WINTER),
      gravity(glm::vec3(0.0f, -9.8f, 0.0f)),
      collisionEnabled(true),
      rng(std::random_device{}()), distPos(-1.0f, 1.0f),
      distSize(0.5f, 1.5f), distLifetime(5.0f, 15.0f)
{
    particles.resize(maxParticles);
    particleData.reserve(maxParticles * 4);
    
    params = getDefaultParams(type, currentSeason);
    
    if (type == RAIN) {
        spawnRate = 500.0f;
    } else if (type == SNOW) {
        spawnRate = 200.0f;
    } else if (type == LEAF) {
        spawnRate = 50.0f;
    } else if (type == HAIL) {
        spawnRate = 300.0f;
    } else if (type == DUST) {
        spawnRate = 150.0f;
    }

    for (auto& p : particles) {
        resetParticle(p);
    }

    initGL();
}

ParticleSystem::~ParticleSystem() {
    glDeleteVertexArrays(1, &VAO);
    glDeleteBuffers(1, &VBO);
}

void ParticleSystem::initGL() {
    glGenVertexArrays(1, &VAO);
    glGenBuffers(1, &VBO);

    glBindVertexArray(VAO);
    glBindBuffer(GL_ARRAY_BUFFER, VBO);

    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 4 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(1);
    glVertexAttribPointer(1, 1, GL_FLOAT, GL_FALSE, 4 * sizeof(float), (void*)(3 * sizeof(float)));

    glBindBuffer(GL_ARRAY_BUFFER, 0);
    glBindVertexArray(0);
}

float ParticleSystem::randomFloat(float min, float max) {
    std::uniform_real_distribution<float> dist(min, max);
    return dist(rng);
}

void ParticleSystem::updateParamsForSeason() {
    ParticleParams seasonal = getSeasonalParams(currentSeason);
    params.gravityScale = seasonal.gravityScale;
}

void ParticleSystem::setSeason(Season season) {
    currentSeason = season;
    updateParamsForSeason();
}

void ParticleSystem::setType(ParticleType type) {
    particleType = type;
    params = getDefaultParams(type, currentSeason);
    updateParamsForSeason();
    
    if (type == RAIN) {
        spawnRate = 500.0f;
    } else if (type == SNOW) {
        spawnRate = 200.0f;
    } else if (type == LEAF) {
        spawnRate = 50.0f;
    } else if (type == HAIL) {
        spawnRate = 300.0f;
    } else if (type == DUST) {
        spawnRate = 150.0f;
    }
    
    for (auto& p : particles) {
        p.isAlive = false;
    }
    activeCount = 0;
    spawnTimer = 0.0f;
}

void ParticleSystem::setParams(const ParticleParams& newParams) {
    params = newParams;
}

void ParticleSystem::setCollisionEnabled(bool enabled) {
    collisionEnabled = enabled;
}

void ParticleSystem::resetParticle(Particle& p) {
    p.position = glm::vec3(
        randomFloat(-spawnArea.x / 2.0f, spawnArea.x / 2.0f),
        spawnArea.y / 2.0f + randomFloat(0.0f, 3.0f),
        randomFloat(-spawnArea.z / 2.0f, spawnArea.z / 2.0f)
    );

    p.velocity = glm::vec3(0.0f, params.initialVelY, 0.0f);
    p.mass = randomFloat(params.massMin, params.massMax);
    p.size = randomFloat(params.sizeMin, params.sizeMax);
    p.maxLifetime = randomFloat(params.lifetimeMin, params.lifetimeMax);

    p.lifetime = 0.0f;
    p.isAlive = false;
    p.type = particleType;
    p.rotation = randomFloat(0.0f, 2.0f * glm::pi<float>());
    p.rotationSpeed = randomFloat(-2.0f, 2.0f);
    p.bounceCount = 0;
}

void ParticleSystem::spawnParticle() {
    for (auto& p : particles) {
        if (!p.isAlive) {
            resetParticle(p);
            p.isAlive = true;
            activeCount++;
            return;
        }
    }
}

void ParticleSystem::updateParticle(Particle& p, float deltaTime, float currentTime, const WindField& wind, CollisionSystem* collision) {
    if (!p.isAlive) return;

    p.lifetime += deltaTime;
    if (p.lifetime >= p.maxLifetime) {
        p.isAlive = false;
        return;
    }

    glm::vec3 windVelocity = wind.getWindVelocity(p.position, currentTime);
    
    glm::vec3 dragForce;
    float dragCoeff = 0.47f;
    float airDensity = 1.225f;
    float crossSection = 3.14159f * p.size * p.size;
    glm::vec3 relVelocity = p.velocity - windVelocity;
    float speed = glm::length(relVelocity);
    if (speed > 0.001f) {
        dragForce = -0.5f * dragCoeff * airDensity * crossSection * speed * glm::normalize(relVelocity);
    } else {
        dragForce = glm::vec3(0.0f);
    }

    float windDragCoeff = 0.47f;
    glm::vec3 windForce;
    float windSpeed = glm::length(windVelocity);
    if (windSpeed > 0.001f) {
        windForce = 0.5f * windDragCoeff * airDensity * crossSection * windSpeed * glm::normalize(windVelocity);
    } else {
        windForce = glm::vec3(0.0f);
    }

    glm::vec3 effectiveGravity = gravity * params.gravityScale;
    glm::vec3 gravityForce = effectiveGravity * p.mass;
    glm::vec3 totalForce = gravityForce + dragForce + windForce;
    p.acceleration = totalForce / p.mass;

    if (params.swirlEffect) {
        float swirlStr = (particleType == LEAF) ? 1.5f : 0.5f;
        float swirl = sin(currentTime * 2.0f + p.position.x * 5.0f + p.rotation) * swirlStr;
        p.acceleration.x += swirl;
        p.acceleration.z += cos(currentTime * 1.5f + p.position.z * 3.0f) * swirlStr * 0.6f;
    }

    p.velocity += p.acceleration * deltaTime;
    
    if (glm::length(p.velocity) > params.terminalVelocity) {
        p.velocity = glm::normalize(p.velocity) * params.terminalVelocity;
    }

    p.rotation += p.rotationSpeed * deltaTime;

    glm::vec3 newPosition = p.position + p.velocity * deltaTime;
    
    if (collisionEnabled && collision) {
        CollisionResult result = collision->checkGroundCollision(newPosition, p.size * 0.5f);
        if (result.hasCollided) {
            if (params.dieOnGround) {
                p.isAlive = false;
                return;
            }
            collision->resolveCollision(newPosition, p.velocity, result, params.restitution, params.friction);
            p.bounceCount++;
            
            if (p.bounceCount > 3 || glm::length(p.velocity) < 0.2f) {
                p.velocity = glm::vec3(0.0f);
            }
        }
    }
    
    p.position = newPosition;
}

void ParticleSystem::update(float deltaTime, float currentTime, const WindField& wind, CollisionSystem* collision) {
    spawnTimer += deltaTime;
    float spawnInterval = 1.0f / spawnRate;
    
    while (spawnTimer >= spawnInterval && activeCount < maxParticles) {
        spawnParticle();
        spawnTimer -= spawnInterval;
    }

    particleData.clear();
    activeCount = 0;

    for (auto& p : particles) {
        updateParticle(p, deltaTime, currentTime, wind, collision);
        if (p.isAlive) {
            particleData.push_back(p.position.x);
            particleData.push_back(p.position.y);
            particleData.push_back(p.position.z);
            particleData.push_back(p.size);
            activeCount++;
        }
    }

    glBindBuffer(GL_ARRAY_BUFFER, VBO);
    glBufferData(GL_ARRAY_BUFFER, particleData.size() * sizeof(float), particleData.data(), GL_DYNAMIC_DRAW);
    glBindBuffer(GL_ARRAY_BUFFER, 0);
}

void ParticleSystem::render() {
    if (activeCount == 0) return;

    glBindVertexArray(VAO);
    glDrawArrays(GL_POINTS, 0, activeCount);
    glBindVertexArray(0);
}

void ParticleSystem::setSpawnArea(const glm::vec3& area) {
    spawnArea = area;
}

void ParticleSystem::setSpawnRate(float rate) {
    spawnRate = rate;
}

void ParticleSystem::setGravity(const glm::vec3& g) {
    gravity = g;
}
