package com.configcenter.server.controller;

import com.configcenter.server.entity.ConfigPreValidation;
import com.configcenter.server.service.ConfigPreValidationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/api/config/pre-validation")
public class ConfigPreValidationController {

    @Autowired
    private ConfigPreValidationService validationService;

    @PostMapping
    public ResponseEntity<ConfigPreValidation> createValidation(
            @RequestBody Map<String, String> request,
            HttpServletRequest httpRequest) {

        ConfigPreValidation validation = validationService.createValidation(
                request.get("application"),
                request.get("profile"),
                request.get("label"),
                request.get("configContent"),
                request.get("testInstanceUrl"),
                request.getOrDefault("createdBy", "system"),
                httpRequest
        );
        return ResponseEntity.ok(validation);
    }

    @PostMapping("/{id}/execute")
    public ResponseEntity<ConfigPreValidation> executeValidation(
            @PathVariable Long id,
            HttpServletRequest httpRequest) {

        ConfigPreValidation validation = validationService.executeValidation(id, httpRequest);
        return ResponseEntity.ok(validation);
    }

    @PostMapping("/{id}/cancel")
    public ResponseEntity<ConfigPreValidation> cancelValidation(
            @PathVariable Long id,
            @RequestParam(defaultValue = "system") String operator,
            HttpServletRequest httpRequest) {

        ConfigPreValidation validation = validationService.cancelValidation(id, operator, httpRequest);
        return ResponseEntity.ok(validation);
    }

    @GetMapping("/application/{application}")
    public ResponseEntity<List<ConfigPreValidation>> getValidationHistory(
            @PathVariable String application) {

        List<ConfigPreValidation> validations = validationService.getValidationHistory(application);
        return ResponseEntity.ok(validations);
    }

    @GetMapping
    public ResponseEntity<List<ConfigPreValidation>> getValidations(
            @RequestParam String application,
            @RequestParam(defaultValue = "default") String profile,
            @RequestParam(defaultValue = "master") String label) {

        List<ConfigPreValidation> validations = validationService.getValidations(
                application, profile, label);
        return ResponseEntity.ok(validations);
    }

    @GetMapping("/active/{application}")
    public ResponseEntity<List<ConfigPreValidation>> getActiveValidations(
            @PathVariable String application) {

        List<ConfigPreValidation> validations = validationService.getActiveValidations(application);
        return ResponseEntity.ok(validations);
    }

    @GetMapping("/{id}")
    public ResponseEntity<ConfigPreValidation> getValidation(@PathVariable Long id) {
        Optional<ConfigPreValidation> validation = validationService.getValidation(id);
        return validation.map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }
}
