package com.abtest.service;

import com.abtest.dto.ExperimentDTO;
import com.abtest.dto.MetricDTO;
import com.abtest.dto.TrafficAdjustmentDTO;
import com.abtest.dto.VariantDTO;
import com.abtest.entity.Experiment;
import com.abtest.entity.Layer;
import com.abtest.entity.Metric;
import com.abtest.entity.Variant;
import com.abtest.repository.ExperimentRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class ExperimentService {

    private final ExperimentRepository experimentRepository;
    private final BucketingService bucketingService;
    private final ClickHouseMetricsService clickHouseMetricsService;
    private final LayerService layerService;

    @Transactional
    public Experiment createExperiment(ExperimentDTO dto) {
        validateVariants(dto.getVariants());

        Experiment experiment = new Experiment();
        experiment.setName(dto.getName());
        experiment.setDescription(dto.getDescription());
        experiment.setOwner(dto.getOwner());
        experiment.setStatus(Experiment.ExperimentStatus.DRAFT);
        experiment.setTrafficPercentage(dto.getTrafficPercentage());
        experiment.setTrafficKey(dto.getTrafficKey());

        if (dto.getLayerId() != null) {
            Layer layer = layerService.getLayer(dto.getLayerId())
                .orElseThrow(() -> new IllegalArgumentException("层不存在: " + dto.getLayerId()));
            experiment.setLayer(layer);
        }

        if (dto.getTrafficMode() != null) {
            experiment.setTrafficMode(Experiment.TrafficAllocationMode.valueOf(dto.getTrafficMode()));
        }
        experiment.setMabEpsilon(dto.getMabEpsilon());
        experiment.setMabUpdateIntervalMinutes(dto.getMabUpdateIntervalMinutes());
        experiment.setAutoStopEnabled(dto.getAutoStopEnabled());
        experiment.setAutoStopConfidenceThreshold(dto.getAutoStopConfidenceThreshold());
        experiment.setAutoStopMaxSampleSize(dto.getAutoStopMaxSampleSize());
        experiment.setStartTime(dto.getStartTime());
        experiment.setEndTime(dto.getEndTime());

        for (VariantDTO variantDTO : dto.getVariants()) {
            Variant variant = new Variant();
            variant.setExperiment(experiment);
            variant.setName(variantDTO.getName());
            variant.setTrafficWeight(variantDTO.getTrafficWeight());
            variant.setIsControl(variantDTO.getIsControl() != null ? variantDTO.getIsControl() : false);
            variant.setConfiguration(variantDTO.getConfiguration());
            experiment.getVariants().add(variant);
        }

        for (MetricDTO metricDTO : dto.getMetrics()) {
            Metric metric = new Metric();
            metric.setExperiment(experiment);
            metric.setName(metricDTO.getName());
            metric.setDescription(metricDTO.getDescription());
            metric.setType(metricDTO.getType());
            metric.setEventName(metricDTO.getEventName());
            metric.setPropertyName(metricDTO.getPropertyName());
            metric.setAggregationType(metricDTO.getAggregationType());
            experiment.getMetrics().add(metric);
        }

        return experimentRepository.save(experiment);
    }

    public Optional<Experiment> getExperiment(Long id) {
        return experimentRepository.findById(id);
    }

    public List<Experiment> getAllExperiments() {
        return experimentRepository.findAll();
    }

    public List<Experiment> getExperimentsByStatus(Experiment.ExperimentStatus status) {
        return experimentRepository.findByStatus(status);
    }

    @Transactional
    public Experiment startExperiment(Long id) {
        Experiment experiment = experimentRepository.findById(id)
            .orElseThrow(() -> new IllegalArgumentException("实验不存在: " + id));

        if (experiment.getStatus() != Experiment.ExperimentStatus.DRAFT) {
            throw new IllegalStateException("只有草稿状态的实验可以启动");
        }

        experiment.setStatus(Experiment.ExperimentStatus.RUNNING);
        experiment.setStartTime(LocalDateTime.now());
        return experimentRepository.save(experiment);
    }

    @Transactional
    public Experiment pauseExperiment(Long id) {
        Experiment experiment = experimentRepository.findById(id)
            .orElseThrow(() -> new IllegalArgumentException("实验不存在: " + id));

        if (experiment.getStatus() != Experiment.ExperimentStatus.RUNNING) {
            throw new IllegalStateException("只有运行状态的实验可以暂停");
        }

        experiment.setStatus(Experiment.ExperimentStatus.PAUSED);
        bucketingService.clearBucketCache(id);
        return experimentRepository.save(experiment);
    }

    @Transactional
    public Experiment resumeExperiment(Long id) {
        Experiment experiment = experimentRepository.findById(id)
            .orElseThrow(() -> new IllegalArgumentException("实验不存在: " + id));

        if (experiment.getStatus() != Experiment.ExperimentStatus.PAUSED) {
            throw new IllegalStateException("只有暂停状态的实验可以恢复");
        }

        experiment.setStatus(Experiment.ExperimentStatus.RUNNING);
        return experimentRepository.save(experiment);
    }

    @Transactional
    public Experiment completeExperiment(Long id) {
        Experiment experiment = experimentRepository.findById(id)
            .orElseThrow(() -> new IllegalArgumentException("实验不存在: " + id));

        experiment.setStatus(Experiment.ExperimentStatus.COMPLETED);
        experiment.setEndTime(LocalDateTime.now());
        bucketingService.clearBucketCache(id);
        return experimentRepository.save(experiment);
    }

    @Transactional
    public Experiment adjustTraffic(TrafficAdjustmentDTO dto) {
        Experiment experiment = experimentRepository.findById(dto.getExperimentId())
            .orElseThrow(() -> new IllegalArgumentException("实验不存在: " + dto.getExperimentId()));

        experiment.setTrafficPercentage(dto.getNewTrafficPercentage());
        bucketingService.clearBucketCache(dto.getExperimentId());
        bucketingService.refreshHashRing(dto.getExperimentId());
        return experimentRepository.save(experiment);
    }

    @Transactional
    public void deleteExperiment(Long id) {
        Experiment experiment = experimentRepository.findById(id)
            .orElseThrow(() -> new IllegalArgumentException("实验不存在: " + id));

        if (experiment.getStatus() == Experiment.ExperimentStatus.RUNNING) {
            throw new IllegalStateException("运行中的实验不能删除，请先暂停或结束实验");
        }

        bucketingService.clearBucketCache(id);
        experimentRepository.delete(experiment);
    }

    private void validateVariants(List<VariantDTO> variants) {
        long controlCount = variants.stream()
            .filter(v -> v.getIsControl() != null && v.getIsControl())
            .count();

        if (controlCount == 0) {
            throw new IllegalArgumentException("必须有一个对照组");
        }
        if (controlCount > 1) {
            throw new IllegalArgumentException("只能有一个对照组");
        }
    }

    public List<String> getVariantNames(Experiment experiment) {
        return experiment.getVariants().stream()
            .map(Variant::getName)
            .collect(Collectors.toList());
    }

    public Optional<Variant> getControlVariant(Experiment experiment) {
        return experiment.getVariants().stream()
            .filter(Variant::getIsControl)
            .findFirst();
    }
}
