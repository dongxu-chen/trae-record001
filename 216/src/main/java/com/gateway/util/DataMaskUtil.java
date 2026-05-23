package com.gateway.util;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.Arrays;
import java.util.List;
import java.util.regex.Pattern;

@Slf4j
@Component
@RequiredArgsConstructor
public class DataMaskUtil {

    private final ObjectMapper objectMapper;

    private static final Pattern ID_CARD_PATTERN = Pattern.compile("^[1-9]\\d{5}(18|19|20)\\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\\d|3[01])\\d{3}[\\dXx]$");
    private static final Pattern EMAIL_PATTERN = Pattern.compile("^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$");
    private static final Pattern BANK_CARD_PATTERN = Pattern.compile("^\\d{16,19}$");
    private static final Pattern MOBILE_PATTERN = Pattern.compile("^1[3-9]\\d{9}$");

    private static final List<String> ID_CARD_FIELDS = Arrays.asList("idcard", "idCard", "id_card", "identity", "identityCard", "身份证", "证件号");
    private static final List<String> EMAIL_FIELDS = Arrays.asList("email", "mail", "邮箱", "电子邮箱");
    private static final List<String> BANK_CARD_FIELDS = Arrays.asList("bankcard", "bankCard", "bank_card", "cardNumber", "cardNo", "银行卡", "卡号", "账号");
    private static final List<String> MOBILE_FIELDS = Arrays.asList("mobile", "phone", "telephone", "手机", "手机号", "电话");

    public String maskBody(String body, List<String> maskFields) {
        if (body == null || body.isEmpty() || maskFields == null || maskFields.isEmpty()) {
            return body;
        }

        try {
            JsonNode rootNode = objectMapper.readTree(body);
            maskJsonNode(rootNode, maskFields);
            return objectMapper.writeValueAsString(rootNode);
        } catch (Exception e) {
            log.debug("Failed to parse body as JSON, returning original");
            return maskPlainText(body, maskFields);
        }
    }

    private void maskJsonNode(JsonNode node, List<String> maskFields) {
        if (node.isObject()) {
            ObjectNode objectNode = (ObjectNode) node;
            objectNode.fields().forEachRemaining(entry -> {
                String fieldName = entry.getKey();
                JsonNode fieldValue = entry.getValue();

                if (maskFields.stream().anyMatch(fieldName::equalsIgnoreCase)) {
                    if (fieldValue.isTextual()) {
                        objectNode.put(fieldName, maskValueByField(fieldName, fieldValue.asText()));
                    }
                } else if (fieldValue.isContainerNode()) {
                    maskJsonNode(fieldValue, maskFields);
                }
            });
        } else if (node.isArray()) {
            node.forEach(child -> maskJsonNode(child, maskFields));
        }
    }

    private String maskPlainText(String body, List<String> maskFields) {
        String result = body;
        for (String field : maskFields) {
            String regex = "(\"" + field + "\"\\s*:\\s*\")([^\"]*)(\")";
            result = result.replaceAll(regex, matchResult -> {
                String value = matchResult.group(2);
                return "\"" + field + "\":\"" + maskValueByField(field, value) + "\"";
            });
        }
        return result;
    }

    private String maskValueByField(String fieldName, String value) {
        if (value == null || value.isEmpty()) {
            return value;
        }

        if (matchesAnyField(fieldName, ID_CARD_FIELDS) || ID_CARD_PATTERN.matcher(value).matches()) {
            return maskIdCard(value);
        }

        if (matchesAnyField(fieldName, EMAIL_FIELDS) || EMAIL_PATTERN.matcher(value).matches()) {
            return maskEmail(value);
        }

        if (matchesAnyField(fieldName, BANK_CARD_FIELDS) || BANK_CARD_PATTERN.matcher(value).matches()) {
            return maskBankCard(value);
        }

        if (matchesAnyField(fieldName, MOBILE_FIELDS) || MOBILE_PATTERN.matcher(value).matches()) {
            return maskMobile(value);
        }

        return maskDefault(value);
    }

    private boolean matchesAnyField(String fieldName, List<String> fieldList) {
        return fieldList.stream()
                .anyMatch(field -> fieldName.toLowerCase().contains(field.toLowerCase()));
    }

    private String maskIdCard(String idCard) {
        if (idCard == null || idCard.length() < 8) {
            return "***";
        }
        int length = idCard.length();
        return idCard.substring(0, 6) + "********" + idCard.substring(length - 4);
    }

    private String maskEmail(String email) {
        if (email == null || !email.contains("@")) {
            return maskDefault(email);
        }
        int atIndex = email.indexOf("@");
        String username = email.substring(0, atIndex);
        String domain = email.substring(atIndex);

        if (username.length() <= 2) {
            return "***" + domain;
        }

        return username.charAt(0) + "***" + username.charAt(username.length() - 1) + domain;
    }

    private String maskBankCard(String bankCard) {
        if (bankCard == null || bankCard.length() < 8) {
            return "***";
        }
        int length = bankCard.length();
        return bankCard.substring(0, 6) + "****" + bankCard.substring(length - 4);
    }

    private String maskMobile(String mobile) {
        if (mobile == null || mobile.length() < 7) {
            return "***";
        }
        int length = mobile.length();
        return mobile.substring(0, 3) + "****" + mobile.substring(length - 4);
    }

    private String maskDefault(String value) {
        if (value == null || value.length() <= 2) {
            return "***";
        }
        int length = value.length();
        int maskLength = Math.min(length / 2, 10);
        int start = (length - maskLength) / 2;
        StringBuilder sb = new StringBuilder(value);
        for (int i = start; i < start + maskLength; i++) {
            sb.setCharAt(i, '*');
        }
        return sb.toString();
    }
}
