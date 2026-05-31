package com.schemaregistry.service;

import com.schemaregistry.model.*;
import com.schemaregistry.util.StringSimilarity;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class EvolutionRecommendationService {

    private static final double RENAME_CONFIDENCE_THRESHOLD = 0.75;

    public EvolutionRecommendation generateRecommendation(SchemaDiff diff, SchemaType type, CompatibilityResult compatibility) {
        List<String> steps = new ArrayList<>();
        List<String> warnings = new ArrayList<>();
        List<String> detectedRenames = new ArrayList<>();
        List<String> safeAdditions = new ArrayList<>();
        List<String> breakingChanges = new ArrayList<>();
        StringBuilder recommendation = new StringBuilder();
        String impact = "LOW";
        CompatibilityLevel suggestedLevel = CompatibilityLevel.BACKWARD;

        if (diff.getRenames() != null && !diff.getRenames().isEmpty()) {
            for (DiffEntry rename : diff.getRenames()) {
                String renameInfo = String.format("%s -> %s (confidence: %.1f%%)",
                        rename.getOldFieldName(),
                        rename.getNewFieldName(),
                        rename.getRenameConfidence() * 100);
                detectedRenames.add(renameInfo);
                warnings.add("Suspected field rename detected: " + renameInfo);
            }
        }

        if (diff.getAdditions() != null) {
            for (DiffEntry addition : diff.getAdditions()) {
                if (addition.isHasDefault()) {
                    safeAdditions.add(addition.getField() + " (with default value)");
                } else {
                    safeAdditions.add(addition.getField());
                }
            }
        }

        int breakingChangesCount = countBreakingChanges(diff, type, breakingChanges);
        boolean hasRenames = detectedRenames.size() > 0;

        if (breakingChangesCount > 0 || hasRenames) {
            if (breakingChangesCount > 0) {
                impact = "HIGH";
                recommendation.append("This schema evolution contains breaking changes. ");
            } else {
                impact = "MEDIUM";
                recommendation.append("This schema evolution contains suspected renames. ");
            }
            suggestedLevel = CompatibilityLevel.NONE;

            warnings.add(0, "Breaking changes detected. Old consumers may fail to read new data.");
            steps.add("Coordinate with all consumers before deploying the new schema");

            if (hasRenames) {
                steps.add(1, "Verify detected renames are intentional and update all references");
                steps.add(2, "Consider adding aliases for renamed fields if supported by the schema type");
            }

            steps.add("Consider versioning your topic or creating a new subject");
            steps.add("Update consumer applications to handle both old and new formats during transition");
        } else if (!diff.getAdditions().isEmpty() || !diff.getModifications().isEmpty()) {
            impact = "MEDIUM";
            recommendation.append("This schema evolution is backward-compatible but requires attention. ");
            suggestedLevel = CompatibilityLevel.BACKWARD;

            steps.add("Deploy producer changes first");
            steps.add("Verify consumer applications can handle new fields");
            steps.add("Monitor system for any deserialization errors");

            if (!safeAdditions.isEmpty()) {
                recommendation.append("New fields added: ").append(String.join(", ", safeAdditions)).append(". ");
            }
        } else {
            recommendation.append("This schema evolution appears safe with minimal changes. ");
            steps.add("Proceed with standard deployment process");
        }

        if (!compatibility.isCompatible()) {
            impact = "CRITICAL";
            recommendation.insert(0, "COMPATIBILITY CHECK FAILED! ");
            warnings.add(0, "Schema compatibility validation failed: " + compatibility.getErrors());
            steps.add(0, "Resolve compatibility issues before proceeding");
        }

        addTypeSpecificRecommendations(diff, type, steps, warnings);

        return EvolutionRecommendation.builder()
                .recommendation(recommendation.toString())
                .impact(impact)
                .steps(steps)
                .suggestedCompatibility(suggestedLevel)
                .warnings(warnings)
                .detectedRenames(detectedRenames)
                .safeAdditions(safeAdditions)
                .breakingChanges(breakingChanges)
                .build();
    }

    public List<String> detectPotentialRenames(List<String> oldFieldNames, List<String> newFieldNames) {
        List<String> potentialRenames = new ArrayList<>();
        Map<String, String> bestMatches = new HashMap<>();
        Map<String, Double> matchScores = new HashMap<>();

        for (String oldName : oldFieldNames) {
            if (newFieldNames.contains(oldName)) {
                continue;
            }

            double bestScore = 0;
            String bestMatch = null;

            for (String newName : newFieldNames) {
                if (oldFieldNames.contains(newName)) {
                    continue;
                }

                double similarity = StringSimilarity.calculateCombinedSimilarity(oldName, newName);
                if (similarity > bestScore && similarity >= RENAME_CONFIDENCE_THRESHOLD) {
                    bestScore = similarity;
                    bestMatch = newName;
                }
            }

            if (bestMatch != null) {
                if (!matchScores.containsKey(bestMatch) || bestScore > matchScores.get(bestMatch)) {
                    bestMatches.put(oldName, bestMatch);
                    matchScores.put(bestMatch, bestScore);
                }
            }
        }

        for (Map.Entry<String, String> entry : bestMatches.entrySet()) {
            String oldName = entry.getKey();
            String newName = entry.getValue();
            double confidence = matchScores.get(newName);
            potentialRenames.add(String.format("%s -> %s (confidence: %.1f%%)",
                    oldName, newName, confidence * 100));
        }

        return potentialRenames;
    }

    private int countBreakingChanges(SchemaDiff diff, SchemaType type, List<String> breakingChanges) {
        int breakingCount = 0;

        if (diff.getDeletions() != null) {
            for (DiffEntry deletion : diff.getDeletions()) {
                if (isBreakingChange(deletion, type)) {
                    breakingCount++;
                    breakingChanges.add("Breaking change: " + deletion.getField() + " removed");
                }
            }
        }

        if (diff.getModifications() != null) {
            for (DiffEntry modification : diff.getModifications()) {
                if (isBreakingModification(modification, type)) {
                    breakingCount++;
                    breakingChanges.add("Breaking change: " + modification.getField() +
                            " modified (" + modification.getOldValue() + " -> " + modification.getNewValue() + ")");
                }
            }
        }

        if (diff.getAdditions() != null) {
            for (DiffEntry addition : diff.getAdditions()) {
                if (!addition.isHasDefault() && isBreakingAddition(addition, type)) {
                    breakingCount++;
                    breakingChanges.add("Breaking change: " + addition.getField() +
                            " added as required without default value");
                }
            }
        }

        return breakingCount;
    }

    private boolean isBreakingChange(DiffEntry entry, SchemaType type) {
        String description = entry.getDescription() != null ? entry.getDescription().toLowerCase() : "";
        String oldValue = entry.getOldValue() != null ? entry.getOldValue().toLowerCase() : "";

        if (oldValue.contains("required") || description.contains("required")) {
            return true;
        }

        if (type == SchemaType.PROTOBUF) {
            return true;
        }

        return false;
    }

    private boolean isBreakingModification(DiffEntry entry, SchemaType type) {
        String oldValue = entry.getOldValue() != null ? entry.getOldValue().toLowerCase() : "";
        String newValue = entry.getNewValue() != null ? entry.getNewValue().toLowerCase() : "";

        if (oldValue.contains("optional") && newValue.contains("required")) {
            return true;
        }

        if (oldValue.contains("string") && !newValue.contains("string")) {
            return true;
        }

        if (entry.getType() == DiffEntry.DiffType.TYPE_CHANGED) {
            return !isCompatibleTypeChange(oldValue, newValue);
        }

        return false;
    }

    private boolean isBreakingAddition(DiffEntry entry, SchemaType type) {
        String description = entry.getDescription() != null ? entry.getDescription().toLowerCase() : "";
        return description.contains("required") && !entry.isHasDefault();
    }

    private boolean isCompatibleTypeChange(String oldType, String newType) {
        Map<String, List<String>> compatibleTypes = new HashMap<>();
        compatibleTypes.put("int", List.of("long", "float", "double"));
        compatibleTypes.put("long", List.of("float", "double"));
        compatibleTypes.put("float", List.of("double"));
        compatibleTypes.put("string", List.of());
        compatibleTypes.put("boolean", List.of());

        for (Map.Entry<String, List<String>> entry : compatibleTypes.entrySet()) {
            if (oldType.contains(entry.getKey())) {
                for (String compatible : entry.getValue()) {
                    if (newType.contains(compatible)) {
                        return true;
                    }
                }
            }
        }

        return oldType.equals(newType);
    }

    private void addTypeSpecificRecommendations(SchemaDiff diff, SchemaType type, List<String> steps, List<String> warnings) {
        switch (type) {
            case AVRO:
                steps.add("For Avro, ensure default values are provided for new fields in backward compatibility mode");
                steps.add("Consider using schema unions when changing field types");
                if (diff.getRenames() != null && !diff.getRenames().isEmpty()) {
                    steps.add("For renamed fields in Avro, use 'aliases' to maintain backward compatibility");
                }
                break;
            case PROTOBUF:
                steps.add("For Protobuf, never reuse field numbers");
                steps.add("Use 'optional' for new fields to maintain backward compatibility");
                if (diff.getRenames() != null && !diff.getRenames().isEmpty()) {
                    warnings.add("Protobuf uses field numbers for identification, renaming fields is safe if tag numbers are preserved");
                }
                break;
            case JSON_SCHEMA:
                steps.add("For JSON Schema, add new fields as optional or provide defaults");
                steps.add("Consider using 'additionalProperties' for flexibility");
                break;
        }
    }
}
