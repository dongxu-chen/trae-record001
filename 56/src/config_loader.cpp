#include "config_loader.h"
#include <iostream>
#include <filesystem>
#include <algorithm>

namespace config {

ConfigLoader::ConfigLoader() {
}

ConfigLoader::~ConfigLoader() {
}

std::string ConfigLoader::escapeString(const std::string& str) {
    std::string result;
    result.reserve(str.size());
    for (char c : str) {
        switch (c) {
            case '"': result += "\\\""; break;
            case '\\': result += "\\\\"; break;
            case '\n': result += "\\n"; break;
            case '\r': result += "\\r"; break;
            case '\t': result += "\\t"; break;
            default: result += c;
        }
    }
    return result;
}

std::string ConfigLoader::unescapeString(const std::string& str) {
    std::string result;
    result.reserve(str.size());
    for (size_t i = 0; i < str.size(); ++i) {
        if (str[i] == '\\' && i + 1 < str.size()) {
            switch (str[i + 1]) {
                case '"': result += '"'; i++; break;
                case '\\': result += '\\'; i++; break;
                case 'n': result += '\n'; i++; break;
                case 'r': result += '\r'; i++; break;
                case 't': result += '\t'; i++; break;
                default: result += str[i];
            }
        } else {
            result += str[i];
        }
    }
    return result;
}

std::string ConfigLoader::readFile(const std::string& filePath) {
    std::ifstream file(filePath);
    if (!file.is_open()) {
        return "";
    }
    std::stringstream buffer;
    buffer << file.rdbuf();
    return buffer.str();
}

bool ConfigLoader::writeFile(const std::string& filePath, const std::string& content) {
    std::filesystem::path path(filePath);
    if (path.has_parent_path()) {
        std::filesystem::create_directories(path.parent_path());
    }

    std::ofstream file(filePath);
    if (!file.is_open()) {
        return false;
    }
    file << content;
    return true;
}

void ConfigLoader::writeMaterialPreset(std::ofstream& file, const MaterialPreset& preset, int indent) {
    std::string pad(indent * 2, ' ');
    file << pad << "{\n";
    file << pad << "  \"name\": \"" << escapeString(preset.name) << "\",\n";
    file << pad << "  \"description\": \"" << escapeString(preset.description) << "\",\n";
    file << pad << "  \"roughness\": " << preset.roughness << ",\n";
    file << pad << "  \"metallic\": " << preset.metallic << ",\n";
    file << pad << "  \"baseColor\": ["
         << preset.baseColorR << ", "
         << preset.baseColorG << ", "
         << preset.baseColorB << "]\n";
    file << pad << "}";
}

void ConfigLoader::writeIBLConfig(std::ofstream& file, const IBLConfig& ibl, int indent) {
    std::string pad(indent * 2, ' ');
    file << pad << "{\n";
    file << pad << "  \"iblPath\": \"" << escapeString(ibl.iblPath) << "\",\n";
    file << pad << "  \"intensity\": " << ibl.intensity << ",\n";
    file << pad << "  \"rotation\": " << ibl.rotation << ",\n";
    file << pad << "  \"environmentIntensity\": " << ibl.environmentIntensity << "\n";
    file << pad << "}";
}

bool ConfigLoader::saveMaterialPreset(const std::string& filePath, const MaterialPreset& preset) {
    std::ofstream file(filePath);
    if (!file.is_open()) {
        std::cerr << "Failed to open file for writing: " << filePath << std::endl;
        return false;
    }

    writeMaterialPreset(file, preset, 0);
    file << "\n";

    std::cout << "Material preset saved: " << filePath << std::endl;
    return true;
}

bool ConfigLoader::saveSceneConfig(const std::string& filePath, const SceneConfig& config) {
    std::ofstream file(filePath);
    if (!file.is_open()) {
        std::cerr << "Failed to open file for writing: " << filePath << std::endl;
        return false;
    }

    file << "{\n";
    file << "  \"name\": \"" << escapeString(config.name) << "\",\n";
    file << "  \"modelPath\": \"" << escapeString(config.modelPath) << "\",\n";
    file << "  \"ibl\": ";
    writeIBLConfig(file, config.ibl, 1);
    file << ",\n";
    file << "  \"material\": ";
    writeMaterialPreset(file, config.material, 1);
    file << ",\n";
    file << "  \"customPresets\": [\n";
    for (size_t i = 0; i < config.customPresets.size(); ++i) {
        writeMaterialPreset(file, config.customPresets[i], 2);
        if (i != config.customPresets.size() - 1) {
            file << ",";
        }
        file << "\n";
    }
    file << "  ]\n";
    file << "}\n";

    std::cout << "Scene config saved: " << filePath << std::endl;
    return true;
}

bool ConfigLoader::savePresetList(const std::string& filePath, const std::vector<MaterialPreset>& presets) {
    std::ofstream file(filePath);
    if (!file.is_open()) {
        std::cerr << "Failed to open file for writing: " << filePath << std::endl;
        return false;
    }

    file << "{\n";
    file << "  \"presets\": [\n";
    for (size_t i = 0; i < presets.size(); ++i) {
        writeMaterialPreset(file, presets[i], 2);
        if (i != presets.size() - 1) {
            file << ",";
        }
        file << "\n";
    }
    file << "  ]\n";
    file << "}\n";

    std::cout << "Preset list saved: " << filePath << std::endl;
    return true;
}

static std::string trim(const std::string& s) {
    size_t start = 0;
    while (start < s.size() && std::isspace(static_cast<unsigned char>(s[start]))) {
        start++;
    }
    size_t end = s.size();
    while (end > start && std::isspace(static_cast<unsigned char>(s[end - 1]))) {
        end--;
    }
    return s.substr(start, end - start);
}

static std::string extractStringValue(const std::string& content, const std::string& key) {
    std::string pattern = "\"" + key + "\"";
    size_t pos = content.find(pattern);
    if (pos == std::string::npos) {
        return "";
    }

    pos = content.find(':', pos);
    if (pos == std::string::npos) {
        return "";
    }

    pos = content.find('"', pos);
    if (pos == std::string::npos) {
        return "";
    }

    size_t start = pos + 1;
    size_t end = content.find('"', start);
    while (end != std::string::npos && content[end - 1] == '\\') {
        end = content.find('"', end + 1);
    }

    if (end == std::string::npos) {
        return "";
    }

    return content.substr(start, end - start);
}

static float extractFloatValue(const std::string& content, const std::string& key) {
    std::string pattern = "\"" + key + "\"";
    size_t pos = content.find(pattern);
    if (pos == std::string::npos) {
        return 0.0f;
    }

    pos = content.find(':', pos);
    if (pos == std::string::npos) {
        return 0.0f;
    }

    while (pos < content.size() && std::isspace(static_cast<unsigned char>(content[pos + 1]))) {
        pos++;
    }

    size_t start = pos + 1;
    size_t end = start;
    while (end < content.size() &&
           (std::isdigit(static_cast<unsigned char>(content[end])) ||
            content[end] == '.' ||
            content[end] == '-' ||
            content[end] == 'e' ||
            content[end] == 'E' ||
            content[end] == '+')) {
        end++;
    }

    std::string numStr = content.substr(start, end - start);
    try {
        return std::stof(numStr);
    } catch (...) {
        return 0.0f;
    }
}

static std::vector<float> extractFloatArray(const std::string& content, const std::string& key) {
    std::vector<float> result;
    std::string pattern = "\"" + key + "\"";
    size_t pos = content.find(pattern);
    if (pos == std::string::npos) {
        return result;
    }

    pos = content.find('[', pos);
    if (pos == std::string::npos) {
        return result;
    }

    size_t end = content.find(']', pos);
    if (end == std::string::npos) {
        return result;
    }

    std::string arrayContent = content.substr(pos + 1, end - pos - 1);
    size_t current = 0;
    while (current < arrayContent.size()) {
        while (current < arrayContent.size() &&
               std::isspace(static_cast<unsigned char>(arrayContent[current]))) {
            current++;
        }
        if (current >= arrayContent.size()) break;

        size_t numStart = current;
        while (current < arrayContent.size() &&
               (std::isdigit(static_cast<unsigned char>(arrayContent[current])) ||
                arrayContent[current] == '.' ||
                arrayContent[current] == '-' ||
                arrayContent[current] == 'e' ||
                arrayContent[current] == 'E' ||
                arrayContent[current] == '+')) {
            current++;
        }

        if (current > numStart) {
            std::string numStr = arrayContent.substr(numStart, current - numStart);
            try {
                result.push_back(std::stof(numStr));
            } catch (...) {
            }
        }

        while (current < arrayContent.size() &&
               arrayContent[current] != ',' &&
               !std::isdigit(static_cast<unsigned char>(arrayContent[current])) &&
               arrayContent[current] != '.' &&
               arrayContent[current] != '-') {
            current++;
        }
        if (current < arrayContent.size() && arrayContent[current] == ',') {
            current++;
        }
    }

    return result;
}

bool ConfigLoader::parseMaterialPreset(const std::string& content, MaterialPreset& preset) {
    preset.name = unescapeString(extractStringValue(content, "name"));
    preset.description = unescapeString(extractStringValue(content, "description"));
    preset.roughness = extractFloatValue(content, "roughness");
    preset.metallic = extractFloatValue(content, "metallic");

    std::vector<float> baseColor = extractFloatArray(content, "baseColor");
    if (baseColor.size() >= 3) {
        preset.baseColorR = baseColor[0];
        preset.baseColorG = baseColor[1];
        preset.baseColorB = baseColor[2];
    }

    return true;
}

bool ConfigLoader::parseIBLConfig(const std::string& content, IBLConfig& ibl) {
    ibl.iblPath = unescapeString(extractStringValue(content, "iblPath"));
    ibl.intensity = extractFloatValue(content, "intensity");
    ibl.rotation = extractFloatValue(content, "rotation");
    ibl.environmentIntensity = extractFloatValue(content, "environmentIntensity");
    return true;
}

bool ConfigLoader::loadMaterialPreset(const std::string& filePath, MaterialPreset& preset) {
    std::string content = readFile(filePath);
    if (content.empty()) {
        std::cerr << "Failed to read material preset: " << filePath << std::endl;
        return false;
    }

    bool result = parseMaterialPreset(content, preset);
    if (result) {
        std::cout << "Material preset loaded: " << filePath << std::endl;
    }
    return result;
}

bool ConfigLoader::loadSceneConfig(const std::string& filePath, SceneConfig& config) {
    std::string content = readFile(filePath);
    if (content.empty()) {
        std::cerr << "Failed to read scene config: " << filePath << std::endl;
        return false;
    }

    config.name = unescapeString(extractStringValue(content, "name"));
    config.modelPath = unescapeString(extractStringValue(content, "modelPath"));

    std::string iblPattern = "\"ibl\"";
    size_t iblStart = content.find(iblPattern);
    if (iblStart != std::string::npos) {
        size_t iblObjStart = content.find('{', iblStart);
        if (iblObjStart != std::string::npos) {
            int depth = 1;
            size_t iblObjEnd = iblObjStart + 1;
            while (iblObjEnd < content.size() && depth > 0) {
                if (content[iblObjEnd] == '{') depth++;
                else if (content[iblObjEnd] == '}') depth--;
                iblObjEnd++;
            }
            if (depth == 0) {
                std::string iblContent = content.substr(iblObjStart, iblObjEnd - iblObjStart);
                parseIBLConfig(iblContent, config.ibl);
            }
        }
    }

    std::string matPattern = "\"material\"";
    size_t matStart = content.find(matPattern);
    if (matStart != std::string::npos) {
        size_t matObjStart = content.find('{', matStart);
        if (matObjStart != std::string::npos) {
            int depth = 1;
            size_t matObjEnd = matObjStart + 1;
            while (matObjEnd < content.size() && depth > 0) {
                if (content[matObjEnd] == '{') depth++;
                else if (content[matObjEnd] == '}') depth--;
                matObjEnd++;
            }
            if (depth == 0) {
                std::string matContent = content.substr(matObjStart, matObjEnd - matObjStart);
                parseMaterialPreset(matContent, config.material);
            }
        }
    }

    std::cout << "Scene config loaded: " << filePath << std::endl;
    return true;
}

bool ConfigLoader::loadPresetList(const std::string& filePath, std::vector<MaterialPreset>& presets) {
    std::string content = readFile(filePath);
    if (content.empty()) {
        std::cerr << "Failed to read preset list: " << filePath << std::endl;
        return false;
    }

    std::string pattern = "\"presets\"";
    size_t start = content.find(pattern);
    if (start == std::string::npos) {
        start = 0;
    }

    size_t arrStart = content.find('[', start);
    if (arrStart == std::string::npos) {
        return false;
    }

    size_t pos = arrStart + 1;
    while (pos < content.size()) {
        while (pos < content.size() && std::isspace(static_cast<unsigned char>(content[pos]))) {
            pos++;
        }

        if (content[pos] == '{') {
            int depth = 1;
            size_t objStart = pos;
            pos++;
            while (pos < content.size() && depth > 0) {
                if (content[pos] == '{') depth++;
                else if (content[pos] == '}') depth--;
                pos++;
            }

            if (depth == 0) {
                std::string objContent = content.substr(objStart, pos - objStart);
                MaterialPreset preset;
                if (parseMaterialPreset(objContent, preset)) {
                    presets.push_back(preset);
                }
            }
        } else if (content[pos] == ']') {
            break;
        } else {
            pos++;
        }
    }

    std::cout << "Preset list loaded: " << filePath << " (" << presets.size() << " presets)" << std::endl;
    return true;
}

} 
