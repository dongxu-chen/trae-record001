package com.datasecurity.masking.label;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.HashMap;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DataLabel {

    private String id;

    private String name;

    private SensitivityLevel sensitivityLevel;

    private String dataType;

    private String source;

    private Map<String, Object> properties;

    private long createTime;

    private long updateTime;

    public DataLabel(String id, String name, SensitivityLevel sensitivityLevel) {
        this.id = id;
        this.name = name;
        this.sensitivityLevel = sensitivityLevel;
        this.createTime = System.currentTimeMillis();
        this.updateTime = this.createTime;
        this.properties = new HashMap<>();
    }

    public void addProperty(String key, Object value) {
        if (properties == null) {
            properties = new HashMap<>();
        }
        properties.put(key, value);
        this.updateTime = System.currentTimeMillis();
    }

    public Object getProperty(String key) {
        return properties != null ? properties.get(key) : null;
    }
}
