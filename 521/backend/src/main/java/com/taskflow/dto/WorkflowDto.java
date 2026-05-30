package com.taskflow.dto;

import lombok.Data;
import java.util.List;
import java.util.Map;

@Data
public class WorkflowDto {
    private Long id;
    private String name;
    private String description;
    private String dagJson;
    private String status;
    private Integer version;
    private String createdBy;
    private List<TaskDto> tasks;

    @Data
    public static class CreateRequest {
        private String name;
        private String description;
        private String dagJson;
        private List<TaskDto> tasks;
    }

    @Data
    public static class UpdateRequest {
        private String name;
        private String description;
        private String dagJson;
        private List<TaskDto> tasks;
    }
}
