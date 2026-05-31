package com.schemaregistry.controller;

import com.schemaregistry.dto.CompatibilityCheckRequest;
import com.schemaregistry.dto.SchemaRequest;
import com.schemaregistry.model.*;
import com.schemaregistry.service.AuditService;
import com.schemaregistry.service.CodeGenerationService;
import com.schemaregistry.service.SchemaEvolutionService;
import com.schemaregistry.service.SchemaService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/schemas")
@CrossOrigin(origins = "http://localhost:3000")
public class SchemaController {

    private final SchemaService schemaService;
    private final SchemaEvolutionService evolutionService;
    private final CodeGenerationService codeGenerationService;
    private final AuditService auditService;

    @Autowired
    public SchemaController(SchemaService schemaService,
                            SchemaEvolutionService evolutionService,
                            CodeGenerationService codeGenerationService,
                            AuditService auditService) {
        this.schemaService = schemaService;
        this.evolutionService = evolutionService;
        this.codeGenerationService = codeGenerationService;
        this.auditService = auditService;
    }

    @PostMapping
    public ResponseEntity<SchemaEntity> createSchema(@Valid @RequestBody SchemaRequest request) {
        SchemaEntity schema = schemaService.createSchema(request);
        auditService.logSchemaCreated(schema.getSubject(), schema.getVersions().get(0).getSchemaText(), request.getDescription());
        return ResponseEntity.ok(schema);
    }

    @GetMapping
    public ResponseEntity<List<SchemaEntity>> getAllSchemas() {
        return ResponseEntity.ok(schemaService.getAllSchemas());
    }

    @GetMapping("/{subject}")
    public ResponseEntity<SchemaEntity> getSchema(@PathVariable String subject) {
        return schemaService.getSchemaBySubject(subject)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{subject}")
    public ResponseEntity<Void> deleteSchema(@PathVariable String subject) {
        schemaService.getSchemaBySubject(subject).ifPresent(schema -> {
            String latestSchema = schema.getVersions().isEmpty() ? null :
                    schema.getVersions().get(schema.getVersions().size() - 1).getSchemaText();
            auditService.logSchemaDeleted(subject, latestSchema, "system");
        });
        schemaService.deleteSchema(subject);
        return ResponseEntity.noContent().build();
    }

    @PutMapping("/{subject}/compatibility")
    public ResponseEntity<SchemaEntity> updateCompatibility(
            @PathVariable String subject,
            @RequestBody Map<String, CompatibilityLevel> body) {
        CompatibilityLevel oldLevel = schemaService.getSchemaBySubject(subject)
                .map(SchemaEntity::getCompatibilityLevel)
                .orElse(null);
        SchemaEntity updated = schemaService.updateCompatibility(subject, body.get("level"));
        auditService.logCompatibilityUpdated(subject,
                oldLevel != null ? oldLevel.name() : null,
                updated.getCompatibilityLevel().name(),
                "system");
        return ResponseEntity.ok(updated);
    }

    @PostMapping("/{subject}/versions")
    public ResponseEntity<SchemaVersion> addVersion(
            @PathVariable String subject,
            @Valid @RequestBody SchemaRequest request) {
        String oldSchema = schemaService.getVersionsBySubject(subject).stream()
                .findFirst()
                .map(SchemaVersion::getSchemaText)
                .orElse(null);

        SchemaVersion version = schemaService.addVersion(subject, request);

        CompatibilityResult compatResult = schemaService.checkCompatibility(
                request.getType(),
                oldSchema,
                version.getSchemaText(),
                request.getCompatibilityLevel()
        );

        auditService.logVersionAdded(subject, version.getVersion(), oldSchema,
                version.getSchemaText(), "system", compatResult.isCompatible());

        return ResponseEntity.ok(version);
    }

    @GetMapping("/{subject}/versions")
    public ResponseEntity<List<SchemaVersion>> getVersions(@PathVariable String subject) {
        return ResponseEntity.ok(schemaService.getVersionsBySubject(subject));
    }

    @GetMapping("/{subject}/versions/{version}")
    public ResponseEntity<SchemaVersion> getVersion(
            @PathVariable String subject,
            @PathVariable Integer version) {
        return schemaService.getVersion(subject, version)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/compatibility/check")
    public ResponseEntity<CompatibilityResult> checkCompatibility(
            @Valid @RequestBody CompatibilityCheckRequest request) {
        return ResponseEntity.ok(schemaService.checkCompatibility(
                request.getType(),
                request.getOldSchema(),
                request.getNewSchema(),
                request.getLevel()
        ));
    }

    @GetMapping("/{subject}/diff")
    public ResponseEntity<SchemaDiff> compareVersions(
            @PathVariable String subject,
            @RequestParam Integer oldVersion,
            @RequestParam Integer newVersion) {
        return ResponseEntity.ok(schemaService.compareVersions(subject, oldVersion, newVersion));
    }

    @PostMapping("/diff")
    public ResponseEntity<SchemaDiff> compareSchemasDirect(
            @RequestParam SchemaType type,
            @RequestBody Map<String, String> body) {
        return ResponseEntity.ok(schemaService.compareSchemasDirect(
                type,
                body.get("oldSchema"),
                body.get("newSchema")
        ));
    }

    @PostMapping("/evolution/recommendation")
    public ResponseEntity<EvolutionRecommendation> getEvolutionRecommendation(
            @Valid @RequestBody CompatibilityCheckRequest request) {
        return ResponseEntity.ok(schemaService.getEvolutionRecommendation(
                request.getType(),
                request.getOldSchema(),
                request.getNewSchema(),
                request.getLevel()
        ));
    }

    @PostMapping("/{subject}/evolve")
    public ResponseEntity<EvolutionResult> autoEvolveSchema(
            @PathVariable String subject,
            @RequestBody Map<String, String> body) {
        String proposedSchema = body.get("schema");
        String username = body.getOrDefault("username", "system");
        return ResponseEntity.ok(evolutionService.autoEvolveSchema(subject, proposedSchema, username));
    }

    @PostMapping("/{subject}/evolve/preview")
    public ResponseEntity<EvolutionResult> previewEvolution(
            @PathVariable String subject,
            @RequestBody Map<String, String> body) {
        String proposedSchema = body.get("schema");
        return ResponseEntity.ok(evolutionService.previewEvolution(subject, proposedSchema));
    }

    @PostMapping("/{subject}/versions/{version}/code")
    public ResponseEntity<List<GeneratedCode>> generateCode(
            @PathVariable String subject,
            @PathVariable Integer version,
            @RequestParam(required = false) String language,
            @RequestParam(required = false) String packageName,
            @RequestParam(required = false) String className,
            @RequestParam(required = false, defaultValue = "system") String username) {

        SchemaVersion schemaVersion = schemaService.getVersion(subject, version)
                .orElseThrow(() -> new RuntimeException("Version not found"));

        SchemaEntity schema = schemaService.getSchemaBySubject(subject)
                .orElseThrow(() -> new RuntimeException("Schema not found"));

        List<GeneratedCode> codes;

        if (language != null) {
            GeneratedCode code = switch (language.toLowerCase()) {
                case "java" -> codeGenerationService.generateJavaCode(
                        schemaVersion.getSchemaText(), schema.getType(), className, packageName);
                case "python" -> codeGenerationService.generatePythonCode(
                        schemaVersion.getSchemaText(), schema.getType(), className);
                case "go" -> codeGenerationService.generateGoCode(
                        schemaVersion.getSchemaText(), schema.getType(), className);
                default -> throw new RuntimeException("Unsupported language: " + language);
            };
            codes = List.of(code);
        } else {
            codes = codeGenerationService.generateAllLanguages(
                    schemaVersion.getSchemaText(), schema.getType(), className, packageName);
        }

        auditService.logCodeGenerated(subject, version,
                language != null ? language : "all", username);

        return ResponseEntity.ok(codes);
    }

    @PostMapping("/code/generate")
    public ResponseEntity<List<GeneratedCode>> generateCodeDirect(
            @RequestParam SchemaType type,
            @RequestParam(required = false) String language,
            @RequestParam(required = false) String packageName,
            @RequestParam(required = false) String className,
            @RequestBody Map<String, String> body) {

        String schemaText = body.get("schema");
        List<GeneratedCode> codes;

        if (language != null) {
            GeneratedCode code = switch (language.toLowerCase()) {
                case "java" -> codeGenerationService.generateJavaCode(
                        schemaText, type, className, packageName);
                case "python" -> codeGenerationService.generatePythonCode(
                        schemaText, type, className);
                case "go" -> codeGenerationService.generateGoCode(
                        schemaText, type, className);
                default -> throw new RuntimeException("Unsupported language: " + language);
            };
            codes = List.of(code);
        } else {
            codes = codeGenerationService.generateAllLanguages(
                    schemaText, type, className, packageName);
        }

        return ResponseEntity.ok(codes);
    }

    @GetMapping("/{subject}/audit")
    public ResponseEntity<List<AuditLog>> getAuditLogs(
            @PathVariable String subject,
            @RequestParam(required = false) Integer version) {
        if (version != null) {
            return ResponseEntity.ok(auditService.getAuditLogsBySubjectAndVersion(subject, version));
        }
        return ResponseEntity.ok(auditService.getAuditLogsBySubject(subject));
    }

    @GetMapping("/audit")
    public ResponseEntity<List<AuditLog>> getAllAuditLogs(
            @RequestParam(required = false) String username,
            @RequestParam(required = false) AuditLog.AuditAction action,
            @RequestParam(required = false, defaultValue = "24") Integer recentHours) {

        if (username != null) {
            return ResponseEntity.ok(auditService.getAuditLogsByUsername(username));
        }
        if (action != null) {
            return ResponseEntity.ok(auditService.getAuditLogsByAction(action));
        }
        if (recentHours != null) {
            return ResponseEntity.ok(auditService.getRecentAuditLogs(recentHours));
        }
        return ResponseEntity.ok(auditService.getAllAuditLogs());
    }

    @GetMapping("/audit/{id}")
    public ResponseEntity<AuditLog> getAuditLogById(@PathVariable Long id) {
        return auditService.getAuditLogById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }
}
