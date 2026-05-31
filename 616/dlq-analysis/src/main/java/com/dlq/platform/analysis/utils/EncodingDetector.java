package com.dlq.platform.analysis.utils;

import lombok.extern.slf4j.Slf4j;

import java.nio.ByteBuffer;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

@Slf4j
public class EncodingDetector {

    private static final List<Charset> TRY_CHARSETS = List.of(
            StandardCharsets.UTF_8,
            Charset.forName("GBK"),
            Charset.forName("GB2312"),
            Charset.forName("GB18030"),
            StandardCharsets.ISO_8859_1,
            StandardCharsets.US_ASCII,
            Charset.forName("UTF-16"),
            Charset.forName("UTF-16BE"),
            Charset.forName("UTF-16LE")
    );

    public static class EncodingResult {
        private final String decodedText;
        private final String charset;
        private final double confidence;
        private final boolean isValid;
        private final String errorMessage;

        public EncodingResult(String decodedText, String charset, double confidence, boolean isValid, String errorMessage) {
            this.decodedText = decodedText;
            this.charset = charset;
            this.confidence = confidence;
            this.isValid = isValid;
            this.errorMessage = errorMessage;
        }

        public String getDecodedText() { return decodedText; }
        public String getCharset() { return charset; }
        public double getConfidence() { return confidence; }
        public boolean isValid() { return isValid; }
        public String getErrorMessage() { return errorMessage; }
    }

    public static List<EncodingResult> tryDecode(byte[] data) {
        List<EncodingResult> results = new ArrayList<>();
        if (data == null || data.length == 0) {
            results.add(new EncodingResult("", StandardCharsets.UTF_8.name(), 1.0, true, "数据为空"));
            return results;
        }

        for (Charset charset : TRY_CHARSETS) {
            try {
                String decoded = decodeWithCharset(data, charset);
                double confidence = calculateConfidence(data, charset, decoded);
                boolean isValid = confidence > 0.5;
                results.add(new EncodingResult(decoded, charset.name(), confidence, isValid, null));
            } catch (Exception e) {
                results.add(new EncodingResult(null, charset.name(), 0.0, false, e.getMessage()));
            }
        }

        results.sort((a, b) -> Double.compare(b.getConfidence(), a.getConfidence()));
        return results;
    }

    public static EncodingResult tryDecodeString(String messageBody) {
        if (messageBody == null) {
            return new EncodingResult(null, null, 0.0, false, "消息体为空");
        }

        try {
            byte[] data = messageBody.getBytes(StandardCharsets.ISO_8859_1);
            List<EncodingResult> results = tryDecode(data);
            return results.isEmpty() ? new EncodingResult(messageBody, StandardCharsets.UTF_8.name(), 0.5, true, null) : results.get(0);
        } catch (Exception e) {
            return new EncodingResult(messageBody, StandardCharsets.UTF_8.name(), 0.5, true, e.getMessage());
        }
    }

    private static String decodeWithCharset(byte[] data, Charset charset) {
        ByteBuffer buffer = ByteBuffer.wrap(data);
        return charset.decode(buffer).toString();
    }

    private static double calculateConfidence(byte[] data, Charset charset, String decoded) {
        double score = 0.0;

        score += checkBom(data, charset) ? 30 : 0;
        score += checkValidCharacters(decoded) * 40;
        score += checkPrintableRatio(decoded) * 20;
        score += checkCommonChineseCharacters(decoded) * 10;

        return Math.min(score / 100.0, 1.0);
    }

    private static boolean checkBom(byte[] data, Charset charset) {
        if (data.length < 3) return false;

        if (charset.equals(StandardCharsets.UTF_8)) {
            return data[0] == (byte) 0xEF && data[1] == (byte) 0xBB && data[2] == (byte) 0xBF;
        } else if (charset.name().equals("UTF-16BE")) {
            return data[0] == (byte) 0xFE && data[1] == (byte) 0xFF;
        } else if (charset.name().equals("UTF-16LE")) {
            return data[0] == (byte) 0xFF && data[1] == (byte) 0xFE;
        }
        return false;
    }

    private static double checkValidCharacters(String decoded) {
        if (decoded == null || decoded.isEmpty()) return 0.5;

        int totalChars = decoded.length();
        int invalidChars = 0;

        for (int i = 0; i < decoded.length(); i++) {
            char c = decoded.charAt(i);
            if (c == '\uFFFD' || c == '\u0000') {
                invalidChars++;
            }
        }

        return totalChars > 0 ? (1.0 - (double) invalidChars / totalChars) : 0.5;
    }

    private static double checkPrintableRatio(String decoded) {
        if (decoded == null || decoded.isEmpty()) return 0.5;

        int totalChars = decoded.length();
        int printableChars = 0;

        for (int i = 0; i < decoded.length(); i++) {
            char c = decoded.charAt(i);
            if (Character.isLetterOrDigit(c) ||
                Character.isWhitespace(c) ||
                (c >= 0x20 && c <= 0x7E) ||
                (c >= 0x4E00 && c <= 0x9FFF) ||
                (c >= 0x3000 && c <= 0x303F) ||
                (c >= 0xFF00 && c <= 0xFFEF)) {
                printableChars++;
            }
        }

        return totalChars > 0 ? (double) printableChars / totalChars : 0.5;
    }

    private static double checkCommonChineseCharacters(String decoded) {
        if (decoded == null || decoded.isEmpty()) return 0.0;

        char[] commonChars = {'的', '一', '是', '在', '不', '了', '有', '和', '人', '这', '中', '大', '为', '上', '个', '国', '我', '以', '要', '他'};
        int found = 0;

        for (char c : commonChars) {
            if (decoded.indexOf(c) >= 0) {
                found++;
            }
        }

        return (double) found / commonChars.length;
    }

    public static String detectAndConvert(String messageBody) {
        if (messageBody == null) return null;

        EncodingResult result = tryDecodeString(messageBody);
        if (result.isValid() && result.getConfidence() > 0.7) {
            log.debug("检测到编码: {}, 置信度: {}", result.getCharset(), result.getConfidence());
            return result.getDecodedText();
        }
        return messageBody;
    }

    public static boolean isPotentialEncodingIssue(String messageBody) {
        if (messageBody == null || messageBody.isEmpty()) return false;

        int garbledCount = 0;
        for (int i = 0; i < messageBody.length(); i++) {
            char c = messageBody.charAt(i);
            if (c == '\uFFFD' || c == '\u0000' || (c >= 0x80 && c <= 0x9F)) {
                garbledCount++;
            }
        }

        return garbledCount > messageBody.length() * 0.1;
    }
}
