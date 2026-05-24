package com.abtest.config;

import com.abtest.dto.ExperimentDTO;
import com.abtest.dto.MetricDTO;
import com.abtest.dto.VariantDTO;
import com.abtest.entity.Experiment;
import com.abtest.entity.Metric;
import com.abtest.repository.ExperimentRepository;
import com.abtest.service.ExperimentService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.Arrays;

@Slf4j
@Configuration
@RequiredArgsConstructor
public class DataInitializer {

    private final ExperimentRepository experimentRepository;
    private final ExperimentService experimentService;

    @Bean
    public CommandLineRunner initSampleData() {
        return args -> {
            if (experimentRepository.count() == 0) {
                log.info("初始化示例实验数据...");
                createSampleExperiment();
                log.info("示例数据初始化完成");
            }
        };
    }

    private void createSampleExperiment() {
        ExperimentDTO dto = new ExperimentDTO();
        dto.setName("首页按钮颜色测试");
        dto.setDescription("测试首页按钮不同颜色对点击率的影响");
        dto.setOwner("product_team");
        dto.setTrafficPercentage(50);
        dto.setTrafficKey("user_id");

        VariantDTO control = new VariantDTO();
        control.setName("control");
        control.setIsControl(true);
        control.setTrafficWeight(50);
        control.setConfiguration("{\"buttonColor\":\"#1890ff\"}");

        VariantDTO test = new VariantDTO();
        test.setName("test_red");
        test.setIsControl(false);
        test.setTrafficWeight(50);
        test.setConfiguration("{\"buttonColor\":\"#f5222d\"}");

        dto.setVariants(Arrays.asList(control, test));

        MetricDTO clickRate = new MetricDTO();
        clickRate.setName("button_click_rate");
        clickRate.setDescription("按钮点击率");
        clickRate.setType(Metric.MetricType.CONVERSION);
        clickRate.setEventName("button_click");

        MetricDTO dwellTime = new MetricDTO();
        dwellTime.setName("page_dwell_time");
        dwellTime.setDescription("页面停留时间");
        dwellTime.setType(Metric.MetricType.CONTINUOUS);
        dwellTime.setEventName("page_leave");
        dwellTime.setPropertyName("dwell_seconds");
        dwellTime.setAggregationType(Metric.AggregationType.AVG);

        dto.setMetrics(Arrays.asList(clickRate, dwellTime));

        Experiment experiment = experimentService.createExperiment(dto);
        log.info("创建示例实验: ID={}, 名称={}", experiment.getId(), experiment.getName());
    }
}
