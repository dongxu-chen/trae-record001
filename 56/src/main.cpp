#include <iostream>
#include <memory>
#include "app.h"
#include <filament/Engine.h>

#if defined(WIN32)
#include <windows.h>
#include <filament/NativeWindowHelper.h>
#endif

int main(int argc, char** argv) {
    MaterialViewerApp app;

    if (!app.initialize(1280, 720, "Filament Material Previewer")) {
        std::cerr << "Failed to initialize application" << std::endl;
        return -1;
    }

    app.run();
    app.cleanup();

    return 0;
}

MaterialViewerApp::MaterialViewerApp() {
    mLastFrameTime = std::chrono::steady_clock::now();
}

MaterialViewerApp::~MaterialViewerApp() {
    cleanup();
}

bool MaterialViewerApp::initialize(int width, int height, const std::string& title) {
    mWidth = width;
    mHeight = height;

    filament::Engine::Backend backend = filament::Engine::Backend::OPENGL;
    mEngine = filament::Engine::create(backend);
    if (!mEngine) {
        std::cerr << "Failed to create Filament engine" << std::endl;
        return false;
    }

    mScene = mEngine->createScene();

#if defined(WIN32)
    HWND hwnd = ::GetConsoleWindow();
    if (hwnd == nullptr) {
        std::cerr << "Warning: No console window found, using dummy window" << std::endl;
        mWindowEntity = utils::Entity();
    } else {
        mWindowEntity = filagui::NativeWindowHelper::get().getEntityForWindow((void*)hwnd);
    }
#else
    mWindowEntity = utils::Entity();
#endif

    mSwapChain = mEngine->createSwapChain(
        filagui::NativeWindowHelper::get().getNativeWindowFor(mWindowEntity),
        filament::Engine::Backend::OPENGL
    );

    mRenderer = mEngine->createRenderer();
    mView = mEngine->createView();
    mView->setScene(mScene);
    mView->setViewport({0, 0, (uint32_t)mWidth, (uint32_t)mHeight});

    mModelViewer = std::make_unique<viewer::ModelViewer>(mEngine, mScene);
    mLightManager = std::make_unique<lighting::LightManager>(mEngine, mScene);
    mUIManager = std::make_unique<ui::UIManager>(mEngine);
    mAnimationManager = std::make_unique<animation::AnimationManager>();
    mConfigLoader = std::make_unique<config::ConfigLoader>();

    setupCamera();
    setupDefaultScene();

    mUIManager->initialize(mWindowEntity);
    mUIManager->setAnimationManager(mAnimationManager.get());

    mRunning = true;
    std::cout << "Application initialized successfully" << std::endl;
    return true;
}

void MaterialViewerApp::setupCamera() {
    mCameraEntity = mEngine->getEntityManager().create();
    mCamera = mEngine->createCamera(mCameraEntity);

    mCamera->setProjection(45.0, double(mWidth) / mHeight, 0.1, 100.0);
    mCamera->lookAt({0, 0, 5}, {0, 0, 0}, {0, 1, 0});
    mView->setCamera(mCamera);
}

void MaterialViewerApp::setupDefaultScene() {
    mLightManager->setupDirectionalLight(50000.0f);

    std::cout << "Default scene setup complete" << std::endl;
    std::cout << "Use UI to load glTF models and IBL environments" << std::endl;
}

void MaterialViewerApp::onAnimationUpdate() {
    if (!mAnimationManager) {
        return;
    }

    if (mUIManager->hasAnimationPlayRequest()) {
        int selectedAnim = mUIManager->getState().animation.selectedAnimation;
        if (selectedAnim >= 0 && (size_t)selectedAnim < mModelViewer->getAnimationCount()) {
            mAnimationManager->play((size_t)selectedAnim);
        }
        mUIManager->resetAnimationPlayRequest();
    }

    if (mUIManager->hasAnimationPauseRequest()) {
        mAnimationManager->pause();
        mUIManager->resetAnimationPauseRequest();
    }

    if (mUIManager->hasAnimationStopRequest()) {
        mAnimationManager->stop();
        mUIManager->resetAnimationStopRequest();
    }

    if (mUIManager->hasAnimationSeekRequest()) {
        float time = mUIManager->getState().animation.currentTime;
        mAnimationManager->seek(time);
        mUIManager->resetAnimationSeekRequest();
    }

    if (mUIManager->hasAnimationIndexChange()) {
        int selectedAnim = mUIManager->getState().animation.selectedAnimation;
        if (selectedAnim >= 0 && (size_t)selectedAnim < mModelViewer->getAnimationCount()) {
            mAnimationManager->play((size_t)selectedAnim);
        }
        mUIManager->resetAnimationIndexChange();
    }

    mAnimationManager->setLooping(mUIManager->getState().animation.isLooping);
}

void MaterialViewerApp::onConfigUpdate() {
    if (!mConfigLoader) {
        return;
    }

    if (mUIManager->hasConfigSaveRequest()) {
        const auto& state = mUIManager->getState();
        config::MaterialPreset preset;
        preset.name = state.config.presetName;
        preset.description = state.config.presetDescription;
        preset.roughness = state.materialParams.roughness;
        preset.metallic = state.materialParams.metallic;
        preset.baseColorR = state.materialParams.baseColorR;
        preset.baseColorG = state.materialParams.baseColorG;
        preset.baseColorB = state.materialParams.baseColorB;

        if (!preset.name.empty() && !state.config.savePath.empty()) {
            mConfigLoader->saveMaterialPreset(state.config.savePath, preset);
        }
        mUIManager->resetConfigSaveRequest();
    }

    if (mUIManager->hasConfigLoadRequest()) {
        const auto& state = mUIManager->getState();
        if (!state.config.loadPath.empty()) {
            config::MaterialPreset preset;
            if (mConfigLoader->loadMaterialPreset(state.config.loadPath, preset)) {
                mUIManager->getState().materialParams.roughness = preset.roughness;
                mUIManager->getState().materialParams.metallic = preset.metallic;
                mUIManager->getState().materialParams.baseColorR = preset.baseColorR;
                mUIManager->getState().materialParams.baseColorG = preset.baseColorG;
                mUIManager->getState().materialParams.baseColorB = preset.baseColorB;
            }
        }
        mUIManager->resetConfigLoadRequest();
    }
}

void MaterialViewerApp::onUIUpdate() {
    if (mUIManager->hasMaterialParamsChanged()) {
        const auto& state = mUIManager->getState();
        if (mModelViewer->hasModel()) {
            mModelViewer->setMaterialParameters(
                state.materialParams.roughness,
                state.materialParams.metallic
            );
            mModelViewer->setBaseColor(
                state.materialParams.baseColorR,
                state.materialParams.baseColorG,
                state.materialParams.baseColorB
            );
        }
        mUIManager->resetMaterialParamsChanged();
    }

    if (mUIManager->hasIBLParamsChanged()) {
        const auto& state = mUIManager->getState();
        mLightManager->updateIBLIntensity(state.iblIntensity);
        mLightManager->updateIBLRotation(state.iblRotation);
        mLightManager->updateEnvironmentIntensity(state.envIntensity);
        mUIManager->resetIBLParamsChanged();
    }

    if (mUIManager->hasModelLoadRequest()) {
        const auto& state = mUIManager->getState();
        if (!state.modelPath.empty()) {
            if (mModelViewer->loadModel(state.modelPath)) {
                std::cout << "Model loaded: " << state.modelPath << std::endl;
                if (mAnimationManager) {
                    mAnimationManager->initialize(mEngine, mModelViewer->getAsset());
                }
            } else {
                std::cerr << "Failed to load model: " << state.modelPath << std::endl;
            }
        }
        mUIManager->resetModelLoadRequest();
    }

    if (mUIManager->hasIBLLoadRequest()) {
        const auto& state = mUIManager->getState();
        if (!state.iblPath.empty()) {
            lighting::IBLConfig config;
            config.iblPath = state.iblPath;
            config.intensity = state.iblIntensity;
            if (mLightManager->setupIBL(config)) {
                std::cout << "IBL loaded: " << state.iblPath << std::endl;
            } else {
                std::cerr << "Failed to load IBL: " << state.iblPath << std::endl;
            }
        }
        mUIManager->resetIBLLoadRequest();
    }

    onAnimationUpdate();
    onConfigUpdate();

    if (mAnimationManager) {
        mUIManager->syncAnimationState(mAnimationManager.get());
    }
}

void MaterialViewerApp::onRender() {
    auto now = std::chrono::steady_clock::now();
    std::chrono::duration<float> delta = now - mLastFrameTime;
    float deltaTime = delta.count();
    mLastFrameTime = now;

    if (mAnimationManager) {
        mAnimationManager->update(deltaTime);
    }

    onUIUpdate();

    if (mRenderer->beginFrame(mSwapChain)) {
        mRenderer->render(mView);
        mUIManager->render(mRenderer, mSwapChain);
        mRenderer->endFrame();
    }
}

void MaterialViewerApp::run() {
    std::cout << "Running Material Previewer..." << std::endl;
    std::cout << "Press Ctrl+C to exit" << std::endl;

    while (mRunning) {
        onRender();
    }
}

void MaterialViewerApp::cleanup() {
    if (mConfigLoader) {
        mConfigLoader.reset();
    }
    if (mAnimationManager) {
        mAnimationManager.reset();
    }
    if (mUIManager) {
        mUIManager.reset();
    }
    if (mModelViewer) {
        mModelViewer.reset();
    }
    if (mLightManager) {
        mLightManager.reset();
    }

    if (mCamera) {
        mEngine->destroyCameraComponent(mCameraEntity);
        mCamera = nullptr;
    }

    if (mView) {
        mEngine->destroy(mView);
        mView = nullptr;
    }
    if (mRenderer) {
        mEngine->destroy(mRenderer);
        mRenderer = nullptr;
    }
    if (mSwapChain) {
        mEngine->destroy(mSwapChain);
        mSwapChain = nullptr;
    }
    if (mScene) {
        mEngine->destroy(mScene);
        mScene = nullptr;
    }
    if (mEngine) {
        filament::Engine::destroy(&mEngine);
        mEngine = nullptr;
    }

    mRunning = false;
    std::cout << "Cleanup complete" << std::endl;
}
