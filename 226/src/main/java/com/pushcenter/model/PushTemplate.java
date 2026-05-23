package com.pushcenter.model;

import com.pushcenter.enums.PushChannel;
import lombok.Builder;
import lombok.Data;

import java.io.Serializable;
import java.util.List;
import java.util.Set;

@Data
@Builder
public class PushTemplate implements Serializable {

    private static final long serialVersionUID = 1L;

    private String templateCode;

    private String templateName;

    private String titleTemplate;

    private String contentTemplate;

    private Set<PushChannel> supportedChannels;

    private PushChannel defaultChannel;

    private List<String> requiredVariables;

    private int maxRetryCount;

    private boolean enabled;
}
