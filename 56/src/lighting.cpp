#include "lighting.h"
#include <iostream>
#include <fstream>
#include <filesystem>
#include <filament/LightManager.h>
#include <filament/IndirectLight.h>
#include <filament/Skybox.h>
#include <filament/Texture.h>
#include <image/KtxBundle.h>
#include <image/ImageOps.h>
#include <image/LinearImage.h>
#include <math/mat4.h>

namespace lighting {

LightManager::LightManager(filament::Engine* engine, filament::Scene* scene)
    : mEngine(engine), mScene(scene) {
    mDirectionalLight = utils::Entity();
}

LightManager::~LightManager() {
    destroyCurrentIBL();

    if (mDirectionalLight.isValid()) {
        mEngine->getEntityManager().destroy(mDirectionalLight);
    }
}

void LightManager::destroyCurrentIBL() {
    if (mSkybox) {
        mScene->setSkybox(nullptr);
        mEngine->destroy(mSkybox);
        mSkybox = nullptr;
    }

    if (mIndirectLight) {
        mScene->setIndirectLight(nullptr);
        mEngine->destroy(mIndirectLight);
        mIndirectLight = nullptr;
    }

    if (mSharedTextures) {
        if (mSkyboxTexture) {
            mEngine->destroy(mSkyboxTexture);
            mSkyboxTexture = nullptr;
        }
        mReflectionsTexture = nullptr;
    } else {
        if (mSkyboxTexture) {
            mEngine->destroy(mSkyboxTexture);
            mSkyboxTexture = nullptr;
        }
        if (mReflectionsTexture) {
            mEngine->destroy(mReflectionsTexture);
            mReflectionsTexture = nullptr;
        }
    }
}

bool LightManager::setupIBL(const IBLConfig& config) {
    destroyCurrentIBL();
    mCurrentConfig = config;

    std::filesystem::path path(config.iblPath);
    if (!std::filesystem::exists(path)) {
        std::cerr << "IBL path does not exist: " << config.iblPath << std::endl;
        return false;
    }

    std::string iblDir = path.parent_path().string();
    std::string baseName = path.stem().string();

    if (baseName.ends_with("_ibl")) {
        baseName = baseName.substr(0, baseName.length() - 4);
    }
    if (baseName.ends_with("_skybox")) {
        baseName = baseName.substr(0, baseName.length() - 7);
    }

    std::string skyboxPath = iblDir + "/" + baseName + "_skybox.ktx";
    if (!std::filesystem::exists(skyboxPath)) {
        skyboxPath = iblDir + "/" + baseName + "_ibl.ktx";
    }
    if (!std::filesystem::exists(skyboxPath)) {
        skyboxPath = config.iblPath;
    }

    std::string reflectionsPath = iblDir + "/" + baseName + "_ibl.ktx";
    if (!std::filesystem::exists(reflectionsPath)) {
        reflectionsPath = config.iblPath;
    }

    if (skyboxPath == reflectionsPath) {
        mSharedTextures = true;
        std::ifstream singleFile(skyboxPath, std::ios::binary);
        if (!singleFile.is_open()) {
            std::cerr << "Failed to open IBL file: " << skyboxPath << std::endl;
            return false;
        }

        singleFile.seekg(0, std::ios::end);
        size_t fileSize = singleFile.tellg();
        singleFile.seekg(0, std::ios::beg);

        std::vector<uint8_t> buffer(fileSize);
        singleFile.read((char*)buffer.data(), fileSize);

        image::KtxBundle bundle(buffer.data(), buffer.size());
        mSkyboxTexture = bundle.createTexture(mEngine);
        if (!mSkyboxTexture) {
            std::cerr << "Failed to create skybox texture" << std::endl;
            return false;
        }

        mReflectionsTexture = mSkyboxTexture;
    } else {
        mSharedTextures = false;
        std::ifstream skyboxFile(skyboxPath, std::ios::binary);
        if (!skyboxFile.is_open()) {
            std::cerr << "Failed to open skybox: " << skyboxPath << std::endl;
            return false;
        }

        skyboxFile.seekg(0, std::ios::end);
        size_t skyboxSize = skyboxFile.tellg();
        skyboxFile.seekg(0, std::ios::beg);

        std::vector<uint8_t> skyboxBuffer(skyboxSize);
        skyboxFile.read((char*)skyboxBuffer.data(), skyboxSize);

        image::KtxBundle skyboxBundle(skyboxBuffer.data(), skyboxBuffer.size());
        mSkyboxTexture = skyboxBundle.createTexture(mEngine);
        if (!mSkyboxTexture) {
            std::cerr << "Failed to create skybox texture" << std::endl;
            return false;
        }

        std::ifstream reflectionsFile(reflectionsPath, std::ios::binary);
        if (!reflectionsFile.is_open()) {
            std::cerr << "Failed to open reflections: " << reflectionsPath << std::endl;
            return false;
        }

        reflectionsFile.seekg(0, std::ios::end);
        size_t reflectionsSize = reflectionsFile.tellg();
        reflectionsFile.seekg(0, std::ios::beg);

        std::vector<uint8_t> reflectionsBuffer(reflectionsSize);
        reflectionsFile.read((char*)reflectionsBuffer.data(), reflectionsSize);

        image::KtxBundle reflectionsBundle(reflectionsBuffer.data(), reflectionsBuffer.size());
        mReflectionsTexture = reflectionsBundle.createTexture(mEngine);
        if (!mReflectionsTexture) {
            std::cerr << "Failed to create reflections texture" << std::endl;
            return false;
        }
    }

    filament::IndirectLight::Builder iblBuilder;
    iblBuilder.reflections(mReflectionsTexture);
    iblBuilder.intensity(config.intensity);
    iblBuilder.rotation(
        filament::math::mat3f::rotation(config.rotation, {0, 1, 0})
    );

    mIndirectLight = iblBuilder.build(*mEngine);
    if (!mIndirectLight) {
        std::cerr << "Failed to build indirect light" << std::endl;
        return false;
    }

    mScene->setIndirectLight(mIndirectLight);

    filament::Skybox::Builder skyboxBuilder;
    skyboxBuilder.environment(mSkyboxTexture);
    skyboxBuilder.intensity(config.environmentIntensity);
    mSkybox = skyboxBuilder.build(*mEngine);
    if (mSkybox) {
        mScene->setSkybox(mSkybox);
    }

    std::cout << "IBL setup complete. Intensity: " << config.intensity << std::endl;
    return true;
}

void LightManager::setupDirectionalLight(float intensity) {
    if (!mDirectionalLight.isValid()) {
        mDirectionalLight = mEngine->getEntityManager().create();
    }

    filament::LightManager::Builder lightBuilder(filament::LightManager::Type::SUN);
    lightBuilder.color({1.0f, 0.95f, 0.9f});
    lightBuilder.intensity(intensity);
    lightBuilder.direction({0.5f, -1.0f, -0.7f});
    lightBuilder.castShadows(true);
    lightBuilder.shadowOptions({
        .mapSize = 1024,
        .shadowCascades = 4,
    });
    lightBuilder.build(*mEngine, mDirectionalLight);

    mScene->addEntity(mDirectionalLight);

    std::cout << "Directional light setup complete. Intensity: " << intensity << std::endl;
}

void LightManager::updateIBLIntensity(float intensity) {
    if (!mIndirectLight) {
        return;
    }

    mIndirectLight->setIntensity(intensity);
    mCurrentConfig.intensity = intensity;
}

void LightManager::updateIBLRotation(float rotation) {
    if (!mIndirectLight) {
        return;
    }

    filament::math::mat3f rotMat = filament::math::mat3f::rotation(rotation, {0, 1, 0});
    mIndirectLight->setRotation(rotMat);
    mCurrentConfig.rotation = rotation;
}

void LightManager::updateEnvironmentIntensity(float intensity) {
    mCurrentConfig.environmentIntensity = intensity;
}

} 
