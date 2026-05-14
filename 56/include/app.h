#pragma once

#include <filament/Engine.h>
#include <filament/Scene.h>
#include <filament/SwapChain.h>
#include <filament/Renderer.h>
#include <filament/View.h>
#include <filament/Camera.h>
#include <filagui/ImGuiHelper.h>
#include <utils/EntityManager.h>
#include <chrono>
#include <memory>
#include "viewer.h"
#include "lighting.h"
#include "ui.h"
#include "animation.h"
#include "config_loader.h"

class MaterialViewerApp {
public:
    MaterialViewerApp();
    ~MaterialViewerApp();

    bool initialize(int width, int height, const std::string& title);
    void run();
    void cleanup();

private:
    void setupCamera();
    void setupDefaultScene();
    void onRender();
    void onUIUpdate();
    void onAnimationUpdate();
    void onConfigUpdate();

    filament::Engine* mEngine = nullptr;
    filament::Scene* mScene = nullptr;
    filament::SwapChain* mSwapChain = nullptr;
    filament::Renderer* mRenderer = nullptr;
    filament::View* mView = nullptr;
    filament::Camera* mCamera = nullptr;
    utils::Entity mCameraEntity;
    utils::Entity mWindowEntity;

    std::unique_ptr<viewer::ModelViewer> mModelViewer;
    std::unique_ptr<lighting::LightManager> mLightManager;
    std::unique_ptr<ui::UIManager> mUIManager;
    std::unique_ptr<animation::AnimationManager> mAnimationManager;
    std::unique_ptr<config::ConfigLoader> mConfigLoader;

    std::chrono::steady_clock::time_point mLastFrameTime;

    int mWidth = 1280;
    int mHeight = 720;
    bool mRunning = true;
    filagui::ImGuiHelper* mImGuiHelper = nullptr;
};
