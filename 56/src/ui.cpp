#include "ui.h"
#include "animation.h"
#include <imgui.h>
#include <filagui/ImGuiHelper.h>
#include <iostream>

namespace ui {

UIManager::UIManager(filament::Engine* engine)
    : mEngine(engine) {
}

UIManager::~UIManager() {
}

void UIManager::initialize(utils::Entity window) {
    mInitialized = true;
}

void UIManager::syncAnimationState(const animation::AnimationManager* animMgr) {
    if (!animMgr) {
        return;
    }

    mState.animation.isPlaying = animMgr->isPlaying();
    mState.animation.isLooping = animMgr->isLooping();
    mState.animation.currentTime = animMgr->getCurrentTime();
    mState.animation.currentAnimationIndex = animMgr->getCurrentAnimationIndex();

    size_t animCount = animMgr->getAnimationCount();
    if (mState.animation.animationNames.size() != animCount) {
        mState.animation.animationNames.clear();
        for (size_t i = 0; i < animCount; ++i) {
            mState.animation.animationNames.push_back(animMgr->getAnimationName(i));
        }
    }
    mState.animation.animationCount = animCount;

    if (animCount > 0) {
        mState.animation.totalDuration = animMgr->getAnimationDuration(
            animMgr->getCurrentAnimationIndex()
        );
    }
}

void UIManager::updateCustomChannelsFromUI() {
    if (!mAnimationManager) {
        return;
    }

    mAnimationManager->clearCustomChannels();

    for (const auto& uiChannel : mState.animation.customChannels) {
        if (!uiChannel.enabled || uiChannel.keyframes.empty()) {
            continue;
        }

        animation::KeyframeChannel channel;
        channel.name = uiChannel.name;

        for (const auto& uiKf : uiChannel.keyframes) {
            animation::Keyframe kf;
            kf.time = uiKf.time;
            kf.value = uiKf.value;
            channel.keyframes.push_back(kf);
        }

        if (uiChannel.name == "Roughness") {
            channel.callback = [this](float value) {
                mState.materialParams.roughness = std::max(0.001f, std::min(1.0f, value));
                mMaterialParamsChanged = true;
            };
        } else if (uiChannel.name == "Metallic") {
            channel.callback = [this](float value) {
                mState.materialParams.metallic = std::max(0.0f, std::min(1.0f, value));
                mMaterialParamsChanged = true;
            };
        }

        mAnimationManager->addCustomChannel(channel);
    }
}

void UIManager::renderAnimationPanel() {
    if (ImGui::CollapsingHeader("Animation", ImGuiTreeNodeFlags_DefaultOpen)) {
        ImGui::Text("Animations available: %zu", mState.animation.animationCount);

        if (mState.animation.animationCount > 0) {
            std::vector<const char*> animNames;
            for (const auto& name : mState.animation.animationNames) {
                animNames.push_back(name.c_str());
            }

            if (animNames.empty()) {
                animNames.push_back("Default");
            }

            int prevSelection = mState.animation.selectedAnimation;
            if (ImGui::Combo("Animation", &mState.animation.selectedAnimation,
                             animNames.data(), (int)animNames.size())) {
                if (mState.animation.selectedAnimation != prevSelection) {
                    mAnimationIndexChanged = true;
                }
            }

            ImGui::Spacing();

            if (ImGui::Button("Play")) {
                mPlayRequested = true;
            }
            ImGui::SameLine();
            if (ImGui::Button("Pause")) {
                mPauseRequested = true;
            }
            ImGui::SameLine();
            if (ImGui::Button("Stop")) {
                mStopRequested = true;
            }

            ImGui::Spacing();

            if (ImGui::Checkbox("Looping", &mState.animation.isLooping)) {
            }

            ImGui::Spacing();

            float duration = mState.animation.totalDuration;
            if (duration > 0.0f) {
                float currentTime = mState.animation.currentTime;
                ImGui::ProgressBar(currentTime / duration, ImVec2(-1, 0),
                    std::to_string(currentTime).c_str());

                if (ImGui::SliderFloat("Timeline", &currentTime, 0.0f, duration, "%.2fs")) {
                    mState.animation.currentTime = currentTime;
                    mSeekRequested = true;
                }
            }

            ImGui::Spacing();

            if (ImGui::Button("Keyframe Editor")) {
                mState.animation.showKeyframeEditor = !mState.animation.showKeyframeEditor;
            }
        } else {
            ImGui::TextColored(ImVec4(1.0f, 0.8f, 0.4f, 1.0f),
                "No animations in model.");
            ImGui::Text("Load an animated glTF file.");
        }
    }

    if (mState.animation.showKeyframeEditor) {
        renderKeyframeEditor();
    }
}

void UIManager::renderKeyframeEditor() {
    ImGui::SetNextWindowSize(ImVec2(500, 400), ImGuiCond_FirstUseEver);
    if (ImGui::Begin("Keyframe Editor", &mState.animation.showKeyframeEditor)) {

        if (ImGui::Button("Add Channel: Roughness")) {
            bool exists = false;
            for (const auto& ch : mState.animation.customChannels) {
                if (ch.name == "Roughness") { exists = true; break; }
            }
            if (!exists) {
                ChannelData ch;
                ch.name = "Roughness";
                ch.enabled = true;
                ch.keyframes.push_back({0.0f, 0.5f});
                ch.keyframes.push_back({1.0f, 0.5f});
                mState.animation.customChannels.push_back(ch);
            }
        }
        ImGui::SameLine();
        if (ImGui::Button("Add Channel: Metallic")) {
            bool exists = false;
            for (const auto& ch : mState.animation.customChannels) {
                if (ch.name == "Metallic") { exists = true; break; }
            }
            if (!exists) {
                ChannelData ch;
                ch.name = "Metallic";
                ch.enabled = true;
                ch.keyframes.push_back({0.0f, 0.0f});
                ch.keyframes.push_back({1.0f, 0.0f});
                mState.animation.customChannels.push_back(ch);
            }
        }

        ImGui::Separator();

        for (size_t i = 0; i < mState.animation.customChannels.size(); ++i) {
            auto& channel = mState.animation.customChannels[i];

            ImGui::PushID((int)i);

            bool enabled = channel.enabled;
            if (ImGui::Checkbox(channel.name.c_str(), &enabled)) {
                channel.enabled = enabled;
            }
            ImGui::SameLine();
            if (ImGui::SmallButton("Remove")) {
                mState.animation.customChannels.erase(mState.animation.customChannels.begin() + i);
                i--;
                ImGui::PopID();
                continue;
            }

            if (channel.enabled) {
                ImGui::Indent();

                if (ImGui::Button("Add Keyframe")) {
                    KeyframeData kf;
                    kf.time = mState.animation.currentTime;
                    kf.value = 0.5f;
                    if (channel.name == "Roughness") {
                        kf.value = mState.materialParams.roughness;
                    } else if (channel.name == "Metallic") {
                        kf.value = mState.materialParams.metallic;
                    }
                    channel.keyframes.push_back(kf);
                }

                ImGui::Spacing();

                for (size_t j = 0; j < channel.keyframes.size(); ++j) {
                    auto& kf = channel.keyframes[j];
                    ImGui::PushID((int)j);

                    ImGui::Text("K%d:", (int)j);
                    ImGui::SameLine();
                    ImGui::SetNextItemWidth(80);
                    ImGui::InputFloat("Time", &kf.time, 0.1f);
                    ImGui::SameLine();
                    ImGui::SetNextItemWidth(80);
                    ImGui::SliderFloat("Value", &kf.value, 0.0f, 1.0f, "%.2f");
                    ImGui::SameLine();
                    if (ImGui::SmallButton("X")) {
                        if (channel.keyframes.size() > 2) {
                            channel.keyframes.erase(channel.keyframes.begin() + j);
                            j--;
                        }
                    }

                    ImGui::PopID();
                }

                if (ImGui::Button("Apply to Animation")) {
                    updateCustomChannelsFromUI();
                }

                ImGui::Unindent();
            }

            ImGui::PopID();
            ImGui::Spacing();
        }
    }
    ImGui::End();
}

void UIManager::renderConfigPanel() {
    if (ImGui::CollapsingHeader("Config / Presets", ImGuiTreeNodeFlags_DefaultOpen)) {
        ImGui::Checkbox("Show Config Panel", &mState.config.showConfigPanel);

        if (ImGui::Button("Save Current Material as Preset")) {
            mState.config.saveRequested = true;
        }

        ImGui::SameLine();
        if (ImGui::Button("Load Preset")) {
            mState.config.loadRequested = true;
        }
    }

    if (mState.config.showConfigPanel) {
        ImGui::SetNextWindowSize(ImVec2(450, 350), ImGuiCond_FirstUseEver);
        if (ImGui::Begin("Preset Manager", &mState.config.showConfigPanel)) {

            static char presetName[128] = "MyPreset";
            static char presetDesc[256] = "Custom material preset";
            static char savePath[512] = "presets/mypreset.json";

            ImGui::Text("Save Preset:");
            ImGui::InputText("Preset Name", presetName, sizeof(presetName));
            ImGui::InputText("Description", presetDesc, sizeof(presetDesc));
            ImGui::InputText("File Path", savePath, sizeof(savePath));

            if (ImGui::Button("Save Preset", ImVec2(-1, 0))) {
                mState.config.presetName = presetName;
                mState.config.presetDescription = presetDesc;
                mState.config.savePath = savePath;
                mState.config.saveRequested = true;
            }

            ImGui::Separator();

            ImGui::Text("Load Preset:");
            static char loadPathBuf[512] = "presets/mypreset.json";
            ImGui::InputText("Load Path", loadPathBuf, sizeof(loadPathBuf));

            if (ImGui::Button("Load Preset", ImVec2(-1, 0))) {
                mState.config.loadPath = loadPathBuf;
                mState.config.loadRequested = true;
            }

            ImGui::Separator();

            ImGui::Text("Current Values:");
            ImGui::Text("  Roughness: %.3f", mState.materialParams.roughness);
            ImGui::Text("  Metallic:  %.3f", mState.materialParams.metallic);
            ImGui::Text("  Color:     (%.2f, %.2f, %.2f)",
                mState.materialParams.baseColorR,
                mState.materialParams.baseColorG,
                mState.materialParams.baseColorB);
        }
        ImGui::End();
    }
}

void UIManager::render(filament::Renderer* renderer, filament::SwapChain* swapChain) {
    if (!mInitialized) {
        return;
    }

    ImGui::NewFrame();

    ImGui::SetNextWindowPos(ImVec2(10, 10), ImGuiCond_FirstUseEver);
    ImGui::SetNextWindowSize(ImVec2(380, 550), ImGuiCond_FirstUseEver);

    if (ImGui::Begin("Material Previewer", nullptr, ImGuiWindowFlags_AlwaysAutoResize)) {

        if (ImGui::CollapsingHeader("Model Loading", ImGuiTreeNodeFlags_DefaultOpen)) {
            ImGui::Text("Model Path:");
            static char modelPathBuffer[512] = "";
            ImGui::InputText("##modelPath", modelPathBuffer, sizeof(modelPathBuffer));

            if (ImGui::Button("Load Model", ImVec2(-1, 0))) {
                mState.modelPath = modelPathBuffer;
                mModelLoadRequested = true;
            }

            ImGui::SameLine();
            if (ImGui::Button("Clear Model")) {
                mState.modelPath = "";
            }
        }

        if (ImGui::CollapsingHeader("IBL Environment", ImGuiTreeNodeFlags_DefaultOpen)) {
            ImGui::Text("IBL Path:");
            static char iblPathBuffer[512] = "";
            ImGui::InputText("##iblPath", iblPathBuffer, sizeof(iblPathBuffer));

            if (ImGui::Button("Load IBL", ImVec2(-1, 0))) {
                mState.iblPath = iblPathBuffer;
                mIBLLoadRequested = true;
            }

            ImGui::Separator();

            if (ImGui::SliderFloat("IBL Intensity", &mState.iblIntensity, 0.0f, 100000.0f, "%.0f")) {
                mIBLParamsChanged = true;
            }

            if (ImGui::SliderFloat("IBL Rotation", &mState.iblRotation, -180.0f, 180.0f, "%.1f deg")) {
                mIBLParamsChanged = true;
            }

            if (ImGui::SliderFloat("Env Intensity", &mState.envIntensity, 0.0f, 5.0f, "%.2f")) {
                mIBLParamsChanged = true;
            }
        }

        if (ImGui::CollapsingHeader("Material Parameters", ImGuiTreeNodeFlags_DefaultOpen)) {
            ImGui::Text("PBR Material Properties");
            ImGui::Separator();

            if (ImGui::SliderFloat("Roughness", &mState.materialParams.roughness, 0.0f, 1.0f, "%.2f")) {
                mMaterialParamsChanged = true;
            }
            ImGui::SameLine();
            if (ImGui::SmallButton("Reset R")) {
                mState.materialParams.roughness = 0.5f;
                mMaterialParamsChanged = true;
            }

            if (ImGui::SliderFloat("Metallic", &mState.materialParams.metallic, 0.0f, 1.0f, "%.2f")) {
                mMaterialParamsChanged = true;
            }
            ImGui::SameLine();
            if (ImGui::SmallButton("Reset M")) {
                mState.materialParams.metallic = 0.0f;
                mMaterialParamsChanged = true;
            }

            ImGui::Separator();

            float color[3] = {
                mState.materialParams.baseColorR,
                mState.materialParams.baseColorG,
                mState.materialParams.baseColorB
            };

            if (ImGui::ColorEdit3("Base Color", color)) {
                mState.materialParams.baseColorR = color[0];
                mState.materialParams.baseColorG = color[1];
                mState.materialParams.baseColorB = color[2];
                mMaterialParamsChanged = true;
            }

            ImGui::Separator();

            ImGui::Text("Presets:");
            if (ImGui::SmallButton("Plastic")) {
                mState.materialParams.roughness = 0.4f;
                mState.materialParams.metallic = 0.0f;
                mMaterialParamsChanged = true;
            }
            ImGui::SameLine();
            if (ImGui::SmallButton("Rubber")) {
                mState.materialParams.roughness = 0.9f;
                mState.materialParams.metallic = 0.0f;
                mMaterialParamsChanged = true;
            }
            ImGui::SameLine();
            if (ImGui::SmallButton("Metal")) {
                mState.materialParams.roughness = 0.2f;
                mState.materialParams.metallic = 1.0f;
                mMaterialParamsChanged = true;
            }

            if (ImGui::SmallButton("Chrome")) {
                mState.materialParams.roughness = 0.05f;
                mState.materialParams.metallic = 1.0f;
                mMaterialParamsChanged = true;
            }
            ImGui::SameLine();
            if (ImGui::SmallButton("Brushed")) {
                mState.materialParams.roughness = 0.6f;
                mState.materialParams.metallic = 1.0f;
                mMaterialParamsChanged = true;
            }
            ImGui::SameLine();
            if (ImGui::SmallButton("Glass")) {
                mState.materialParams.roughness = 0.0f;
                mState.materialParams.metallic = 0.0f;
                mMaterialParamsChanged = true;
            }
        }

        renderAnimationPanel();

        renderConfigPanel();

        if (ImGui::CollapsingHeader("Info", ImGuiTreeNodeFlags_None)) {
            ImGui::Text("Roughness: %.3f", mState.materialParams.roughness);
            ImGui::Text("Metallic:  %.3f", mState.materialParams.metallic);
            ImGui::Text("Color:     (%.2f, %.2f, %.2f)",
                mState.materialParams.baseColorR,
                mState.materialParams.baseColorG,
                mState.materialParams.baseColorB
            );
            ImGui::Separator();
            ImGui::Text("IBL Intensity: %.0f", mState.iblIntensity);
            ImGui::Text("IBL Rotation:  %.1f deg", mState.iblRotation);
            ImGui::Text("Env Intensity: %.2f", mState.envIntensity);
            ImGui::Separator();
            ImGui::Text("Animations: %zu", mState.animation.animationCount);
            ImGui::Text("Playing: %s", mState.animation.isPlaying ? "Yes" : "No");
            ImGui::Text("Time: %.2fs / %.2fs",
                mState.animation.currentTime,
                mState.animation.totalDuration);
        }

        ImGui::Checkbox("Show Demo Window", &mState.showDemoWindow);

        if (mState.showDemoWindow) {
            ImGui::ShowDemoWindow(&mState.showDemoWindow);
        }
    }

    ImGui::End();

    ImGui::Render();

    if (ImGui::GetDrawData()) {
        filagui::ImGuiHelper imguiHelper(mEngine);
        imguiHelper.render(renderer, swapChain, ImGui::GetDrawData());
    }
}

void UIManager::updateUIState() {
}

} 
