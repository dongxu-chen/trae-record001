package com.configcenter.server.controller;

import com.configcenter.server.entity.ConfigDependency;
import com.configcenter.server.service.ConfigDependencyService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/api/config/dependencies")
public class ConfigDependencyController {

    @Autowired
    private ConfigDependencyService dependencyService;

    @PostMapping
    public ResponseEntity<ConfigDependency> addDependency(
            @RequestBody Map<String, String> request,
            HttpServletRequest httpRequest) {

        ConfigDependency dependency = dependencyService.addDependency(
                request.get("sourceApplication"),
                request.get("sourceProfile"),
                request.get("sourceLabel"),
                request.get("sourceConfigKey"),
                request.get("targetApplication"),
                request.get("targetProfile"),
                request.get("targetLabel"),
                request.get("targetConfigKey"),
                ConfigDependency.DependencyType.valueOf(
                        request.getOrDefault("dependencyType", "REQUIRED")),
                request.get("description"),
                request.getOrDefault("operator", "system"),
                httpRequest
        );
        return ResponseEntity.ok(dependency);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Map<String, Object>> removeDependency(
            @PathVariable Long id,
            @RequestParam(defaultValue = "system") String operator,
            HttpServletRequest httpRequest) {

        dependencyService.removeDependency(id, operator, httpRequest);
        return ResponseEntity.ok(Map.of(
                "success", true,
                "message", "依赖关系已移除"
        ));
    }

    @GetMapping("/application/{application}")
    public ResponseEntity<List<ConfigDependency>> getDependenciesByApplication(
            @PathVariable String application) {

        List<ConfigDependency> dependencies = dependencyService.getDependenciesByApplication(application);
        return ResponseEntity.ok(dependencies);
    }

    @GetMapping("/source/{application}")
    public ResponseEntity<List<ConfigDependency>> getSourceDependencies(
            @PathVariable String application) {

        List<ConfigDependency> dependencies = dependencyService.getSourceDependencies(application);
        return ResponseEntity.ok(dependencies);
    }

    @GetMapping("/target/{application}")
    public ResponseEntity<List<ConfigDependency>> getTargetDependencies(
            @PathVariable String application) {

        List<ConfigDependency> dependencies = dependencyService.getTargetDependencies(application);
        return ResponseEntity.ok(dependencies);
    }

    @GetMapping("/analyze")
    public ResponseEntity<Map<String, Object>> analyzeDependencies(
            @RequestParam String application,
            @RequestParam(defaultValue = "default") String profile,
            @RequestParam(defaultValue = "master") String label,
            @RequestParam String configKey) {

        Map<String, Object> analysis = dependencyService.analyzeDependencies(
                application, profile, label, configKey);
        return ResponseEntity.ok(analysis);
    }

    @GetMapping("/graph/{application}")
    public ResponseEntity<Map<String, Object>> getDependencyGraph(
            @PathVariable String application) {

        Map<String, Object> graph = dependencyService.getDependencyGraph(application);
        return ResponseEntity.ok(graph);
    }

    @GetMapping("/topology/{application}")
    public ResponseEntity<Map<String, Object>> getTopologyGraph(
            @PathVariable String application) {

        Map<String, Object> topology = dependencyService.getTopologyGraph(application);
        return ResponseEntity.ok(topology);
    }

    @GetMapping("/{id}")
    public ResponseEntity<ConfigDependency> getDependency(@PathVariable Long id) {
        Optional<ConfigDependency> dependency = dependencyService.getDependency(id);
        return dependency.map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping
    public ResponseEntity<List<ConfigDependency>> getAllDependencies() {
        List<ConfigDependency> dependencies = dependencyService.getAllDependencies();
        return ResponseEntity.ok(dependencies);
    }
}
