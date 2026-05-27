package com.datasecurity.masking.interceptor;

import com.datasecurity.masking.access.PermissionService;
import com.datasecurity.masking.access.UserContext;
import com.datasecurity.masking.access.UserContextHolder;
import com.datasecurity.masking.model.SensitiveField;
import com.datasecurity.masking.service.MetadataService;
import com.datasecurity.masking.strategy.MaskStrategyService;
import lombok.extern.slf4j.Slf4j;
import org.bson.Document;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

@Slf4j
@Component
public class MongoDBMaskInterceptor {

    @Autowired
    private MetadataService metadataService;

    @Autowired
    private MaskStrategyService maskStrategyService;

    @Autowired
    private PermissionService permissionService;

    public <T> List<T> findWithMasking(MongoTemplate mongoTemplate, Query query, Class<T> entityClass,
                                       String collectionName, String databaseId) {
        List<T> results = mongoTemplate.find(query, entityClass, collectionName);
        return maskResults(results, databaseId);
    }

    public Document findOneWithMasking(MongoTemplate mongoTemplate, Query query,
                                       String collectionName, String databaseId) {
        Document result = mongoTemplate.findOne(query, Document.class, collectionName);
        if (result == null) {
            return null;
        }
        return maskDocument(result, databaseId);
    }

    public List<Document> findAllWithMasking(MongoTemplate mongoTemplate,
                                             String collectionName, String databaseId) {
        List<Document> results = mongoTemplate.findAll(Document.class, collectionName);
        return maskDocuments(results, databaseId);
    }

    @SuppressWarnings("unchecked")
    private <T> List<T> maskResults(List<T> results, String databaseId) {
        if (results == null || results.isEmpty()) {
            return results;
        }

        UserContext user = UserContextHolder.get();
        if (!permissionService.needMasking(user)) {
            return results;
        }

        List<SensitiveField> sensitiveFields = metadataService.getSensitiveFields(databaseId);
        if (sensitiveFields == null || sensitiveFields.isEmpty()) {
            return results;
        }

        List<T> maskedResults = new ArrayList<>();
        for (T result : results) {
            if (result instanceof Document) {
                maskedResults.add((T) maskDocument((Document) result, sensitiveFields, user));
            } else {
                maskedResults.add(maskEntity(result, sensitiveFields, user));
            }
        }

        return maskedResults;
    }

    private List<Document> maskDocuments(List<Document> documents, String databaseId) {
        if (documents == null || documents.isEmpty()) {
            return documents;
        }

        UserContext user = UserContextHolder.get();
        if (!permissionService.needMasking(user)) {
            return documents;
        }

        List<SensitiveField> sensitiveFields = metadataService.getSensitiveFields(databaseId);
        if (sensitiveFields == null || sensitiveFields.isEmpty()) {
            return documents;
        }

        List<Document> maskedDocuments = new ArrayList<>();
        for (Document doc : documents) {
            maskedDocuments.add(maskDocument(doc, sensitiveFields, user));
        }

        return maskedDocuments;
    }

    private Document maskDocument(Document doc, String databaseId) {
        UserContext user = UserContextHolder.get();
        if (!permissionService.needMasking(user)) {
            return doc;
        }

        List<SensitiveField> sensitiveFields = metadataService.getSensitiveFields(databaseId);
        if (sensitiveFields == null || sensitiveFields.isEmpty()) {
            return doc;
        }

        return maskDocument(doc, sensitiveFields, user);
    }

    private Document maskDocument(Document doc, List<SensitiveField> sensitiveFields, UserContext user) {
        Document maskedDoc = new Document(doc);

        for (SensitiveField field : sensitiveFields) {
            String fieldName = field.getColumnName();
            Object value = getNestedValue(maskedDoc, fieldName);
            if (value instanceof String) {
                if (!permissionService.canViewSensitiveType(user, field.getSensitiveType())) {
                    String maskedValue = maskStrategyService.mask((String) value, field.getSensitiveType());
                    setNestedValue(maskedDoc, fieldName, maskedValue);
                }
            }
        }

        return maskedDoc;
    }

    @SuppressWarnings("unchecked")
    private <T> T maskEntity(T entity, List<SensitiveField> sensitiveFields, UserContext user) {
        try {
            for (SensitiveField field : sensitiveFields) {
                String fieldName = field.getColumnName();
                java.lang.reflect.Field entityField = findField(entity.getClass(), fieldName);
                if (entityField != null) {
                    entityField.setAccessible(true);
                    Object value = entityField.get(entity);
                    if (value instanceof String) {
                        if (!permissionService.canViewSensitiveType(user, field.getSensitiveType())) {
                            String maskedValue = maskStrategyService.mask((String) value, field.getSensitiveType());
                            entityField.set(entity, maskedValue);
                        }
                    }
                }
            }
        } catch (Exception e) {
            log.warn("Failed to mask entity of type: {}", entity.getClass().getName(), e);
        }
        return entity;
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

    private void setNestedValue(Document doc, String fieldName, Object value) {
        String[] parts = fieldName.split("\\.");
        Document current = doc;
        for (int i = 0; i < parts.length - 1; i++) {
            Object next = current.get(parts[i]);
            if (next instanceof Document) {
                current = (Document) next;
            } else {
                Document newDoc = new Document();
                current.put(parts[i], newDoc);
                current = newDoc;
            }
        }
        current.put(parts[parts.length - 1], value);
    }

    private java.lang.reflect.Field findField(Class<?> clazz, String fieldName) {
        Class<?> currentClass = clazz;
        while (currentClass != null && currentClass != Object.class) {
            try {
                return currentClass.getDeclaredField(fieldName);
            } catch (NoSuchFieldException e) {
                currentClass = currentClass.getSuperclass();
            }
        }
        return null;
    }
}
