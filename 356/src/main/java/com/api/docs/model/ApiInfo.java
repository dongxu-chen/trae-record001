package com.api.docs.model;

import java.util.ArrayList;
import java.util.List;

public class ApiInfo {
    private String title;
    private String description;
    private String version;
    private String serverUrl;
    private List<ControllerInfo> controllers = new ArrayList<>();
    private List<ModelInfo> models = new ArrayList<>();

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public String getVersion() {
        return version;
    }

    public void setVersion(String version) {
        this.version = version;
    }

    public String getServerUrl() {
        return serverUrl;
    }

    public void setServerUrl(String serverUrl) {
        this.serverUrl = serverUrl;
    }

    public List<ControllerInfo> getControllers() {
        return controllers;
    }

    public void setControllers(List<ControllerInfo> controllers) {
        this.controllers = controllers;
    }

    public void addController(ControllerInfo controller) {
        this.controllers.add(controller);
    }

    public List<ModelInfo> getModels() {
        return models;
    }

    public void setModels(List<ModelInfo> models) {
        this.models = models;
    }

    public void addModel(ModelInfo model) {
        this.models.add(model);
    }
}