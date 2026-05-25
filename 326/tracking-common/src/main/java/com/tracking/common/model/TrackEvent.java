package com.tracking.common.model;

import com.alibaba.fastjson2.JSON;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TrackEvent implements Serializable {

    private static final long serialVersionUID = 1L;

    private String id;

    @NotBlank(message = "事件名称不能为空")
    private String event;

    @NotNull(message = "时间戳不能为空")
    private Long timestamp;

    private String anonymousId;

    private String userId;

    private String sessionId;

    private String platform;

    private String appId;

    private String appVersion;

    private String channel;

    private String os;

    private String osVersion;

    private String deviceId;

    private String deviceModel;

    private String ip;

    private String userAgent;

    private String referrer;

    private String url;

    private String title;

    private Integer screenWidth;

    private Integer screenHeight;

    private String networkType;

    private String carrier;

    @Builder.Default
    private Map<String, Object> properties = new HashMap<>();

    private Long receiveTime;

    private String source;

    private String country;

    private String province;

    private String city;

    public String toJson() {
        return JSON.toJSONString(this);
    }

    public static TrackEvent fromJson(String json) {
        return JSON.parseObject(json, TrackEvent.class);
    }

    public void addProperty(String key, Object value) {
        if (this.properties == null) {
            this.properties = new HashMap<>();
        }
        this.properties.put(key, value);
    }

    public Object getProperty(String key) {
        return this.properties != null ? this.properties.get(key) : null;
    }
}
