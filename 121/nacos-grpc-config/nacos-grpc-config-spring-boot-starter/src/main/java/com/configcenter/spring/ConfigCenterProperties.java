package com.configcenter.spring;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * 配置中心属性配置
 */
@ConfigurationProperties(prefix = "config.center")
public class ConfigCenterProperties {

    /**
     * 配置中心服务器地址
     */
    private String serverHost = "localhost";

    /**
     * 配置中心服务器端口
     */
    private int serverPort = 9090;

    /**
     * 客户端ID，不填则自动生成
     */
    private String clientId;

    /**
     * 服务名称
     */
    private String serviceName = "unknown-service";

    /**
     * 命名空间
     */
    private String namespace = "public";

    /**
     * 分组
     */
    private String group = "DEFAULT_GROUP";

    /**
     * 是否自动启动
     */
    private boolean autoStartup = true;

    /**
     * 订阅的配置DataId列表
     */
    private String[] subscribeDataIds = {};

    public String getServerHost() {
        return serverHost;
    }

    public void setServerHost(String serverHost) {
        this.serverHost = serverHost;
    }

    public int getServerPort() {
        return serverPort;
    }

    public void setServerPort(int serverPort) {
        this.serverPort = serverPort;
    }

    public String getClientId() {
        return clientId;
    }

    public void setClientId(String clientId) {
        this.clientId = clientId;
    }

    public String getServiceName() {
        return serviceName;
    }

    public void setServiceName(String serviceName) {
        this.serviceName = serviceName;
    }

    public String getNamespace() {
        return namespace;
    }

    public void setNamespace(String namespace) {
        this.namespace = namespace;
    }

    public String getGroup() {
        return group;
    }

    public void setGroup(String group) {
        this.group = group;
    }

    public boolean isAutoStartup() {
        return autoStartup;
    }

    public void setAutoStartup(boolean autoStartup) {
        this.autoStartup = autoStartup;
    }

    public String[] getSubscribeDataIds() {
        return subscribeDataIds;
    }

    public void setSubscribeDataIds(String[] subscribeDataIds) {
        this.subscribeDataIds = subscribeDataIds;
    }
}
