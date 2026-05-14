#ifndef PARTICLE_H
#define PARTICLE_H

#include <glad/glad.h>
#include <glm/glm.hpp>
#include <vector>
#include <random>
#include "wind.h"
#include "collision.h"

enum ParticleType {
    SNOW,
    RAIN,
    LEAF,
    HAIL,
    DUST
};

enum Season {
    WINTER,
    SPRING,
    SUMMER,
    AUTUMN
};

struct ParticleParams {
    float gravityScale;
    float massMin;
    float massMax;
    float sizeMin;
    float sizeMax;
    float lifetimeMin;
    float lifetimeMax;
    float initialVelY;
    float terminalVelocity;
    float restitution;
    float friction;
    bool swirlEffect;
    bool dieOnGround;
    glm::vec3 color;
};

struct Particle {
    glm::vec3 position;
    glm::vec3 velocity;
    glm::vec3 acceleration;
    float mass;
    float size;
    float lifetime;
    float maxLifetime;
    bool isAlive;
    ParticleType type;
    float rotation;
    float rotationSpeed;
    int bounceCount;
};

class ParticleSystem {
public:
    ParticleSystem(ParticleType type, unsigned int maxParticles, const glm::vec3& spawnArea);
    ~ParticleSystem();

    void update(float deltaTime, float currentTime, const WindField& wind, CollisionSystem* collision);
    void render();

    void setSpawnArea(const glm::vec3& area);
    void setSpawnRate(float rate);
    void setGravity(const glm::vec3& gravity);
    void setSeason(Season season);
    void setParams(const ParticleParams& params);
    void setType(ParticleType type);
    void setCollisionEnabled(bool enabled);
    
    ParticleType getType() const { return particleType; }
    Season getSeason() const { return currentSeason; }
    const ParticleParams& getParams() const { return params; }
    unsigned int getActiveCount() const { return activeCount; }
    
    static ParticleParams getDefaultParams(ParticleType type, Season season);
    static ParticleParams getSeasonalParams(Season season);

private:
    std::vector<Particle> particles;
    unsigned int maxParticles;
    unsigned int activeCount;
    ParticleType particleType;
    Season currentSeason;
    glm::vec3 spawnArea;
    float spawnRate;
    float spawnTimer;
    glm::vec3 gravity;
    ParticleParams params;
    bool collisionEnabled;

    GLuint VAO, VBO;
    std::vector<float> particleData;

    std::mt19937 rng;
    std::uniform_real_distribution<float> distPos;
    std::uniform_real_distribution<float> distSize;
    std::uniform_real_distribution<float> distLifetime;

    void spawnParticle();
    void updateParticle(Particle& p, float deltaTime, float currentTime, const WindField& wind, CollisionSystem* collision);
    void resetParticle(Particle& p);
    void initGL();
    float randomFloat(float min, float max);
    void updateParamsForSeason();
};

#endif
