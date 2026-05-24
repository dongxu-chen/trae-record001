package com.abtest.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import lombok.Data;
import java.time.LocalDateTime;
import java.util.List;

@Data
public class ExperimentDTO {

    @NotBlank(message = "实验名称不能为空")
    @Size(max = 100, message = "实验名称长度不能超过100")
    private String name;

    @Size(max = 1000, message = "描述长度不能超过1000")
    private String description;

    @NotBlank(message = "负责人不能为空")
    private String owner;

    @NotNull(message = "流量占比不能为空")
    @Min(value = 1, message = "流量占比最小为1%")
    @Max(value = 100, message = "流量占比最大为100%")
    private Integer trafficPercentage;

    @NotBlank(message = "流量分流键不能为空")
    private String trafficKey;

    private Long layerId;

    private String trafficMode = "FIXED";

    private Double mabEpsilon = 0.1;

    private Integer mabUpdateIntervalMinutes = 60;

    private Boolean autoStopEnabled = false;

    private Double autoStopConfidenceThreshold = 0.95;

    private Long autoStopMaxSampleSize;

    private LocalDateTime startTime;

    private LocalDateTime endTime;

    @NotEmpty(message = "至少需要一个实验组")
    @Valid
    private List<VariantDTO> variants;

    @NotEmpty(message = "至少需要一个指标")
    @Valid
    private List<MetricDTO> metrics;
}
