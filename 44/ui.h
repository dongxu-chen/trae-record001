#ifndef UI_H
#define UI_H

#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include <glm/glm.hpp>
#include <vector>

#include "particle.h"
#include "wind.h"
#include "collision.h"

struct UISettings {
    bool showUI;
    bool showSnow;
    bool showRain;
    bool showLeaf;
    bool showHail;
    bool showDust;
    Season currentSeason;
    GroundType groundType;
    
    float windStrength;
    float windTurbulence;
    glm::vec3 windDirection;
    
    float precipitationMultiplier;
    float gravityMultiplier;
    
    bool collisionEnabled;
    float restitutionOverride;
    float frictionOverride;
    
    float heightMapScale;
    float heightMapFreq;
    
    UISettings();
};

class UIManager {
public:
    UIManager();
    ~UIManager();
    
    void init(GLFWwindow* window);
    void shutdown();
    
    void newFrame();
    void render();
    
    void buildUI(UISettings& settings,
                 const std::vector<ParticleSystem*>& systems,
                 WindField& wind,
                 CollisionSystem& collision);
    
    UISettings& getSettings() { return settings; }
    
private:
    bool initialized;
    UISettings settings;
    
    void drawWeatherPanel(UISettings& settings, const std::vector<ParticleSystem*>& systems);
    void drawWindPanel(UISettings& settings, WindField& wind);
    void drawPhysicsPanel(UISettings& settings);
    void drawTerrainPanel(UISettings& settings, CollisionSystem& collision);
    void drawStatsPanel(const std::vector<ParticleSystem*>& systems);
    
    const char* getSeasonName(Season season);
    const char* getParticleTypeName(ParticleType type);
    const char* getGroundTypeName(GroundType type);
};

#endif
