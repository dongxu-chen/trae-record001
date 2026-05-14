#include "viewer.h"
#include <iostream>
#include <fstream>
#include <filesystem>
#include <filament/TransformManager.h>
#include <gltfio/AssetLoader.h>
#include <gltfio/ResourceLoader.h>
#include <gltfio/MaterialProvider.h>
#include <filament/Material.h>
#include <filament/MaterialInstance.h>
#include <utils/EntityManager.h>

namespace viewer {

ModelViewer::ModelViewer(filament::Engine* engine, filament::Scene* scene)
    : mEngine(engine), mScene(scene) {

    mMaterialProvider = gltfio::createMaterialProvider(engine);

    gltfio::AssetLoader::Config config;
    config.engine = engine;
    config.materials = mMaterialProvider.get();
    mAssetLoader = new gltfio::AssetLoader(config);

    gltfio::ResourceLoader::Config resourceConfig;
    resourceConfig.engine = engine;
    resourceConfig.normalizeSkinningWeights = true;
    resourceConfig.recomputeBoundingBoxes = true;
    resourceConfig.generateTangents = true;
    mResourceLoader = new gltfio::ResourceLoader(resourceConfig);
}

ModelViewer::~ModelViewer() {
    destroyCurrentAsset();

    if (mResourceLoader) {
        delete mResourceLoader;
        mResourceLoader = nullptr;
    }

    if (mAssetLoader) {
        delete mAssetLoader;
        mAssetLoader = nullptr;
    }
}

void ModelViewer::destroyCurrentAsset() {
    if (mAsset) {
        if (mResourceLoader) {
            mResourceLoader->evictResourceData();
        }

        mScene->removeEntities(mAsset->getEntities(), mAsset->getEntityCount());

        if (mAssetLoader) {
            mAssetLoader->destroyAsset(mAsset);
        }
        mAsset = nullptr;

        mEngine->flushAndWait();
    }
}

bool ModelViewer::loadModel(const std::string& gltfPath) {
    destroyCurrentAsset();

    std::filesystem::path path(gltfPath);
    if (!std::filesystem::exists(path)) {
        std::cerr << "File does not exist: " << gltfPath << std::endl;
        return false;
    }

    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file.is_open()) {
        std::cerr << "Failed to open file: " << gltfPath << std::endl;
        return false;
    }

    std::streamsize size = file.tellg();
    file.seekg(0, std::ios::beg);

    std::vector<uint8_t> buffer(size);
    if (!file.read((char*)buffer.data(), size)) {
        std::cerr << "Failed to read file: " << gltfPath << std::endl;
        return false;
    }

    mAsset = mAssetLoader->createAssetFromJson(buffer.data(), buffer.size());
    if (!mAsset) {
        mAsset = mAssetLoader->createAssetFromBinary(buffer.data(), buffer.size());
    }

    if (!mAsset) {
        std::cerr << "Failed to parse glTF file: " << gltfPath << std::endl;
        return false;
    }

    std::string basePath = path.parent_path().string() + "/";
    mResourceLoader->asyncBeginLoad(mAsset);

    while (mResourceLoader->asyncGetLoadProgress() < 1.0f) {
        mResourceLoader->asyncUpdateLoad();
    }

    mResourceLoader->asyncEndLoad();

    auto const entities = mAsset->getEntities();
    mScene->addEntities(entities, mAsset->getEntityCount());

    const filament::Aabb& aabb = mAsset->getBoundingBox();
    filament::math::float3 center = (aabb.min + aabb.max) * 0.5f;
    filament::math::float3 extents = (aabb.max - aabb.min) * 0.5f;
    float maxExtent = std::max({extents.x, extents.y, extents.z});

    float scale = 1.0f;
    if (maxExtent > 0.001f) {
        scale = 1.0f / maxExtent;
    }

    filament::TransformManager& tcm = mEngine->getTransformManager();
    filament::TransformManager::Instance ti = tcm.getInstance(mAsset->getRoot());
    if (ti.isValid()) {
        filament::math::mat4f transform = filament::math::mat4f::translation(-center)
            * filament::math::mat4f::scaling(scale);
        tcm.setTransform(ti, transform);
    }

    std::cout << "Model loaded successfully. Entity count: "
              << mAsset->getEntityCount() << std::endl;

    return true;
}

void ModelViewer::setMaterialParameters(float roughness, float metallic) {
    if (!mAsset) {
        return;
    }

    roughness = std::max(0.001f, std::min(1.0f, roughness));
    metallic = std::max(0.0f, std::min(1.0f, metallic));

    const gltfio::MaterialInstance* const* materials = mAsset->getMaterialInstances();
    for (size_t i = 0; i < mAsset->getMaterialInstanceCount(); ++i) {
        gltfio::MaterialInstance* mat = const_cast<gltfio::MaterialInstance*>(materials[i]);
        if (mat) {
            mat->setParameter("roughness", roughness);
            mat->setParameter("metallic", metallic);
        }
    }
}

void ModelViewer::setBaseColor(float r, float g, float b) {
    if (!mAsset) {
        return;
    }

    r = std::max(0.0f, std::min(1.0f, r));
    g = std::max(0.0f, std::min(1.0f, g));
    b = std::max(0.0f, std::min(1.0f, b));

    filament::math::float4 color(r, g, b, 1.0f);
    const gltfio::MaterialInstance* const* materials = mAsset->getMaterialInstances();
    for (size_t i = 0; i < mAsset->getMaterialInstanceCount(); ++i) {
        gltfio::MaterialInstance* mat = const_cast<gltfio::MaterialInstance*>(materials[i]);
        if (mat) {
            mat->setParameter("baseColorFactor", color);
        }
    }
}

void ModelViewer::setTransform(const filament::math::mat4f& transform) {
    if (!mAsset) {
        return;
    }

    filament::TransformManager& tcm = mEngine->getTransformManager();
    filament::TransformManager::Instance ti = tcm.getInstance(mAsset->getRoot());
    if (ti.isValid()) {
        tcm.setTransform(ti, transform);
    }
}

void ModelViewer::setVisible(bool visible) {
    if (!mAsset) {
        return;
    }

    filament::RenderableManager& rcm = mEngine->getRenderableManager();
    auto entities = mAsset->getRenderableEntities();
    for (size_t i = 0; i < mAsset->getRenderableEntityCount(); ++i) {
        filament::RenderableManager::Instance ri = rcm.getInstance(entities[i]);
        if (ri.isValid()) {
            rcm.setLayerMask(ri,
                visible ? 0x1 : 0x0,
                visible ? 0x1 : 0x0
            );
        }
    }
}

void ModelViewer::resetMaterial() {
    setMaterialParameters(mOriginalRoughness, mOriginalMetallic);
}

std::vector<std::string> ModelViewer::getMaterialNames() const {
    std::vector<std::string> names;
    if (!mAsset) {
        return names;
    }

    const gltfio::MaterialInstance* const* materials = mAsset->getMaterialInstances();
    for (size_t i = 0; i < mAsset->getMaterialInstanceCount(); ++i) {
        gltfio::MaterialInstance* mat = const_cast<gltfio::MaterialInstance*>(materials[i]);
        if (mat) {
            names.push_back(std::to_string(i));
        }
    }

    return names;
}

size_t ModelViewer::getAnimationCount() const {
    if (!mAsset) {
        return 0;
    }
    return mAsset->getAnimationCount();
}

std::string ModelViewer::getAnimationName(size_t index) const {
    if (!mAsset || index >= mAsset->getAnimationCount()) {
        return "";
    }
    const char* name = mAsset->getAnimationName(index);
    return name ? std::string(name) : std::string("Animation ") + std::to_string(index);
}

float ModelViewer::getAnimationDuration(size_t index) const {
    if (!mAsset || index >= mAsset->getAnimationCount()) {
        return 0.0f;
    }
    return mAsset->getAnimationDuration(index);
}

} 
