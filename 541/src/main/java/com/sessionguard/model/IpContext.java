package com.sessionguard.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class IpContext implements Serializable {

    private static final long serialVersionUID = 1L;

    private String ipAddress;

    private String subnetPrefix;

    private String geoCountry;

    private String geoCity;

    private String geoRegion;

    private String isp;

    private boolean isProxy;

    private boolean isVpn;

    private boolean isTor;

    private boolean isDataCenter;
}
