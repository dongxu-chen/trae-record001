#pragma once

#include <filament/Engine.h>
#include <filament/SwapChain.h>
#include <filament/Renderer.h>
#include <utils/EntityManager.h>
#include <string>
#include <vector>

namespace animation {
    class AnimationManager;
}

namespace ui {

struct MaterialParams {
    float roughness = 0.5f;
    float metallic = 0.0f;
    float baseColorR = 0.8f;
    float baseColorG = 0.8f;
    float baseColorB = 0.8f;
};

struct KeyframeData {
    float time = 0.0f;
    float value = 0.0f;
};

struct ChannelData {
    std::string name;
    bool enabled = true;
    std::vector<KeyframeData> keyframes;
};

struct AnimationState {
    bool isPlaying = false;
    bool isLooping = true;
    float currentTime = 0.0f;
    float totalDuration = 0.0f;
    size_t currentAnimationIndex = 0;
    size_t animationCount = 0;
    std::vector<std::string> animationNames;
    std::vector<ChannelData> customChannels;
    int selectedAnimation = 0;
    int selectedChannel = -1;
    int selectedKeyframe = -1;
    bool showKeyframeEditor = false;
};

struct ConfigState {
    std::string presetName;
    std::string presetDescription;
    std::string savePath;
    std::string loadPath;
    bool saveRequested = false;
    bool loadRequested = false;
    bool showConfigPanel = false;
};

struct UIState {
    MaterialParams materialParams;
    float iblIntensity = 30000.0f;
    float iblRotation = 0.0f;
    float envIntensity = 1.0f;
    bool showDemoWindow = false;
    std::string modelPath;
    std::string iblPath;

    AnimationState animation;
    ConfigState config;
};

class UIManager {
public:
    explicit UIManager(filament::Engine* engine);
    ~UIManager();

    void initialize(utils::Entity window);
    void render(filament::Renderer* renderer, filament::SwapChain* swapChain);
    void updateUIState();

    const UIState& getState() const { return mState; }
    bool hasMaterialParamsChanged() const { return mMaterialParamsChanged; }
    bool hasIBLParamsChanged() const { return mIBLParamsChanged; }
    bool hasModelLoadRequest() const { return mModelLoadRequested; }
    bool hasIBLLoadRequest() const { return mIBLLoadRequested; }

    void resetMaterialParamsChanged() { mMaterialParamsChanged = false; }
    void resetIBLParamsChanged() { mIBLParamsChanged = false; }
    void resetModelLoadRequest() { mModelLoadRequested = false; }
    void resetIBLLoadRequest() { mIBLLoadRequested = false; }

    void setAnimationManager(animation::AnimationManager* animMgr) { mAnimationManager = animMgr; }

    bool hasAnimationPlayRequest() const { return mPlayRequested; }
    bool hasAnimationPauseRequest() const { return mPauseRequested; }
    bool hasAnimationStopRequest() const { return mStopRequested; }
    bool hasAnimationSeekRequest() const { return mSeekRequested; }
    bool hasAnimationIndexChange() const { return mAnimationIndexChanged; }

    void resetAnimationPlayRequest() { mPlayRequested = false; }
    void resetAnimationPauseRequest() { mPauseRequested = false; }
    void resetAnimationStopRequest() { mStopRequested = false; }
    void resetAnimationSeekRequest() { mSeekRequested = false; }
    void resetAnimationIndexChange() { mAnimationIndexChanged = false; }

    bool hasConfigSaveRequest() const { return mState.config.saveRequested; }
    bool hasConfigLoadRequest() const { return mState.config.loadRequested; }

    void resetConfigSaveRequest() { mState.config.saveRequested = false; }
    void resetConfigLoadRequest() { mState.config.loadRequested = false; }

    void syncAnimationState(const animation::AnimationManager* animMgr);
    void updateCustomChannelsFromUI();

private:
    void renderAnimationPanel();
    void renderKeyframeEditor();
    void renderConfigPanel();

    filament::Engine* mEngine;
    animation::AnimationManager* mAnimationManager = nullptr;
    UIState mState;
    bool mMaterialParamsChanged = false;
    bool mIBLParamsChanged = false;
    bool mModelLoadRequested = false;
    bool mIBLLoadRequested = false;
    bool mInitialized = false;

    bool mPlayRequested = false;
    bool mPauseRequested = false;
    bool mStopRequested = false;
    bool mSeekRequested = false;
    bool mAnimationIndexChanged = false;
};

} 
