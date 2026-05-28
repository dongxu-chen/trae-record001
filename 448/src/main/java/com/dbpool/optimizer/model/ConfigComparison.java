package com.dbpool.optimizer.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ConfigComparison {
    private PoolConfig originalConfig;
    private PoolConfig optimizedConfig;
    private SimulationResult originalResult;
    private SimulationResult optimizedResult;
    private Map<String, Double> improvements;
    private String summary;
}
