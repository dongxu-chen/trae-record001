package com.datasecurity.masking;

import com.datasecurity.masking.enums.SensitiveType;
import com.datasecurity.masking.label.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
class DataLabelTest {

    @Autowired
    private LabelPropagationEngine propagationEngine;

    @Autowired
    private ExportFileLabeler fileLabeler;

    @BeforeEach
    void setUp() {
        propagationEngine.clearAllLabels();
    }

    @Test
    void testSensitivityLevelOrder() {
        assertTrue(SensitivityLevel.TOP_SECRET.isMoreSensitiveThan(SensitivityLevel.SECRET));
        assertTrue(SensitivityLevel.SECRET.isMoreSensitiveThan(SensitivityLevel.CONFIDENTIAL));
        assertTrue(SensitivityLevel.CONFIDENTIAL.isMoreSensitiveThan(SensitivityLevel.INTERNAL));
        assertTrue(SensitivityLevel.INTERNAL.isMoreSensitiveThan(SensitivityLevel.PUBLIC));

        assertEquals(0, SensitivityLevel.PUBLIC.getLevel());
        assertEquals(4, SensitivityLevel.TOP_SECRET.getLevel());
    }

    @Test
    void testSensitivityLevelFromLevel() {
        assertEquals(SensitivityLevel.PUBLIC, SensitivityLevel.fromLevel(0));
        assertEquals(SensitivityLevel.INTERNAL, SensitivityLevel.fromLevel(1));
        assertEquals(SensitivityLevel.CONFIDENTIAL, SensitivityLevel.fromLevel(2));
        assertEquals(SensitivityLevel.SECRET, SensitivityLevel.fromLevel(3));
        assertEquals(SensitivityLevel.TOP_SECRET, SensitivityLevel.fromLevel(4));
        assertEquals(SensitivityLevel.PUBLIC, SensitivityLevel.fromLevel(999));
    }

    @Test
    void testCreateFieldLabel() {
        FieldLabel label = propagationEngine.createFieldLabel(
                "users", "phone", SensitiveType.PHONE, SensitivityLevel.CONFIDENTIAL);

        assertNotNull(label);
        assertEquals("users.phone", label.getId());
        assertEquals("phone", label.getName());
        assertEquals(SensitiveType.PHONE, label.getSensitiveType());
        assertEquals(SensitivityLevel.CONFIDENTIAL, label.getSensitivityLevel());
        assertEquals("FIELD", label.getDataType());
    }

    @Test
    void testGetFieldLabel() {
        propagationEngine.createFieldLabel("users", "id_card", SensitiveType.ID_CARD, SensitivityLevel.SECRET);

        FieldLabel label = propagationEngine.getFieldLabel("users", "id_card");
        assertNotNull(label);
        assertEquals(SensitiveType.ID_CARD, label.getSensitiveType());

        label = propagationEngine.getFieldLabel("users.id_card");
        assertNotNull(label);

        label = propagationEngine.getFieldLabel("users", "unknown");
        assertNull(label);
    }

    @Test
    void testLabelPropagation() {
        propagationEngine.createFieldLabel("users", "phone", SensitiveType.PHONE, SensitivityLevel.CONFIDENTIAL);

        propagationEngine.propagateLabel("users.phone", "user_profiles.contact_phone");

        FieldLabel targetLabel = propagationEngine.getFieldLabel("user_profiles.contact_phone");
        assertNotNull(targetLabel);
        assertEquals(SensitiveType.PHONE, targetLabel.getSensitiveType());
        assertEquals(SensitivityLevel.CONFIDENTIAL, targetLabel.getSensitivityLevel());
        assertEquals("propagated_from:users.phone", targetLabel.getSource());
    }

    @Test
    void testCalculateDataSetLevel() {
        FieldLabel label1 = new FieldLabel("users", "name", SensitiveType.NAME, SensitivityLevel.CONFIDENTIAL);
        FieldLabel label2 = new FieldLabel("users", "id_card", SensitiveType.ID_CARD, SensitivityLevel.SECRET);
        FieldLabel label3 = new FieldLabel("users", "phone", SensitiveType.PHONE, SensitivityLevel.CONFIDENTIAL);

        java.util.List<FieldLabel> labels = java.util.List.of(label1, label2, label3);
        SensitivityLevel level = propagationEngine.calculateDataSetLevel(labels);

        assertEquals(SensitivityLevel.SECRET, level);
    }

    @Test
    void testAnalyzeContent() {
        String content = "name,phone,id_card\n张三,13800138000,110101199001011234\n李四,13900139000,310101199203045678";

        FileLabel fileLabel = fileLabeler.analyzeContent(content, "CSV");

        assertNotNull(fileLabel);
        assertEquals("CSV", fileLabel.getFileType());
        assertTrue(fileLabel.getSensitiveFieldCount() > 0);
        assertTrue(fileLabel.getOverallLevel().isMoreSensitiveThan(SensitivityLevel.PUBLIC));

        System.out.println("Overall sensitivity level: " + fileLabel.getOverallLevel().getName());
        System.out.println("Sensitive fields found: " + fileLabel.getSensitiveFieldCount());
    }

    @Test
    void testGenerateSensitivityMark() {
        FileLabel fileLabel = new FileLabel("test.csv", "CSV");
        fileLabel.addSensitiveField(new FieldLabel("users", "phone", SensitiveType.PHONE, SensitivityLevel.CONFIDENTIAL));
        fileLabel.addSensitiveField(new FieldLabel("users", "id_card", SensitiveType.ID_CARD, SensitivityLevel.SECRET));

        String mark = fileLabeler.generateSensitivityMark(fileLabel);

        assertNotNull(mark);
        assertTrue(mark.contains("数据敏感等级"));
        assertTrue(mark.contains(SensitivityLevel.SECRET.getName()));
        assertTrue(mark.contains("phone"));
        assertTrue(mark.contains("id_card"));

        System.out.println(mark);
    }

    @Test
    void testGetAllFieldLabels() {
        propagationEngine.createFieldLabel("users", "phone", SensitiveType.PHONE, SensitivityLevel.CONFIDENTIAL);
        propagationEngine.createFieldLabel("users", "name", SensitiveType.NAME, SensitivityLevel.CONFIDENTIAL);
        propagationEngine.createFieldLabel("orders", "bank_card", SensitiveType.BANK_CARD, SensitivityLevel.SECRET);

        Map<String, FieldLabel> allLabels = propagationEngine.getAllFieldLabels();
        assertEquals(3, allLabels.size());
        assertTrue(allLabels.containsKey("users.phone"));
        assertTrue(allLabels.containsKey("users.name"));
        assertTrue(allLabels.containsKey("orders.bank_card"));
    }

    @Test
    void testRemoveFieldLabel() {
        propagationEngine.createFieldLabel("users", "phone", SensitiveType.PHONE, SensitivityLevel.CONFIDENTIAL);
        assertNotNull(propagationEngine.getFieldLabel("users.phone"));

        propagationEngine.removeFieldLabel("users.phone");
        assertNull(propagationEngine.getFieldLabel("users.phone"));
    }

    @Test
    void testClearAllLabels() {
        propagationEngine.createFieldLabel("users", "phone", SensitiveType.PHONE, SensitivityLevel.CONFIDENTIAL);
        propagationEngine.createFieldLabel("users", "name", SensitiveType.NAME, SensitivityLevel.CONFIDENTIAL);

        assertEquals(2, propagationEngine.getAllFieldLabels().size());

        propagationEngine.clearAllLabels();
        assertEquals(0, propagationEngine.getAllFieldLabels().size());
    }
}
