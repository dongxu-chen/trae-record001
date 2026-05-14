#pragma once

#include <filament/Engine.h>
#include <filament/Scene.h>
#include <filament/View.h>
#include <gltfio/AssetLoader.h>
#include <gltfio/ResourceLoader.h>
#include <gltfio/MaterialProvider.h>
#include <math/mat4.h>
#include <memory>
#include <string>
#include <vector>

namespace viewer {

class ModelViewer {
public:
    explicit ModelViewer(filament::Engine* engine, filament::Scene* scene);
    ~ModelViewer();

    bool loadModel(const std::string& gltfPath);
    void setMaterialParameters(float roughness, float metallic);
    void setBaseColor(float r, float g, float b);
    void setTransform(const filament::math::mat4f& transform);
    void setVisible(bool visible);
    void resetMaterial();

    std::vector<std::string> getMaterialNames() const;
    bool hasModel() const { return mAsset != nullptr; }

    gltfio::FilamentAsset* getAsset() const { return mAsset; }
    size_t getAnimationCount() const;
    std::string getAnimationName(size_t index) const;
    float getAnimationDuration(size_t index) const;

private:
    void destroyCurrentAsset();

    filament::Engine* mEngine;
    filament::Scene* mScene;
    std::unique_ptr<gltfio::MaterialProvider> mMaterialProvider;
    gltfio::AssetLoader* mAssetLoader = nullptr;
    gltfio::ResourceLoader* mResourceLoader = nullptr;
    gltfio::FilamentAsset* mAsset = nullptr;

    float mOriginalRoughness = 0.5f;
    float mOriginalMetallic = 0.0f;
};

} 
