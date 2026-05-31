package com.log.mask;

import com.log.mask.core.RegexMaskEngine;
import com.log.mask.parser.JsonLogParser;
import com.log.mask.parser.LogParser;
import com.log.mask.parser.LogParserFactory;
import com.log.mask.parser.TextLogParser;
import com.log.mask.parser.XmlLogParser;
import org.junit.Before;
import org.junit.Test;
import static org.junit.Assert.*;

public class LogParserTest {
    private RegexMaskEngine engine;

    @Before
    public void setUp() {
        engine = new RegexMaskEngine();
    }

    @Test
    public void testTextLogParser() {
        LogParser parser = new TextLogParser();
        String input = "用户登录: 手机号=13812345678, 密码=123456";
        String result = parser.parseAndMask(input, engine);
        assertFalse(result.contains("13812345678"));
        assertFalse(result.contains("123456"));
        assertTrue(result.contains("手机号"));
    }

    @Test
    public void testJsonLogParser() {
        LogParser parser = new JsonLogParser();
        String input = "{\"username\":\"张三\",\"password\":\"secret\",\"phone\":\"13911112222\"}";
        String result = parser.parseAndMask(input, engine);
        assertFalse(result.contains("secret"));
        assertFalse(result.contains("13911112222"));
        assertTrue(result.contains("张三"));
        assertTrue(result.contains("username"));
    }

    @Test
    public void testXmlLogParser() {
        LogParser parser = new XmlLogParser();
        String input = "<log><user>李四</user><password>mypassword</password><phone>13733334444</phone></log>";
        String result = parser.parseAndMask(input, engine);
        assertFalse(result.contains("mypassword"));
        assertFalse(result.contains("13733334444"));
        assertTrue(result.contains("李四"));
        assertTrue(result.contains("<user>"));
    }

    @Test
    public void testLogParserFactory() {
        assertTrue(LogParserFactory.getParser("text") instanceof TextLogParser);
        assertTrue(LogParserFactory.getParser("json") instanceof JsonLogParser);
        assertTrue(LogParserFactory.getParser("xml") instanceof XmlLogParser);
        assertTrue(LogParserFactory.getParser("unknown") instanceof TextLogParser);
    }

    @Test
    public void testNestedJson() {
        LogParser parser = new JsonLogParser();
        String input = "{\"user\":{\"name\":\"王五\",\"pwd\":\"123456\"},\"contact\":{\"mobile\":\"13655556666\"}}";
        String result = parser.parseAndMask(input, engine);
        assertFalse(result.contains("123456"));
        assertFalse(result.contains("13655556666"));
        assertTrue(result.contains("王五"));
    }

    @Test
    public void testJsonArray() {
        LogParser parser = new JsonLogParser();
        String input = "{\"users\":[{\"name\":\"赵六\",\"phone\":\"13577778888\"},{\"name\":\"钱七\",\"password\":\"pass123\"}]}";
        String result = parser.parseAndMask(input, engine);
        assertFalse(result.contains("13577778888"));
        assertFalse(result.contains("pass123"));
        assertTrue(result.contains("赵六"));
        assertTrue(result.contains("钱七"));
    }

    @Test
    public void testDeeplyNestedJson() {
        LogParser parser = new JsonLogParser();
        String input = "{\n" +
                "  \"level1\": {\n" +
                "    \"level2\": {\n" +
                "      \"level3\": {\n" +
                "        \"user\": {\n" +
                "          \"password\": \"deepsecret\",\n" +
                "          \"info\": {\n" +
                "            \"phone\": \"13899990000\",\n" +
                "            \"idCard\": \"110101199001018888\"\n" +
                "          }\n" +
                "        }\n" +
                "      }\n" +
                "    }\n" +
                "  }\n" +
                "}";
        String result = parser.parseAndMask(input, engine);
        assertFalse(result.contains("deepsecret"));
        assertFalse(result.contains("13899990000"));
        assertFalse(result.contains("110101199001018888"));
    }

    @Test
    public void testJsonArrayWithNestedObjects() {
        LogParser parser = new JsonLogParser();
        String input = "{\n" +
                "  \"transactions\": [\n" +
                "    {\n" +
                "      \"id\": 1,\n" +
                "      \"customer\": {\n" +
                "        \"name\": \"张三\",\n" +
                "        \"phone\": \"13811112222\",\n" +
                "        \"bankCard\": \"6222021234567890123\"\n" +
                "      }\n" +
                "    },\n" +
                "    {\n" +
                "      \"id\": 2,\n" +
                "      \"customer\": {\n" +
                "        \"name\": \"李四\",\n" +
                "        \"phone\": \"13933334444\",\n" +
                "        \"password\": \"securepass\"\n" +
                "      }\n" +
                "    }\n" +
                "  ]\n" +
                "}";
        String result = parser.parseAndMask(input, engine);
        assertFalse(result.contains("13811112222"));
        assertFalse(result.contains("6222021234567890123"));
        assertFalse(result.contains("13933334444"));
        assertFalse(result.contains("securepass"));
        assertTrue(result.contains("张三"));
        assertTrue(result.contains("李四"));
    }

    @Test
    public void testJsonSensitiveFieldNameDetection() {
        LogParser parser = new JsonLogParser();
        String input = "{\"userPassword\":\"mypass\",\"userPhone\":\"13812345678\",\"userIdCard\":\"110101199001011234\"}";
        String result = parser.parseAndMask(input, engine);
        assertFalse(result.contains("mypass"));
        assertFalse(result.contains("13812345678"));
        assertFalse(result.contains("110101199001011234"));
    }

    @Test
    public void testJsonWithNullValues() {
        LogParser parser = new JsonLogParser();
        String input = "{\"user\":null,\"password\":\"123456\",\"phone\":null}";
        String result = parser.parseAndMask(input, engine);
        assertTrue(result.contains("\"user\":null"));
        assertFalse(result.contains("123456"));
    }

    @Test
    public void testXmlWithAttributes() {
        LogParser parser = new XmlLogParser();
        String input = "<user id=\"1\" phone=\"13812345678\" password=\"secret123\">张三</user>";
        String result = parser.parseAndMask(input, engine);
        assertFalse(result.contains("13812345678"));
        assertFalse(result.contains("secret123"));
        assertTrue(result.contains("张三"));
    }
}
