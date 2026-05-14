#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/type_ptr.hpp>

#include <iostream>
#include <vector>

#include "shader.h"
#include "camera.h"
#include "particle.h"
#include "wind.h"
#include "collision.h"
#include "ui.h"

void framebuffer_size_callback(GLFWwindow* window, int width, int height);
void mouse_callback(GLFWwindow* window, double xpos, double ypos);
void scroll_callback(GLFWwindow* window, double xoffset, double yoffset);
void key_callback(GLFWwindow* window, int key, int scancode, int action, int mods);
void processInput(GLFWwindow* window);

const unsigned int SCR_WIDTH = 1280;
const unsigned int SCR_HEIGHT = 720;

Camera camera(glm::vec3(0.0f, 8.0f, 25.0f));
float lastX = SCR_WIDTH / 2.0f;
float lastY = SCR_HEIGHT / 2.0f;
bool firstMouse = true;
bool mouseEnabled = true;

float deltaTime = 0.0f;
float lastFrame = 0.0f;

UIManager uiManager;
UISettings uiSettings;

int main()
{
    glfwInit();
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

#ifdef __APPLE__
    glfwWindowHint(GLFW_OPENGL_FORWARD_COMPAT, GL_TRUE);
#endif

    GLFWwindow* window = glfwCreateWindow(SCR_WIDTH, SCR_HEIGHT, "Weather Particle System", NULL, NULL);
    if (window == NULL)
    {
        std::cout << "Failed to create GLFW window" << std::endl;
        glfwTerminate();
        return -1;
    }
    glfwMakeContextCurrent(window);
    glfwSetFramebufferSizeCallback(window, framebuffer_size_callback);
    glfwSetCursorPosCallback(window, mouse_callback);
    glfwSetScrollCallback(window, scroll_callback);
    glfwSetKeyCallback(window, key_callback);

    glfwSetInputMode(window, GLFW_CURSOR, GLFW_CURSOR_DISABLED);

    if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress))
    {
        std::cout << "Failed to initialize GLAD" << std::endl;
        return -1;
    }

    glEnable(GL_DEPTH_TEST);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glEnable(GL_PROGRAM_POINT_SIZE);

    uiManager.init(window);

    Shader particleShader("shaders/particle.vs", "shaders/particle.fs");

    glm::vec3 spawnArea(40.0f, 15.0f, 40.0f);
    
    ParticleSystem snowSystem(SNOW, 15000, spawnArea);
    ParticleSystem rainSystem(RAIN, 25000, spawnArea);
    ParticleSystem leafSystem(LEAF, 5000, spawnArea);
    ParticleSystem hailSystem(HAIL, 10000, spawnArea);
    ParticleSystem dustSystem(DUST, 8000, spawnArea);
    
    std::vector<ParticleSystem*> particleSystems = {
        &snowSystem, &rainSystem, &leafSystem, &hailSystem, &dustSystem
    };
    
    for (auto* sys : particleSystems) {
        sys->setSeason(WINTER);
        sys->setCollisionEnabled(true);
    }

    WindField wind(glm::vec3(1.0f, 0.0f, 0.3f), 3.0f, 0.8f);
    CollisionSystem collision;

    float baseSnowRate = 200.0f;
    float baseRainRate = 500.0f;
    float baseLeafRate = 50.0f;
    float baseHailRate = 300.0f;
    float baseDustRate = 150.0f;

    while (!glfwWindowShouldClose(window))
    {
        float currentFrame = static_cast<float>(glfwGetTime());
        deltaTime = currentFrame - lastFrame;
        if (deltaTime > 0.1f) deltaTime = 0.1f;
        lastFrame = currentFrame;

        processInput(window);

        uiManager.newFrame();

        snowSystem.setSpawnRate(uiSettings.showSnow ? baseSnowRate * uiSettings.precipitationMultiplier : 0.0f);
        rainSystem.setSpawnRate(uiSettings.showRain ? baseRainRate * uiSettings.precipitationMultiplier : 0.0f);
        leafSystem.setSpawnRate(uiSettings.showLeaf ? baseLeafRate * uiSettings.precipitationMultiplier : 0.0f);
        hailSystem.setSpawnRate(uiSettings.showHail ? baseHailRate * uiSettings.precipitationMultiplier : 0.0f);
        dustSystem.setSpawnRate(uiSettings.showDust ? baseDustRate * uiSettings.precipitationMultiplier : 0.0f);

        for (auto* sys : particleSystems) {
            sys->setCollisionEnabled(uiSettings.collisionEnabled);
        }

        if (uiSettings.showSnow)
            snowSystem.update(deltaTime, currentFrame, wind, uiSettings.collisionEnabled ? &collision : nullptr);
        if (uiSettings.showRain)
            rainSystem.update(deltaTime, currentFrame, wind, uiSettings.collisionEnabled ? &collision : nullptr);
        if (uiSettings.showLeaf)
            leafSystem.update(deltaTime, currentFrame, wind, uiSettings.collisionEnabled ? &collision : nullptr);
        if (uiSettings.showHail)
            hailSystem.update(deltaTime, currentFrame, wind, uiSettings.collisionEnabled ? &collision : nullptr);
        if (uiSettings.showDust)
            dustSystem.update(deltaTime, currentFrame, wind, uiSettings.collisionEnabled ? &collision : nullptr);

        glm::vec3 clearColor;
        switch (uiSettings.currentSeason) {
            case WINTER:
                clearColor = glm::vec3(0.08f, 0.10f, 0.15f);
                break;
            case SPRING:
                clearColor = glm::vec3(0.15f, 0.25f, 0.12f);
                break;
            case SUMMER:
                clearColor = glm::vec3(0.45f, 0.65f, 0.85f);
                break;
            case AUTUMN:
                clearColor = glm::vec3(0.40f, 0.25f, 0.10f);
                break;
            default:
                clearColor = glm::vec3(0.05f, 0.08f, 0.15f);
                break;
        }
        glClearColor(clearColor.r, clearColor.g, clearColor.b, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        particleShader.use();

        glm::mat4 projection = glm::perspective(glm::radians(camera.Zoom), (float)SCR_WIDTH / (float)SCR_HEIGHT, 0.1f, 200.0f);
        glm::mat4 view = camera.GetViewMatrix();
        particleShader.setMat4("projection", projection);
        particleShader.setMat4("view", view);
        particleShader.setVec3("cameraPos", camera.Position);

        if (uiSettings.showSnow)
        {
            particleShader.setVec3("particleColor", glm::vec3(0.95f, 0.98f, 1.0f));
            snowSystem.render();
        }

        if (uiSettings.showRain)
        {
            particleShader.setVec3("particleColor", glm::vec3(0.6f, 0.8f, 0.95f));
            rainSystem.render();
        }

        if (uiSettings.showLeaf)
        {
            particleShader.setVec3("particleColor", glm::vec3(0.8f, 0.5f, 0.2f));
            leafSystem.render();
        }

        if (uiSettings.showHail)
        {
            particleShader.setVec3("particleColor", glm::vec3(0.85f, 0.9f, 1.0f));
            hailSystem.render();
        }

        if (uiSettings.showDust)
        {
            particleShader.setVec3("particleColor", glm::vec3(0.7f, 0.65f, 0.55f));
            dustSystem.render();
        }

        uiManager.buildUI(uiSettings, particleSystems, wind, collision);
        uiManager.render();

        glfwSwapBuffers(window);
        glfwPollEvents();
    }

    uiManager.shutdown();
    glfwTerminate();
    return 0;
}

void processInput(GLFWwindow* window)
{
    if (glfwGetKey(window, GLFW_KEY_ESCAPE) == GLFW_PRESS)
        glfwSetWindowShouldClose(window, true);

    if (glfwGetKey(window, GLFW_KEY_W) == GLFW_PRESS)
        camera.ProcessKeyboard(FORWARD, deltaTime);
    if (glfwGetKey(window, GLFW_KEY_S) == GLFW_PRESS)
        camera.ProcessKeyboard(BACKWARD, deltaTime);
    if (glfwGetKey(window, GLFW_KEY_A) == GLFW_PRESS)
        camera.ProcessKeyboard(LEFT, deltaTime);
    if (glfwGetKey(window, GLFW_KEY_D) == GLFW_PRESS)
        camera.ProcessKeyboard(RIGHT, deltaTime);
}

void key_callback(GLFWwindow* window, int key, int scancode, int action, int mods)
{
    if (key == GLFW_KEY_TAB && action == GLFW_PRESS)
    {
        uiSettings.showUI = !uiSettings.showUI;
        mouseEnabled = !mouseEnabled;
        if (mouseEnabled)
            glfwSetInputMode(window, GLFW_CURSOR, GLFW_CURSOR_DISABLED);
        else
            glfwSetInputMode(window, GLFW_CURSOR, GLFW_CURSOR_NORMAL);
    }
}

void framebuffer_size_callback(GLFWwindow* window, int width, int height)
{
    glViewport(0, 0, width, height);
}

void mouse_callback(GLFWwindow* window, double xposIn, double yposIn)
{
    if (!mouseEnabled) return;

    float xpos = static_cast<float>(xposIn);
    float ypos = static_cast<float>(yposIn);

    if (firstMouse)
    {
        lastX = xpos;
        lastY = ypos;
        firstMouse = false;
    }

    float xoffset = xpos - lastX;
    float yoffset = lastY - ypos;

    lastX = xpos;
    lastY = ypos;

    camera.ProcessMouseMovement(xoffset, yoffset);
}

void scroll_callback(GLFWwindow* window, double xoffset, double yoffset)
{
    if (!mouseEnabled) return;
    camera.ProcessMouseScroll(static_cast<float>(yoffset));
}
