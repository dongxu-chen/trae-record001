package com.abtest.service;

import com.abtest.dto.LayerDTO;
import com.abtest.entity.Experiment;
import com.abtest.entity.Layer;
import com.abtest.repository.LayerRepository;
import com.google.common.hash.Hashing;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Optional;

@Slf4j
@Service
@RequiredArgsConstructor
public class LayerService {

    private static final int TOTAL_BUCKETS = 10000;

    private final LayerRepository layerRepository;

    @Transactional
    public Layer createLayer(LayerDTO dto) {
        Layer layer = new Layer();
        layer.setName(dto.getName());
        layer.setDescription(dto.getDescription());
        layer.setTrafficKey(dto.getTrafficKey());
        layer.setTrafficPercentage(dto.getTrafficPercentage());
        layer.setIsActive(dto.getIsActive());
        return layerRepository.save(layer);
    }

    public Optional<Layer> getLayer(Long id) {
        return layerRepository.findById(id);
    }

    public List<Layer> getAllLayers() {
        return layerRepository.findAll();
    }

    public List<Layer> getActiveLayers() {
        return layerRepository.findByIsActiveTrue();
    }

    @Transactional
    public Layer updateLayer(Long id, LayerDTO dto) {
        Layer layer = layerRepository.findById(id)
            .orElseThrow(() -> new IllegalArgumentException("层不存在: " + id));

        layer.setName(dto.getName());
        layer.setDescription(dto.getDescription());
        layer.setTrafficKey(dto.getTrafficKey());
        layer.setTrafficPercentage(dto.getTrafficPercentage());
        layer.setIsActive(dto.getIsActive());
        return layerRepository.save(layer);
    }

    @Transactional
    public void deleteLayer(Long id) {
        Layer layer = layerRepository.findById(id)
            .orElseThrow(() -> new IllegalArgumentException("层不存在: " + id));

        if (!layer.getExperiments().isEmpty()) {
            throw new IllegalStateException("该层下还有实验，无法删除");
        }

        layerRepository.delete(layer);
    }

    public boolean isUserInLayer(String userId, Layer layer) {
        int bucket = calculateBucket(userId, layer.getTrafficKey());
        int threshold = (layer.getTrafficPercentage() * TOTAL_BUCKETS) / 100;
        return bucket < threshold;
    }

    public int getLayerBucket(String userId, Layer layer) {
        return calculateBucket(userId, layer.getTrafficKey());
    }

    public Experiment assignExperimentInLayer(String userId, Layer layer) {
        if (!isUserInLayer(userId, layer)) {
            return null;
        }

        List<Experiment> runningExperiments = layer.getExperiments().stream()
            .filter(e -> e.getStatus() == Experiment.ExperimentStatus.RUNNING)
            .toList();

        if (runningExperiments.isEmpty()) {
            return null;
        }

        int bucket = getLayerBucket(userId, layer);
        int experimentIndex = bucket % runningExperiments.size();
        return runningExperiments.get(experimentIndex);
    }

    private int calculateBucket(String userId, String trafficKey) {
        String combined = userId + ":" + trafficKey;
        int hash = Hashing.murmur3_32_fixed().hashString(combined, StandardCharsets.UTF_8).asInt();
        return Math.abs(hash) % TOTAL_BUCKETS;
    }

    public boolean validateLayerForExperiment(Layer layer, Experiment experiment) {
        if (layer.getExperiments().stream()
            .anyMatch(e -> e.getStatus() == Experiment.ExperimentStatus.RUNNING
                && !e.getId().equals(experiment.getId()))) {
            return true;
        }
        return true;
    }
}
