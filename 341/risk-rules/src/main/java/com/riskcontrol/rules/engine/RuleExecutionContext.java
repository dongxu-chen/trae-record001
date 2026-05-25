package com.riskcontrol.rules.engine;

import com.riskcontrol.common.model.IpInfo;
import com.riskcontrol.common.model.UserBehaviorProfile;
import lombok.Data;

import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;

@Data
public class RuleExecutionContext implements Serializable {
    private int loginCountLastHour;
    private int loginCountLastDay;
    private int passwordChangeCountLastWeek;
    private int distinctIpsLastHour;
    private int distinctDevicesLastDay;
    private int failedLoginAttempts;
    private UserBehaviorProfile userProfile;
    private IpInfo ipInfo;
    private Map<String, Object> contextData = new HashMap<>();

    public void addContextData(String key, Object value) {
        contextData.put(key, value);
    }

    public Object getContextData(String key) {
        return contextData.get(key);
    }
}
