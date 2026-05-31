package com.schemaregistry.service;

import com.schemaregistry.compatibility.CompatibilityChecker;
import com.schemaregistry.dto.SchemaRequest;
import com.schemaregistry.model.*;
import com.schemaregistry.repository.SchemaRepository;
import com.schemaregistry.repository.SchemaVersionRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

@Service
public class SchemaService {

    private final SchemaRepository schemaRepository;
    private final SchemaVersionRepository versionRepository;
    private final List<CompatibilityChecker> compatibilityCheckers;
    private final SchemaDiffService diffService;
    private final EvolutionRecommendationService recommendationService;

    @Autowired
    public SchemaService(SchemaRepository schemaRepository,
                         SchemaVersionRepository versionRepository,
                         List<CompatibilityChecker> compatibilityCheckers,
                         SchemaDiffService diffService,
                         EvolutionRecommendationService recommendationService) {
        this.schemaRepository = schemaRepository;
        this.versionRepository = versionRepository;
        this.compatibilityCheckers = compatibilityCheckers;
        this.diffService = diffService;
        this.recommendationService = recommendationService;
    }

    @Transactional
    public SchemaEntity createSchema(SchemaRequest request) {
        if (schemaRepository.existsBySubject(request.getSubject())) {
            throw new RuntimeException("Subject already exists: " + request.getSubject());
        }

        SchemaEntity schema = new SchemaEntity();
        schema.setSubject(request.getSubject());
        schema.setType(request.getType());
        schema.setCompatibilityLevel(request.getCompatibilityLevel() != null ?
                request.getCompatibilityLevel() : CompatibilityLevel.BACKWARD);

        SchemaVersion version = new SchemaVersion();
        version.setVersion(1);
        version.setSchemaText(request.getSchema());
        version.setDescription(request.getDescription());

        schema.addVersion(version);
        return schemaRepository.save(schema);
    }

    @Transactional
    public SchemaVersion addVersion(String subject, SchemaRequest request) {
        SchemaEntity schema = schemaRepository.findBySubject(subject)
                .orElseThrow(() -> new RuntimeException("Schema not found: " + subject));

        Integer maxVersion = versionRepository.findMaxVersionBySchemaId(schema.getId())
                .orElse(0);

        SchemaVersion newVersion = new SchemaVersion();
        newVersion.setVersion(maxVersion + 1);
        newVersion.setSchemaText(request.getSchema());
        newVersion.setDescription(request.getDescription());
        newVersion.setSchema(schema);

        return versionRepository.save(newVersion);
    }

    public List<SchemaEntity> getAllSchemas() {
        return schemaRepository.findAll();
    }

    public Optional<SchemaEntity> getSchemaBySubject(String subject) {
        return schemaRepository.findBySubject(subject);
    }

    public List<SchemaVersion> getVersionsBySubject(String subject) {
        return versionRepository.findBySubjectOrderByVersionDesc(subject);
    }

    public Optional<SchemaVersion> getVersion(String subject, Integer version) {
        return versionRepository.findBySubjectAndVersion(subject, version);
    }

    public CompatibilityResult checkCompatibility(SchemaType type, String oldSchema, String newSchema, CompatibilityLevel level) {
        CompatibilityChecker checker = findChecker(type.name());
        if (checker == null) {
            throw new RuntimeException("No compatibility checker found for type: " + type);
        }
        return checker.checkCompatibility(oldSchema, newSchema, level != null ? level : CompatibilityLevel.BACKWARD);
    }

    public SchemaDiff compareVersions(String subject, Integer oldVersion, Integer newVersion) {
        SchemaVersion oldVer = versionRepository.findBySubjectAndVersion(subject, oldVersion)
                .orElseThrow(() -> new RuntimeException("Version not found: " + oldVersion));
        SchemaVersion newVer = versionRepository.findBySubjectAndVersion(subject, newVersion)
                .orElseThrow(() -> new RuntimeException("Version not found: " + newVersion));

        SchemaEntity schema = schemaRepository.findBySubject(subject)
                .orElseThrow(() -> new RuntimeException("Schema not found: " + subject));

        return diffService.compareSchemas(
                oldVer.getSchemaText(),
                newVer.getSchemaText(),
                schema.getType(),
                oldVersion.toString(),
                newVersion.toString()
        );
    }

    public SchemaDiff compareSchemasDirect(SchemaType type, String oldSchema, String newSchema) {
        return diffService.compareSchemas(oldSchema, newSchema, type, "old", "new");
    }

    public EvolutionRecommendation getEvolutionRecommendation(SchemaType type, String oldSchema, String newSchema, CompatibilityLevel level) {
        SchemaDiff diff = diffService.compareSchemas(oldSchema, newSchema, type, "current", "proposed");
        CompatibilityResult compatibility = checkCompatibility(type, oldSchema, newSchema, level);
        return recommendationService.generateRecommendation(diff, type, compatibility);
    }

    @Transactional
    public void deleteSchema(String subject) {
        SchemaEntity schema = schemaRepository.findBySubject(subject)
                .orElseThrow(() -> new RuntimeException("Schema not found: " + subject));
        schemaRepository.delete(schema);
    }

    @Transactional
    public SchemaEntity updateCompatibility(String subject, CompatibilityLevel level) {
        SchemaEntity schema = schemaRepository.findBySubject(subject)
                .orElseThrow(() -> new RuntimeException("Schema not found: " + subject));
        schema.setCompatibilityLevel(level);
        return schemaRepository.save(schema);
    }

    private CompatibilityChecker findChecker(String type) {
        return compatibilityCheckers.stream()
                .filter(c -> c.supports(type))
                .findFirst()
                .orElse(null);
    }
}
