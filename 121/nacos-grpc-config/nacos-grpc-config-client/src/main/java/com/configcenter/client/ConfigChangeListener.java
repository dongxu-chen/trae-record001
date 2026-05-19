package com.configcenter.client;

/**
 * 配置变更监听器
 */
public interface ConfigChangeListener {

    /**
     * 配置变更时调用
     * @param event 配置变更事件
     */
    void onChange(ConfigChangeEvent event);
}
