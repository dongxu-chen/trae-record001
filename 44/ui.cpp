#include "ui.h"
#include <imgui.h>
#include <imgui_impl_glfw.h>
#include <imgui_impl_opengl3.h>
#include <iostream>

UISettings::UISettings()
    : showUI(true),
      showSnow(true),
      showRain(false),
      showLeaf(false),
      showHail(false),
      showDust(false),
      currentSeason(WINTER),
      groundType(FLAT_GROUND),
      windStrength(3.0f),
      windTurbulence(0.8f),
      windDirection(glm::vec3(1.0f, 0.0f, 0.3f)),
      precipitationMultiplier(1.0f),
      gravityMultiplier(1.0f),
      collisionEnabled(true),
      restitutionOverride(0.5f),
      frictionOverride(0.3f),
      heightMapScale(1.0f),
      heightMapFreq(0.3f)
{}

UIManager::UIManager() : initialized(false) {}

UIManager::~UIManager() {
    if (initialized) {
        shutdown();
    }
}

void UIManager::init(GLFWwindow* window) {
    if (initialized) return;
    
    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImGuiIO& io = ImGui::GetIO(); (void)io;
    io.ConfigFlags |= ImGuiConfigFlags_NavEnableKeyboard;
    
    ImGui::StyleColorsDark();
    
    ImGui_ImplGlfw_InitForOpenGL(window, true);
    ImGui_ImplOpenGL3_Init("#version 330");
    
    initialized = true;
}

void UIManager::shutdown() {
    if (!initialized) return;
    
    ImGui_ImplOpenGL3_Shutdown();
    ImGui_ImplGlfw_Shutdown();
    ImGui::DestroyContext();
    
    initialized = false;
}

void UIManager::newFrame() {
    if (!initialized) return;
    
    ImGui_ImplOpenGL3_NewFrame();
    ImGui_ImplGlfw_NewFrame();
    ImGui::NewFrame();
}

void UIManager::render() {
    if (!initialized) return;
    
    ImGui::Render();
    ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
}

const char* UIManager::getSeasonName(Season season) {
    switch (season) {
        case WINTER: return "Winter";
        case SPRING: return "Spring";
        case SUMMER: return "Summer";
        case AUTUMN: return "Autumn";
        default: return "Unknown";
    }
}

const char* UIManager::getParticleTypeName(ParticleType type) {
    switch (type) {
        case SNOW: return "Snow";
        case RAIN: return "Rain";
        case LEAF: return "Leaf";
        case HAIL: return "Hail";
        case DUST: return "Dust";
        default: return "Unknown";
    }
}

const char* UIManager::getGroundTypeName(GroundType type) {
    switch (type) {
        case FLAT_GROUND: return "Flat Ground";
        case HEIGHT_MAP: return "Height Map";
        case SPHERE: return "Sphere";
        case BOX: return "Box";
        default: return "Unknown";
    }
}

void UIManager::drawWeatherPanel(UISettings& settings, const std::vector<ParticleSystem*>& systems) {
    if (ImGui::CollapsingHeader("Weather", ImGuiTreeNodeFlags_DefaultOpen)) {
        ImGui::Text("Active Season: %s", getSeasonName(settings.currentSeason));
        ImGui::Spacing();
        
        if (ImGui::Button("Winter")) {
            settings.currentSeason = WINTER;
            settings.showSnow = true;
            settings.showRain = false;
            settings.showLeaf = false;
            settings.showHail = false;
            settings.showDust = false;
            for (auto* sys : systems) sys->setSeason(WINTER);
        }
        ImGui::SameLine();
        if (ImGui::Button("Spring")) {
            settings.currentSeason = SPRING;
            settings.showSnow = false;
            settings.showRain = true;
            settings.showLeaf = false;
            settings.showHail = false;
            settings.showDust = true;
            for (auto* sys : systems) sys->setSeason(SPRING);
        }
        ImGui::SameLine();
        if (ImGui::Button("Summer")) {
            settings.currentSeason = SUMMER;
            settings.showSnow = false;
            settings.showRain = true;
            settings.showLeaf = false;
            settings.showHail = false;
            settings.showDust = true;
            for (auto* sys : systems) sys->setSeason(SUMMER);
        }
        ImGui::SameLine();
        if (ImGui::Button("Autumn")) {
            settings.currentSeason = AUTUMN;
            settings.showSnow = false;
            settings.showRain = false;
            settings.showLeaf = true;
            settings.showHail = false;
            settings.showDust = false;
            for (auto* sys : systems) sys->setSeason(AUTUMN);
        }
        
        ImGui::Spacing();
        ImGui::Separator();
        ImGui::Spacing();
        
        ImGui::Checkbox("Snow", &settings.showSnow);
        ImGui::Checkbox("Rain", &settings.showRain);
        ImGui::Checkbox("Leaves", &settings.showLeaf);
        ImGui::Checkbox("Hail", &settings.showHail);
        ImGui::Checkbox("Dust", &settings.showDust);
        
        ImGui::Spacing();
        ImGui::SliderFloat("Precipitation Rate", &settings.precipitationMultiplier, 0.1f, 5.0f, "%.1fx");
        
        ImGui::Spacing();
        if (ImGui::Button("Clear All")) {
            settings.showSnow = false;
            settings.showRain = false;
            settings.showLeaf = false;
            settings.showHail = false;
            settings.showDust = false;
        }
    }
}

void UIManager::drawWindPanel(UISettings& settings, WindField& wind) {
    if (ImGui::CollapsingHeader("Wind Field", ImGuiTreeNodeFlags_DefaultOpen)) {
        bool changed = false;
        
        changed |= ImGui::SliderFloat("Wind Strength", &settings.windStrength, 0.0f, 20.0f, "%.1f m/s");
        changed |= ImGui::SliderFloat("Turbulence", &settings.windTurbulence, 0.0f, 2.0f, "%.2f");
        
        ImGui::Spacing();
        ImGui::Text("Wind Direction:");
        changed |= ImGui::SliderFloat("X", &settings.windDirection.x, -1.0f, 1.0f, "%.2f");
        changed |= ImGui::SliderFloat("Y", &settings.windDirection.y, -0.5f, 0.5f, "%.2f");
        changed |= ImGui::SliderFloat("Z", &settings.windDirection.z, -1.0f, 1.0f, "%.2f");
        
        if (ImGui::Button("Reset Wind")) {
            settings.windStrength = 3.0f;
            settings.windTurbulence = 0.8f;
            settings.windDirection = glm::vec3(1.0f, 0.0f, 0.3f);
            changed = true;
        }
        
        if (changed) {
            glm::vec3 dir = glm::normalize(settings.windDirection);
            wind.setBaseDirection(dir);
            wind.setStrength(settings.windStrength);
            wind.setTurbulence(settings.windTurbulence);
        }
        
        ImGui::Spacing();
        ImGui::Text("Wind Speed: %.1f m/s", settings.windStrength);
        ImGui::Text("Beaufort Scale: ");
        ImGui::SameLine();
        if (settings.windStrength < 0.3f) ImGui::TextColored(ImVec4(0.5f, 0.5f, 1.0f, 1.0f), "Calm");
        else if (settings.windStrength < 1.6f) ImGui::TextColored(ImVec4(0.4f, 0.6f, 1.0f, 1.0f), "Light Air");
        else if (settings.windStrength < 3.4f) ImGui::TextColored(ImVec4(0.3f, 0.7f, 1.0f, 1.0f), "Light Breeze");
        else if (settings.windStrength < 5.5f) ImGui::TextColored(ImVec4(0.2f, 0.8f, 1.0f, 1.0f), "Gentle Breeze");
        else if (settings.windStrength < 8.0f) ImGui::TextColored(ImVec4(0.1f, 0.9f, 0.8f, 1.0f), "Moderate Breeze");
        else if (settings.windStrength < 10.8f) ImGui::TextColored(ImVec4(0.0f, 1.0f, 0.5f, 1.0f), "Fresh Breeze");
        else if (settings.windStrength < 13.9f) ImGui::TextColored(ImVec4(1.0f, 0.8f, 0.0f, 1.0f), "Strong Breeze");
        else ImGui::TextColored(ImVec4(1.0f, 0.3f, 0.0f, 1.0f), "High Wind");
    }
}

void UIManager::drawPhysicsPanel(UISettings& settings) {
    if (ImGui::CollapsingHeader("Physics")) {
        ImGui::Checkbox("Collision Detection", &settings.collisionEnabled);
        
        ImGui::Spacing();
        ImGui::SliderFloat("Gravity Scale", &settings.gravityMultiplier, 0.1f, 3.0f, "%.2fx");
        
        ImGui::Spacing();
        ImGui::Text("Collision Response:");
        ImGui::SliderFloat("Restitution", &settings.restitutionOverride, 0.0f, 1.0f, "%.2f");
        ImGui::SliderFloat("Friction", &settings.frictionOverride, 0.0f, 1.0f, "%.2f");
        
        ImGui::Spacing();
        ImGui::Text("Hint: Lower restitution = more damping");
    }
}

void UIManager::drawTerrainPanel(UISettings& settings, CollisionSystem& collision) {
    if (ImGui::CollapsingHeader("Terrain")) {
        bool terrainChanged = false;
        
        const char* groundTypes[] = {"Flat Ground", "Height Map", "Sphere", "Box"};
        int currentType = static_cast<int>(settings.groundType);
        
        if (ImGui::Combo("Ground Type", &currentType, groundTypes, IM_ARRAYSIZE(groundTypes))) {
            settings.groundType = static_cast<GroundType>(currentType);
            collision.setGroundType(settings.groundType);
            terrainChanged = true;
        }
        
        ImGui::Spacing();
        
        if (settings.groundType == FLAT_GROUND) {
            static float groundY = 0.0f;
            if (ImGui::SliderFloat("Ground Y", &groundY, -5.0f, 5.0f, "%.1f")) {
                collision.setFlatGroundY(groundY);
            }
        }
        else if (settings.groundType == HEIGHT_MAP) {
            if (ImGui::SliderFloat("Height Scale", &settings.heightMapScale, 0.1f, 5.0f, "%.1f")) {
                collision.setHeightMapParams(settings.heightMapScale, settings.heightMapFreq);
            }
            if (ImGui::SliderFloat("Frequency", &settings.heightMapFreq, 0.1f, 2.0f, "%.2f")) {
                collision.setHeightMapParams(settings.heightMapScale, settings.heightMapFreq);
            }
        }
        else if (settings.groundType == SPHERE) {
            static glm::vec3 sphereCenter(0.0f, 2.5f, 0.0f);
            static float sphereRadius = 5.0f;
            
            bool changed = false;
            changed |= ImGui::SliderFloat("Sphere Radius", &sphereRadius, 1.0f, 10.0f, "%.1f");
            changed |= ImGui::SliderFloat3("Sphere Center", &sphereCenter.x, -10.0f, 10.0f, "%.1f");
            
            if (changed) {
                collision.setSphere(sphereCenter, sphereRadius);
            }
        }
        else if (settings.groundType == BOX) {
            static glm::vec3 boxMin(-3.0f, 0.0f, -3.0f);
            static glm::vec3 boxMax(3.0f, 2.0f, 3.0f);
            
            bool changed = false;
            changed |= ImGui::SliderFloat3("Box Min", &boxMin.x, -10.0f, 0.0f, "%.1f");
            changed |= ImGui::SliderFloat3("Box Max", &boxMax.x, 0.0f, 10.0f, "%.1f");
            
            if (changed) {
                collision.setBox(boxMin, boxMax);
            }
        }
    }
}

void UIManager::drawStatsPanel(const std::vector<ParticleSystem*>& systems) {
    if (ImGui::CollapsingHeader("Stats")) {
        unsigned int totalParticles = 0;
        for (const auto* sys : systems) {
            totalParticles += sys->getActiveCount();
        }
        
        ImGui::Text("Total Active Particles: %u", totalParticles);
        ImGui::Spacing();
        
        for (const auto* sys : systems) {
            ImGui::Text("%s: %u active", 
                getParticleTypeName(sys->getType()),
                sys->getActiveCount());
        }
        
        ImGui::Spacing();
        ImGui::Text("Controls:");
        ImGui::BulletText("WASD - Move Camera");
        ImGui::BulletText("Mouse - Look Around");
        ImGui::BulletText("Scroll - Zoom");
        ImGui::BulletText("Tab - Toggle UI");
        ImGui::BulletText("ESC - Exit");
    }
}

void UIManager::buildUI(UISettings& settings,
                        const std::vector<ParticleSystem*>& systems,
                        WindField& wind,
                        CollisionSystem& collision) {
    if (!settings.showUI) return;
    
    ImGui::SetNextWindowPos(ImVec2(10, 10), ImGuiCond_FirstUseEver);
    ImGui::SetNextWindowSize(ImVec2(350, 0), ImGuiCond_FirstUseEver);
    
    ImGui::Begin("Weather Particle System", nullptr, 
        ImGuiWindowFlags_NoCollapse | 
        ImGuiWindowFlags_AlwaysAutoResize);
    
    drawWeatherPanel(settings, systems);
    drawWindPanel(settings, wind);
    drawPhysicsPanel(settings);
    drawTerrainPanel(settings, collision);
    drawStatsPanel(systems);
    
    ImGui::End();
}
