package com.log.mask.parser;

import com.log.mask.core.RegexMaskEngine;
import org.dom4j.*;
import org.dom4j.tree.DefaultText;

import java.util.*;

public class XmlLogParser implements LogParser {
    private final Set<String> sensitiveFields = new HashSet<>(Arrays.asList(
            "password", "pwd", "passwd", "pass",
            "idCard", "id_card", "idcard", "身份证",
            "phone", "mobile", "telephone", "手机号", "电话",
            "email", "邮箱",
            "bankCard", "bank_card", "银行卡",
            "name", "username", "姓名"
    ));

    @Override
    public String parseAndMask(String logContent, RegexMaskEngine maskEngine) {
        if (logContent == null || logContent.isEmpty()) {
            return logContent;
        }
        try {
            Document document = DocumentHelper.parseText(logContent);
            maskXmlElement(document.getRootElement(), maskEngine);
            return document.asXML();
        } catch (DocumentException e) {
            return maskEngine.mask(logContent);
        }
    }

    private void maskXmlElement(Element element, RegexMaskEngine maskEngine) {
        String elementName = element.getName();
        
        for (Object obj : element.attributes()) {
            Attribute attr = (Attribute) obj;
            String attrValue = attr.getValue();
            if (isSensitiveField(attr.getName()) || isSensitiveField(elementName)) {
                attr.setValue(maskEngine.mask(attrValue));
            } else {
                String maskedValue = maskEngine.mask(attrValue);
                if (!maskedValue.equals(attrValue)) {
                    attr.setValue(maskedValue);
                }
            }
        }

        List<Node> content = element.content();
        for (int i = 0; i < content.size(); i++) {
            Node node = content.get(i);
            if (node instanceof DefaultText) {
                String text = node.getText();
                if (isSensitiveField(elementName)) {
                    ((DefaultText) node).setText(maskEngine.mask(text));
                } else {
                    String maskedText = maskEngine.mask(text);
                    if (!maskedText.equals(text)) {
                        ((DefaultText) node).setText(maskedText);
                    }
                }
            } else if (node instanceof Element) {
                maskXmlElement((Element) node, maskEngine);
            }
        }
    }

    private boolean isSensitiveField(String name) {
        String lowerName = name.toLowerCase();
        for (String sensitive : sensitiveFields) {
            if (lowerName.contains(sensitive)) {
                return true;
            }
        }
        return false;
    }

    public void addSensitiveField(String fieldName) {
        sensitiveFields.add(fieldName.toLowerCase());
    }

    public void removeSensitiveField(String fieldName) {
        sensitiveFields.remove(fieldName.toLowerCase());
    }

    @Override
    public boolean supportFormat(String format) {
        return "xml".equalsIgnoreCase(format);
    }
}
