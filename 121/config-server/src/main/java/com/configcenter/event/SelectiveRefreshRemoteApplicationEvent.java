package com.configcenter.event;

import org.springframework.cloud.bus.event.RemoteApplicationEvent;

public class SelectiveRefreshRemoteApplicationEvent extends RemoteApplicationEvent {

    private String serviceName;
    private String branch;

    public SelectiveRefreshRemoteApplicationEvent() {
    }

    public SelectiveRefreshRemoteApplicationEvent(Object source, String originService,
                                                   String destinationService,
                                                   String serviceName, String branch) {
        super(source, originService, destinationService);
        this.serviceName = serviceName;
        this.branch = branch;
    }

    public String getServiceName() {
        return serviceName;
    }

    public void setServiceName(String serviceName) {
        this.serviceName = serviceName;
    }

    public String getBranch() {
        return branch;
    }

    public void setBranch(String branch) {
        this.branch = branch;
    }
}
