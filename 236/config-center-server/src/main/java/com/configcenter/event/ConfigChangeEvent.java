package com.configcenter.event;

import org.springframework.cloud.bus.event.RemoteApplicationEvent;

public class ConfigChangeEvent extends RemoteApplicationEvent {

    private String application;
    private String profile;
    private String version;

    public ConfigChangeEvent() {
    }

    public ConfigChangeEvent(Object source, String originService, String destinationService,
                             String application, String profile, String version) {
        super(source, originService, destinationService);
        this.application = application;
        this.profile = profile;
        this.version = version;
    }

    public String getApplication() {
        return application;
    }

    public void setApplication(String application) {
        this.application = application;
    }

    public String getProfile() {
        return profile;
    }

    public void setProfile(String profile) {
        this.profile = profile;
    }

    public String getVersion() {
        return version;
    }

    public void setVersion(String version) {
        this.version = version;
    }
}
