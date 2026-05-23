package com.shortlink.dto;

import lombok.Data;

@Data
public class IpLocationResult {

    private String country;

    private String province;

    private String city;

    private String district;

    private String isp;

    public IpLocationResult() {
    }

    public IpLocationResult(String country, String province, String city) {
        this.country = country;
        this.province = province;
        this.city = city;
    }
}
