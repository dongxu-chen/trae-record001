package com.api.docs.config;

import java.util.HashSet;
import java.util.Set;

public class GeneratorConfig {
    private String projectPath;
    private String outputPath = "./docs";
    private String apiVersion = "1.0.0";
    private String apiTitle = "API Documentation";
    private String apiDescription = "Auto-generated API documentation";
    private String serverUrl = "http://localhost:8080";
    private int serverPort = 8088;
    private boolean enableSwaggerUI = true;
    private boolean generateMarkdown = true;
    private boolean enableVersioning = true;

    private boolean enablePermissionFilter = false;
    private Set<String> allowedRoles = new HashSet<>();
    private Set<String> sensitiveTags = new HashSet<>();
    private Set<String> sensitivePaths = new HashSet<>();
    private boolean hideInternalModels = true;

    private boolean enableExampleGenerator = true;
    private boolean enableMockServer = false;
    private int mockServerPort = 8089;
    private boolean enableCustomAnnotations = true;

    public String getProjectPath() {
        return projectPath;
    }

    public void setProjectPath(String projectPath) {
        this.projectPath = projectPath;
    }

    public String getOutputPath() {
        return outputPath;
    }

    public void setOutputPath(String outputPath) {
        this.outputPath = outputPath;
    }

    public String getApiVersion() {
        return apiVersion;
    }

    public void setApiVersion(String apiVersion) {
        this.apiVersion = apiVersion;
    }

    public String getApiTitle() {
        return apiTitle;
    }

    public void setApiTitle(String apiTitle) {
        this.apiTitle = apiTitle;
    }

    public String getApiDescription() {
        return apiDescription;
    }

    public void setApiDescription(String apiDescription) {
        this.apiDescription = apiDescription;
    }

    public String getServerUrl() {
        return serverUrl;
    }

    public void setServerUrl(String serverUrl) {
        this.serverUrl = serverUrl;
    }

    public int getServerPort() {
        return serverPort;
    }

    public void setServerPort(int serverPort) {
        this.serverPort = serverPort;
    }

    public boolean isEnableSwaggerUI() {
        return enableSwaggerUI;
    }

    public void setEnableSwaggerUI(boolean enableSwaggerUI) {
        this.enableSwaggerUI = enableSwaggerUI;
    }

    public boolean isGenerateMarkdown() {
        return generateMarkdown;
    }

    public void setGenerateMarkdown(boolean generateMarkdown) {
        this.generateMarkdown = generateMarkdown;
    }

    public boolean isEnableVersioning() {
        return enableVersioning;
    }

    public void setEnableVersioning(boolean enableVersioning) {
        this.enableVersioning = enableVersioning;
    }

    public boolean isEnablePermissionFilter() {
        return enablePermissionFilter;
    }

    public void setEnablePermissionFilter(boolean enablePermissionFilter) {
        this.enablePermissionFilter = enablePermissionFilter;
    }

    public Set<String> getAllowedRoles() {
        return allowedRoles;
    }

    public void setAllowedRoles(Set<String> allowedRoles) {
        this.allowedRoles = allowedRoles;
    }

    public void addAllowedRole(String role) {
        this.allowedRoles.add(role);
    }

    public Set<String> getSensitiveTags() {
        return sensitiveTags;
    }

    public void setSensitiveTags(Set<String> sensitiveTags) {
        this.sensitiveTags = sensitiveTags;
    }

    public void addSensitiveTag(String tag) {
        this.sensitiveTags.add(tag);
    }

    public Set<String> getSensitivePaths() {
        return sensitivePaths;
    }

    public void setSensitivePaths(Set<String> sensitivePaths) {
        this.sensitivePaths = sensitivePaths;
    }

    public void addSensitivePath(String path) {
        this.sensitivePaths.add(path);
    }

    public boolean isHideInternalModels() {
        return hideInternalModels;
    }

    public void setHideInternalModels(boolean hideInternalModels) {
        this.hideInternalModels = hideInternalModels;
    }

    public boolean isEnableExampleGenerator() {
        return enableExampleGenerator;
    }

    public void setEnableExampleGenerator(boolean enableExampleGenerator) {
        this.enableExampleGenerator = enableExampleGenerator;
    }

    public boolean isEnableMockServer() {
        return enableMockServer;
    }

    public void setEnableMockServer(boolean enableMockServer) {
        this.enableMockServer = enableMockServer;
    }

    public int getMockServerPort() {
        return mockServerPort;
    }

    public void setMockServerPort(int mockServerPort) {
        this.mockServerPort = mockServerPort;
    }

    public boolean isEnableCustomAnnotations() {
        return enableCustomAnnotations;
    }

    public void setEnableCustomAnnotations(boolean enableCustomAnnotations) {
        this.enableCustomAnnotations = enableCustomAnnotations;
    }
}