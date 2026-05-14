#pragma once

#include <string>
#include <vector>
#include <fstream>
#include <sstream>

namespace config {

struct MaterialPreset {
    std::string name;
    std::string description;
    float roughness = 0.5f;
    float metallic = 0.0f;
    float baseColorR = 0.8f;
    float baseColorG = 0.8f;
    float baseColorB = 0.8f;
};

struct IBLConfig {
    std::string iblPath;
    float intensity = 30000.0f;
    float rotation = 0.0f;
    float environmentIntensity = 1.0f;
};

struct SceneConfig {
    std::string name;
    std::string modelPath;
    IBLConfig ibl;
    MaterialPreset material;
    std::vector<MaterialPreset> customPresets;
};

class ConfigLoader {
public:
    ConfigLoader();
    ~ConfigLoader();

    bool saveMaterialPreset(const std::string& filePath, const MaterialPreset& preset);
    bool loadMaterialPreset(const std::string& filePath, MaterialPreset& preset);

    bool saveSceneConfig(const std::string& filePath, const SceneConfig& config);
    bool loadSceneConfig(const std::string& filePath, SceneConfig& config);

    bool savePresetList(const std::string& filePath, const std::vector<MaterialPreset>& presets);
    bool loadPresetList(const std::string& filePath, std::vector<MaterialPreset>& presets);

private:
    std::string escapeString(const std::string& str);
    std::string unescapeString(const std::string& str);

    void writeMaterialPreset(std::ofstream& file, const MaterialPreset& preset, int indent = 0);
    void writeIBLConfig(std::ofstream& file, const IBLConfig& ibl, int indent = 0);

    bool parseMaterialPreset(const std::string& content, MaterialPreset& preset);
    bool parseIBLConfig(const std::string& content, IBLConfig& ibl);

    std::string readFile(const std::string& filePath);
    bool writeFile(const std::string& filePath, const std::string& content);
};

} 
