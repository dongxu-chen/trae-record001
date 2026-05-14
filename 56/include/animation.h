#pragma once

#include <gltfio/Animator.h>
#include <gltfio/FilamentAsset.h>
#include <filament/Engine.h>
#include <string>
#include <vector>
#include <functional>
#include <memory>

namespace animation {

struct Keyframe {
    float time = 0.0f;
    float value = 0.0f;
};

struct KeyframeChannel {
    std::string name;
    std::vector<Keyframe> keyframes;
    std::function<void(float)> callback;
};

class AnimationManager {
public:
    AnimationManager();
    ~AnimationManager();

    void initialize(filament::Engine* engine, gltfio::FilamentAsset* asset);
    void shutdown();

    void update(float deltaTime);

    size_t getAnimationCount() const;
    std::string getAnimationName(size_t index) const;
    float getAnimationDuration(size_t index) const;

    void play(size_t index);
    void pause();
    void resume();
    void stop();
    void seek(float time);
    void setLooping(bool looping);

    bool isPlaying() const { return mIsPlaying; }
    bool isLooping() const { return mIsLooping; }
    float getCurrentTime() const { return mCurrentTime; }
    size_t getCurrentAnimationIndex() const { return mCurrentIndex; }

    void addCustomChannel(const KeyframeChannel& channel);
    void removeCustomChannel(const std::string& name);
    void clearCustomChannels();

    KeyframeChannel* getCustomChannel(const std::string& name);

    size_t getCustomChannelCount() const { return mCustomChannels.size(); }
    const std::vector<KeyframeChannel>& getCustomChannels() const { return mCustomChannels; }

    bool hasAnimator() const { return mAnimator != nullptr; }

private:
    void updateCustomChannels(float time);
    float evaluateChannel(const KeyframeChannel& channel, float time);

    filament::Engine* mEngine = nullptr;
    gltfio::FilamentAsset* mAsset = nullptr;
    gltfio::Animator* mAnimator = nullptr;

    bool mIsPlaying = false;
    bool mIsLooping = true;
    float mCurrentTime = 0.0f;
    float mTotalDuration = 0.0f;
    size_t mCurrentIndex = 0;

    std::vector<KeyframeChannel> mCustomChannels;
};

} 
