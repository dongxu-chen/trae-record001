#pragma once

#include <filament/Engine.h>
#include <filament/Scene.h>
#include <filament/IndirectLight.h>
#include <filament/Texture.h>
#include <utils/EntityManager.h>
#include <string>

namespace lighting {

struct IBLConfig {
    std::string iblPath;
    float intensity = 30000.0f;
    float rotation = 0.0f;
    float environmentIntensity = 1.0f;
};

class LightManager {
public:
    explicit LightManager(filament::Engine* engine, filament::Scene* scene);
    ~LightManager();

    bool setupIBL(const IBLConfig& config);
    void setupDirectionalLight(float intensity = 100000.0f);
    void updateIBLIntensity(float intensity);
    void updateIBLRotation(float rotation);
    void updateEnvironmentIntensity(float intensity);

    bool hasIBL() const { return mIndirectLight != nullptr; }

private:
    void destroyCurrentIBL();

    filament::Engine* mEngine;
    filament::Scene* mScene;
    filament::IndirectLight* mIndirectLight = nullptr;
    filament::Skybox* mSkybox = nullptr;
    filament::Texture* mSkyboxTexture = nullptr;
    filament::Texture* mReflectionsTexture = nullptr;
    bool mSharedTextures = false;

    utils::Entity mDirectionalLight;
    IBLConfig mCurrentConfig;
};

} 
