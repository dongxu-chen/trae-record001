package com.configcenter.server.service;

import com.configcenter.server.entity.ConfigDependency;
import com.configcenter.server.repository.ConfigDependencyRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.servlet.http.HttpServletRequest;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class ConfigDependencyService {

    private static final Logger logger = LoggerFactory.getLogger(ConfigDependencyService.class);

    @Autowired
    private ConfigDependencyRepository dependencyRepository;

    @Autowired
    private ConfigAuditLogService auditLogService;

    @Transactional
    public ConfigDependency addDependency(String sourceApplication, String sourceProfile,
                                           String sourceLabel, String sourceConfigKey,
                                           String targetApplication, String targetProfile,
                                           String targetLabel, String targetConfigKey,
                                           ConfigDependency.DependencyType dependencyType,
                                           String description, String operator,
                                           HttpServletRequest request) {

        Optional<ConfigDependency> existing = dependencyRepository
                .findBySourceApplicationAndSourceProfileAndSourceLabelAndSourceConfigKeyAndTargetApplicationAndTargetProfileAndTargetLabelAndTargetConfigKey(
                        sourceApplication, sourceProfile, sourceLabel, sourceConfigKey,
                        targetApplication, targetProfile, targetLabel, targetConfigKey);

        if (existing.isPresent()) {
            throw new RuntimeException("依赖关系已存在");
        }

        ConfigDependency dependency = new ConfigDependency();
        dependency.setSourceApplication(sourceApplication);
        dependency.setSourceProfile(sourceProfile);
        dependency.setSourceLabel(sourceLabel);
        dependency.setSourceConfigKey(sourceConfigKey);
        dependency.setTargetApplication(targetApplication);
        dependency.setTargetProfile(targetProfile);
        dependency.setTargetLabel(targetLabel);
        dependency.setTargetConfigKey(targetConfigKey);
        dependency.setDependencyType(dependencyType);
        dependency.setDescription(description);

        ConfigDependency saved = dependencyRepository.save(dependency);

        logger.info("添加配置依赖: {} -> {}", sourceConfigKey, targetConfigKey);

        return saved;
    }

    @Transactional
    public void removeDependency(Long dependencyId, String operator, HttpServletRequest request) {
        ConfigDependency dependency = dependencyRepository.findById(dependencyId)
                .orElseThrow(() -> new RuntimeException("依赖关系不存在: " + dependencyId));

        dependencyRepository.delete(dependency);

        logger.info("移除配置依赖: {} -> {}",
                dependency.getSourceConfigKey(), dependency.getTargetConfigKey());
    }

    public List<ConfigDependency> getDependenciesByApplication(String application) {
        return dependencyRepository.findByApplication(application);
    }

    public List<ConfigDependency> getSourceDependencies(String application) {
        return dependencyRepository.findBySourceApplicationOrderByCreatedAtDesc(application);
    }

    public List<ConfigDependency> getTargetDependencies(String application) {
        return dependencyRepository.findByTargetApplicationOrderByCreatedAtDesc(application);
    }

    public List<ConfigDependency> getDependenciesBySourceConfig(String application,
                                                                  String profile, String label,
                                                                  String configKey) {
        return dependencyRepository.findBySourceConfig(application, profile, label, configKey);
    }

    public List<ConfigDependency> getDependenciesByTargetConfig(String application,
                                                                  String profile, String label,
                                                                  String configKey) {
        return dependencyRepository.findByTargetConfig(application, profile, label, configKey);
    }

    public Map<String, Object> analyzeDependencies(String application, String profile,
                                                     String label, String configKey) {
        Map<String, Object> analysis = new HashMap<>();

        List<ConfigDependency> sourceDeps = dependencyRepository.findBySourceConfig(
                application, profile, label, configKey);

        List<ConfigDependency> targetDeps = dependencyRepository.findByTargetConfig(
                application, profile, label, configKey);

        analysis.put("sourceDependencies", sourceDeps);
        analysis.put("targetDependencies", targetDeps);
        analysis.put("sourceDependencyCount", sourceDeps.size());
        analysis.put("targetDependencyCount", targetDeps.size());

        if (!sourceDeps.isEmpty()) {
            List<Map<String, String>> warnings = new ArrayList<>();
            for (ConfigDependency dep : sourceDeps) {
                Map<String, String> warning = new HashMap<>();
                warning.put("targetApplication", dep.getTargetApplication());
                warning.put("targetConfigKey", dep.getTargetConfigKey());
                warning.put("dependencyType", dep.getDependencyType().name());
                warning.put("message", String.format(
                        "该配置变更可能影响 %s 应用的 %s 配置项",
                        dep.getTargetApplication(), dep.getTargetConfigKey()));
                warnings.add(warning);
            }
            analysis.put("changeWarnings", warnings);
        }

        if (!targetDeps.isEmpty()) {
            List<Map<String, String>> prerequisites = new ArrayList<>();
            for (ConfigDependency dep : targetDeps) {
                Map<String, String> prereq = new HashMap<>();
                prereq.put("sourceApplication", dep.getSourceApplication());
                prereq.put("sourceConfigKey", dep.getSourceConfigKey());
                prereq.put("dependencyType", dep.getDependencyType().name());
                prereq.put("message", String.format(
                        "该配置依赖于 %s 应用的 %s 配置项",
                        dep.getSourceApplication(), dep.getSourceConfigKey()));
                prerequisites.add(prereq);
            }
            analysis.put("prerequisites", prerequisites);
        }

        return analysis;
    }

    public Map<String, Object> getDependencyGraph(String application) {
        List<ConfigDependency> allDeps = dependencyRepository.findByApplication(application);

        Set<String> nodes = new HashSet<>();
        List<Map<String, Object>> edges = new ArrayList<>();

        nodes.add(application);

        for (ConfigDependency dep : allDeps) {
            nodes.add(dep.getSourceApplication());
            nodes.add(dep.getTargetApplication());

            Map<String, Object> edge = new HashMap<>();
            edge.put("source", dep.getSourceApplication());
            edge.put("target", dep.getTargetApplication());
            edge.put("sourceKey", dep.getSourceConfigKey());
            edge.put("targetKey", dep.getTargetConfigKey());
            edge.put("type", dep.getDependencyType().name());
            edges.add(edge);
        }

        Map<String, Object> graph = new HashMap<>();
        graph.put("nodes", new ArrayList<>(nodes));
        graph.put("edges", edges);
        graph.put("nodeCount", nodes.size());
        graph.put("edgeCount", edges.size());

        return graph;
    }

    public Map<String, Object> getTopologyGraph(String application) {
        List<ConfigDependency> allDeps = dependencyRepository.findByApplication(application);

        Set<String> applications = new HashSet<>();
        Map<String, List<String>> configsByApp = new HashMap<>();
        List<Map<String, Object>> connections = new ArrayList<>();

        applications.add(application);
        configsByApp.putIfAbsent(application, new ArrayList<>());

        for (ConfigDependency dep : allDeps) {
            applications.add(dep.getSourceApplication());
            applications.add(dep.getTargetApplication());

            configsByApp.computeIfAbsent(dep.getSourceApplication(), k -> new ArrayList<>())
                    .add(dep.getSourceConfigKey());
            configsByApp.computeIfAbsent(dep.getTargetApplication(), k -> new ArrayList<>())
                    .add(dep.getTargetConfigKey());

            Map<String, Object> conn = new HashMap<>();
            conn.put("from", dep.getSourceApplication());
            conn.put("to", dep.getTargetApplication());
            conn.put("fromConfig", dep.getSourceConfigKey());
            conn.put("toConfig", dep.getTargetConfigKey());
            conn.put("dependencyType", dep.getDependencyType().name());
            connections.add(conn);
        }

        Map<String, Object> topology = new HashMap<>();
        topology.put("applications", new ArrayList<>(applications));
        topology.put("configsByApp", configsByApp);
        topology.put("connections", connections);

        return topology;
    }

    public Optional<ConfigDependency> getDependency(Long id) {
        return dependencyRepository.findById(id);
    }

    public List<ConfigDependency> getAllDependencies() {
        return dependencyRepository.findAll();
    }
}
