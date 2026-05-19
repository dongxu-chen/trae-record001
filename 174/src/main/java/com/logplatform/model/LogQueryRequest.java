package com.logplatform.model;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.Data;

import java.util.List;

@Data
public class LogQueryRequest {

    private String query;

    private String appName;

    private String level;

    private String startTime;

    private String endTime;

    @Min(value = 0, message = "页码不能小于0")
    private int page = 0;

    @Min(value = 1, message = "每页大小不能小于1")
    @Max(value = 100, message = "每页大小不能超过100")
    private int size = 20;

    private boolean highlight = true;

    private List<String> fields;

    private String sortField = "@timestamp";

    private String sortOrder = "desc";
}
