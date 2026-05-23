package com.log.collector.interceptor;

import com.log.collector.util.MaskingRuleManager;
import org.apache.flume.Context;
import org.apache.flume.Event;
import org.apache.flume.event.SimpleEvent;
import org.junit.Before;
import org.junit.Test;

import java.io.File;
import java.io.FileWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.HashMap;

import static org.junit.Assert.*;

public class DataMaskingInterceptorTest {

    private String tempConfigFile;

    @Before
    public void setUp() throws Exception {
        File tempFile = File.createTempFile("masking-rules-", ".json");
        tempFile.deleteOnExit();
        tempConfigFile = tempFile.getAbsolutePath();

        String defaultRules = "{\n" +
                "  \"rules\": [\n" +
                "    {\n" +
                "      \"name\": \"phone\",\n" +
                "      \"pattern\": \"(?<!\\\\d)(1[3-9]\\\\d{9})(?!\\\\d)\",\n" +
                "      \"maskChar\": \"*\",\n" +
                "      \"keepPrefix\": 3,\n" +
                "      \"keepSuffix\": 4,\n" +
                "      \"enabled\": true\n" +
                "    },\n" +
                "    {\n" +
                "      \"name\": \"idcard\",\n" +
                "      \"pattern\": \"(?<!\\\\d)([1-9]\\\\d{5}(19|20)\\\\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\\\\d|3[01])\\\\d{3}[\\\\dXx])(?!\\\\d)\",\n" +
                "      \"maskChar\": \"*\",\n" +
                "      \"keepPrefix\": 6,\n" +
                "      \"keepSuffix\": 4,\n" +
                "      \"enabled\": true\n" +
                "    },\n" +
                "    {\n" +
                "      \"name\": \"email\",\n" +
                "      \"pattern\": \"(?<![a-zA-Z0-9._-])([a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\\\\.[a-zA-Z]{2,})(?![a-zA-Z0-9._-])\",\n" +
                "      \"maskChar\": \"*\",\n" +
                "      \"keepPrefix\": 1,\n" +
                "      \"keepSuffix\": 1,\n" +
                "      \"enabled\": true\n" +
                "    }\n" +
                "  ]\n" +
                "}";

        try (FileWriter writer = new FileWriter(tempFile)) {
            writer.write(defaultRules);
        }
    }

    @Test
    public void testPhoneMasking() {
        Context context = new Context();
        context.put("maskBody", "true");
        context.put("configFilePath", tempConfigFile);
        context.put("enableHotReload", "false");

        DataMaskingInterceptor.Builder builder = new DataMaskingInterceptor.Builder();
        builder.configure(context);
        DataMaskingInterceptor interceptor = (DataMaskingInterceptor) builder.build();

        Event event = new SimpleEvent();
        event.setBody("用户手机号: 13812345678".getBytes(StandardCharsets.UTF_8));

        Event result = interceptor.intercept(event);
        String body = new String(result.getBody(), StandardCharsets.UTF_8);

        assertTrue("手机号应该被脱敏", body.contains("138****5678"));
        assertFalse("原始手机号不应该出现", body.contains("13812345678"));
    }

    @Test
    public void testIdCardMasking() {
        Context context = new Context();
        context.put("maskBody", "true");
        context.put("configFilePath", tempConfigFile);
        context.put("enableHotReload", "false");

        DataMaskingInterceptor.Builder builder = new DataMaskingInterceptor.Builder();
        builder.configure(context);
        DataMaskingInterceptor interceptor = (DataMaskingInterceptor) builder.build();

        Event event = new SimpleEvent();
        event.setBody("身份证号: 110101199001011234".getBytes(StandardCharsets.UTF_8));

        Event result = interceptor.intercept(event);
        String body = new String(result.getBody(), StandardCharsets.UTF_8);

        assertTrue("身份证应该被脱敏", body.contains("110101********1234"));
    }

    @Test
    public void testMultipleSensitiveData() {
        Context context = new Context();
        context.put("maskBody", "true");
        context.put("configFilePath", tempConfigFile);
        context.put("enableHotReload", "false");

        DataMaskingInterceptor.Builder builder = new DataMaskingInterceptor.Builder();
        builder.configure(context);
        DataMaskingInterceptor interceptor = (DataMaskingInterceptor) builder.build();

        String input = "用户信息: 张三, 手机: 13987654321, 身份证: 310101198505057890, 邮箱: zhangsan@test.com";
        Event event = new SimpleEvent();
        event.setBody(input.getBytes(StandardCharsets.UTF_8));

        Event result = interceptor.intercept(event);
        String body = new String(result.getBody(), StandardCharsets.UTF_8);

        assertTrue(body.contains("139****4321"));
        assertTrue(body.contains("310101********7890"));
    }

    @Test
    public void testHeaderMasking() {
        Context context = new Context();
        context.put("maskBody", "false");
        context.put("maskFields", "phone,idcard");
        context.put("configFilePath", tempConfigFile);
        context.put("enableHotReload", "false");

        DataMaskingInterceptor.Builder builder = new DataMaskingInterceptor.Builder();
        builder.configure(context);
        DataMaskingInterceptor interceptor = (DataMaskingInterceptor) builder.build();

        Event event = new SimpleEvent();
        event.setHeaders(new HashMap<String, String>() {{
            put("phone", "13812345678");
            put("idcard", "110101199001011234");
            put("name", "张三");
        }});
        event.setBody("原始内容不处理".getBytes(StandardCharsets.UTF_8));

        Event result = interceptor.intercept(event);

        assertEquals("138****5678", result.getHeaders().get("phone"));
        assertEquals("110101********1234", result.getHeaders().get("idcard"));
        assertEquals("张三", result.getHeaders().get("name"));
    }

    @Test
    public void testDynamicRuleReload() throws Exception {
        MaskingRuleManager manager = MaskingRuleManager.getInstance();
        manager.init(tempConfigFile, false);

        String input = "手机号: 13812345678";
        String masked = manager.applyMasking(input);
        assertTrue("手机号应该被脱敏", masked.contains("138****5678"));

        String newRules = "{\n" +
                "  \"rules\": [\n" +
                "    {\n" +
                "      \"name\": \"phone\",\n" +
                "      \"pattern\": \"(?<!\\\\d)(1[3-9]\\\\d{9})(?!\\\\d)\",\n" +
                "      \"maskChar\": \"#\",\n" +
                "      \"keepPrefix\": 3,\n" +
                "      \"keepSuffix\": 4,\n" +
                "      \"enabled\": true\n" +
                "    }\n" +
                "  ]\n" +
                "}";

        try (FileWriter writer = new FileWriter(tempConfigFile)) {
            writer.write(newRules);
        }

        manager.reload();

        String masked2 = manager.applyMasking(input);
        assertTrue("应该使用新的脱敏字符#", masked2.contains("138####5678"));
    }
}
