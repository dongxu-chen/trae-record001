package com.tracking.common.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ClickStreamResult implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long total;

    private List<TrackEvent> events;

    private Integer page;

    private Integer pageSize;
}
