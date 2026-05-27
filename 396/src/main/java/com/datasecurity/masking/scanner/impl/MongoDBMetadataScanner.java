package com.datasecurity.masking.scanner.impl;

import com.datasecurity.masking.enums.DatabaseType;
import com.datasecurity.masking.enums.SensitiveType;
import com.datasecurity.masking.model.DatabaseConfig;
import com.datasecurity.masking.model.SensitiveField;
import com.datasecurity.masking.recognizer.SensitiveFieldRecognizer;
import com.datasecurity.masking.scanner.MetadataScanner;
import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoClients;
import com.mongodb.client.MongoCollection;
import com.mongodb.client.MongoDatabase;
import lombok.extern.slf4j.Slf4j;
import org.bson.Document;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.*;

@Slf4j
@Component
public class MongoDBMetadataScanner implements MetadataScanner {

    @Autowired
    private SensitiveFieldRecognizer recognizer;

    private static final int SAMPLE_SIZE = 100;

    @Override
    public boolean support(DatabaseConfig config) {
        return DatabaseType.MONGODB.equals(config.getType());
    }

    @Override
    public List<SensitiveField> scan(DatabaseConfig config) {
        List<SensitiveField> sensitiveFields = new ArrayList<>();
        String connectionString = buildConnectionString(config);

        try (MongoClient mongoClient = MongoClients.create(connectionString)) {
            MongoDatabase database = mongoClient.getDatabase(config.getDatabase());

            for (String collectionName : database.listCollectionNames()) {
                MongoCollection<Document> collection = database.getCollection(collectionName);
                Set<String> fieldNames = extractFieldNames(collection);

                for (String fieldName : fieldNames) {
                    SensitiveType sensitiveType = recognizer.recognizeByColumnName(fieldName, null);

                    if (!SensitiveType.UNKNOWN.equals(sensitiveType)) {
                        sensitiveFields.add(SensitiveField.builder()
                                .tableName(collectionName)
                                .columnName(fieldName)
                                .sensitiveType(sensitiveType)
                                .build());
                        log.info("Found sensitive field in MongoDB: {}.{} -> {}", collectionName, fieldName, sensitiveType);
                    } else {
                        SensitiveType valueSensitiveType = recognizeBySampleValue(collection, fieldName);
                        if (!SensitiveType.UNKNOWN.equals(valueSensitiveType)) {
                            sensitiveFields.add(SensitiveField.builder()
                                    .tableName(collectionName)
                                    .columnName(fieldName)
                                    .sensitiveType(valueSensitiveType)
                                    .build());
                            log.info("Found sensitive field by value in MongoDB: {}.{} -> {}",
                                    collectionName, fieldName, valueSensitiveType);
                        }
                    }
                }
            }
        } catch (Exception e) {
            log.error("Failed to scan MongoDB metadata for database: {}", config.getName(), e);
            throw new RuntimeException("Failed to scan MongoDB metadata", e);
        }

        return sensitiveFields;
    }

    private Set<String> extractFieldNames(MongoCollection<Document> collection) {
        Set<String> fieldNames = new HashSet<>();
        for (Document doc : collection.find().limit(SAMPLE_SIZE)) {
            extractFieldNamesFromDocument(doc, "", fieldNames);
        }
        return fieldNames;
    }

    private void extractFieldNamesFromDocument(Document doc, String prefix, Set<String> fieldNames) {
        for (Map.Entry<String, Object> entry : doc.entrySet()) {
            String fieldName = prefix.isEmpty() ? entry.getKey() : prefix + "." + entry.getKey();
            Object value = entry.getValue();

            if (value instanceof Document) {
                extractFieldNamesFromDocument((Document) value, fieldName, fieldNames);
            } else if (value instanceof List) {
                fieldNames.add(fieldName);
            } else {
                fieldNames.add(fieldName);
            }
        }
    }

    private SensitiveType recognizeBySampleValue(MongoCollection<Document> collection, String fieldName) {
        for (Document doc : collection.find().limit(SAMPLE_SIZE)) {
            Object value = getNestedValue(doc, fieldName);
            if (value instanceof String) {
                SensitiveType type = recognizer.recognizeByValue((String) value);
                if (!SensitiveType.UNKNOWN.equals(type)) {
                    return type;
                }
            }
        }
        return SensitiveType.UNKNOWN;
    }

    private Object getNestedValue(Document doc, String fieldName) {
        String[] parts = fieldName.split("\\.");
        Object current = doc;
        for (String part : parts) {
            if (current instanceof Document) {
                current = ((Document) current).get(part);
            } else {
                return null;
            }
        }
        return current;
    }

    private String buildConnectionString(DatabaseConfig config) {
        if (config.getConnectionUrl() != null && !config.getConnectionUrl().isEmpty()) {
            return config.getConnectionUrl();
        }
        if (config.getUsername() != null && !config.getUsername().isEmpty()) {
            return String.format("mongodb://%s:%s@%s:%d/%s",
                    config.getUsername(), config.getPassword(), config.getHost(), config.getPort(), config.getDatabase());
        }
        return String.format("mongodb://%s:%d/%s", config.getHost(), config.getPort(), config.getDatabase());
    }
}
