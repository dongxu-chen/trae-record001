#include "animation.h"
#include <iostream>
#include <algorithm>

namespace animation {

AnimationManager::AnimationManager() {
}

AnimationManager::~AnimationManager() {
    shutdown();
}

void AnimationManager::initialize(filament::Engine* engine, gltfio::FilamentAsset* asset) {
    shutdown();

    mEngine = engine;
    mAsset = asset;

    if (mAsset && mAsset->getAnimator()) {
        mAnimator = mAsset->getAnimator();
        mIsPlaying = false;
        mCurrentTime = 0.0f;
        mCurrentIndex = 0;
        mTotalDuration = 0.0f;

        if (mAsset->getAnimationCount() > 0) {
            mTotalDuration = mAsset->getAnimationDuration(0);
        }

        std::cout << "AnimationManager initialized with "
                  << mAsset->getAnimationCount() << " animations" << std::endl;
    }
}

void AnimationManager::shutdown() {
    mAnimator = nullptr;
    mAsset = nullptr;
    mEngine = nullptr;
    mIsPlaying = false;
    mCurrentTime = 0.0f;
    mTotalDuration = 0.0f;
    mCurrentIndex = 0;
}

void AnimationManager::update(float deltaTime) {
    if (!mAnimator) {
        return;
    }

    if (mIsPlaying && mTotalDuration > 0.0f) {
        mCurrentTime += deltaTime;

        if (mIsLooping) {
            while (mCurrentTime >= mTotalDuration) {
                mCurrentTime -= mTotalDuration;
            }
        } else {
            if (mCurrentTime >= mTotalDuration) {
                mCurrentTime = mTotalDuration;
                mIsPlaying = false;
            }
        }

        if (mCurrentIndex < mAsset->getAnimationCount()) {
            mAnimator->applyAnimation(mCurrentIndex, mCurrentTime);
        }
    }

    updateCustomChannels(mCurrentTime);
}

size_t AnimationManager::getAnimationCount() const {
    if (!mAsset) {
        return 0;
    }
    return mAsset->getAnimationCount();
}

std::string AnimationManager::getAnimationName(size_t index) const {
    if (!mAsset || index >= mAsset->getAnimationCount()) {
        return "";
    }
    const char* name = mAsset->getAnimationName(index);
    return name ? std::string(name) : std::string("Animation ") + std::to_string(index);
}

float AnimationManager::getAnimationDuration(size_t index) const {
    if (!mAsset || index >= mAsset->getAnimationCount()) {
        return 0.0f;
    }
    return mAsset->getAnimationDuration(index);
}

void AnimationManager::play(size_t index) {
    if (!mAnimator || !mAsset) {
        return;
    }

    if (index >= mAsset->getAnimationCount()) {
        std::cerr << "Animation index out of range: " << index << std::endl;
        return;
    }

    mCurrentIndex = index;
    mTotalDuration = mAsset->getAnimationDuration(index);
    mCurrentTime = 0.0f;
    mIsPlaying = true;

    std::cout << "Playing animation " << index << ": "
              << getAnimationName(index)
              << " (duration: " << mTotalDuration << "s)" << std::endl;
}

void AnimationManager::pause() {
    mIsPlaying = false;
}

void AnimationManager::resume() {
    if (mAnimator && mTotalDuration > 0.0f) {
        mIsPlaying = true;
    }
}

void AnimationManager::stop() {
    mIsPlaying = false;
    mCurrentTime = 0.0f;

    if (mAnimator && mCurrentIndex < getAnimationCount()) {
        mAnimator->applyAnimation(mCurrentIndex, 0.0f);
    }
}

void AnimationManager::seek(float time) {
    if (!mAnimator || mTotalDuration <= 0.0f) {
        return;
    }

    mCurrentTime = std::max(0.0f, std::min(time, mTotalDuration));

    if (mCurrentIndex < getAnimationCount()) {
        mAnimator->applyAnimation(mCurrentIndex, mCurrentTime);
    }

    updateCustomChannels(mCurrentTime);
}

void AnimationManager::setLooping(bool looping) {
    mIsLooping = looping;
}

void AnimationManager::addCustomChannel(const KeyframeChannel& channel) {
    mCustomChannels.push_back(channel);
}

void AnimationManager::removeCustomChannel(const std::string& name) {
    auto it = std::find_if(mCustomChannels.begin(), mCustomChannels.end(),
        [&name](const KeyframeChannel& ch) { return ch.name == name; });
    if (it != mCustomChannels.end()) {
        mCustomChannels.erase(it);
    }
}

void AnimationManager::clearCustomChannels() {
    mCustomChannels.clear();
}

KeyframeChannel* AnimationManager::getCustomChannel(const std::string& name) {
    auto it = std::find_if(mCustomChannels.begin(), mCustomChannels.end(),
        [&name](const KeyframeChannel& ch) { return ch.name == name; });
    if (it != mCustomChannels.end()) {
        return &(*it);
    }
    return nullptr;
}

void AnimationManager::updateCustomChannels(float time) {
    for (const auto& channel : mCustomChannels) {
        if (channel.keyframes.empty() || !channel.callback) {
            continue;
        }

        float value = evaluateChannel(channel, time);
        channel.callback(value);
    }
}

float AnimationManager::evaluateChannel(const KeyframeChannel& channel, float time) {
    if (channel.keyframes.empty()) {
        return 0.0f;
    }

    if (channel.keyframes.size() == 1) {
        return channel.keyframes[0].value;
    }

    const auto& kfs = channel.keyframes;

    if (time <= kfs.front().time) {
        return kfs.front().value;
    }
    if (time >= kfs.back().time) {
        return kfs.back().value;
    }

    for (size_t i = 0; i < kfs.size() - 1; ++i) {
        const auto& kf1 = kfs[i];
        const auto& kf2 = kfs[i + 1];

        if (time >= kf1.time && time <= kf2.time) {
            float t = 0.0f;
            float deltaTime = kf2.time - kf1.time;
            if (deltaTime > 0.0001f) {
                t = (time - kf1.time) / deltaTime;
            }
            return kf1.value + (kf2.value - kf1.value) * t;
        }
    }

    return kfs.back().value;
}

} 
