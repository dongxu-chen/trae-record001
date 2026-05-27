package com.datasecurity.masking;

import com.datasecurity.masking.enums.MaskStrategy;
import com.datasecurity.masking.enums.SensitiveType;
import com.datasecurity.masking.model.MaskPolicy;
import com.datasecurity.masking.recognizer.SensitiveFieldRecognizer;
import com.datasecurity.masking.strategy.MaskStrategyService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
class DataMaskingServiceTest {

    @Autowired
    private SensitiveFieldRecognizer recognizer;

    @Autowired
    private MaskStrategyService maskStrategyService;

    @BeforeEach
    void setUp() {
    }

    @Test
    void testRecognizeByIdCardColumnName() {
        SensitiveType type = recognizer.recognizeByColumnName("id_card", "身份证号");
        assertEquals(SensitiveType.ID_CARD, type);

        type = recognizer.recognizeByColumnName("idCard", null);
        assertEquals(SensitiveType.ID_CARD, type);

        type = recognizer.recognizeByColumnName("身份证号码", null);
        assertEquals(SensitiveType.ID_CARD, type);
    }

    @Test
    void testRecognizeByPhoneColumnName() {
        SensitiveType type = recognizer.recognizeByColumnName("phone", "手机号");
        assertEquals(SensitiveType.PHONE, type);

        type = recognizer.recognizeByColumnName("mobile", null);
        assertEquals(SensitiveType.PHONE, type);

        type = recognizer.recognizeByColumnName("手机号码", null);
        assertEquals(SensitiveType.PHONE, type);
    }

    @Test
    void testRecognizeByBankCardColumnName() {
        SensitiveType type = recognizer.recognizeByColumnName("bank_card", "银行卡号");
        assertEquals(SensitiveType.BANK_CARD, type);

        type = recognizer.recognizeByColumnName("银行卡", null);
        assertEquals(SensitiveType.BANK_CARD, type);
    }

    @Test
    void testRecognizeByNameColumnName() {
        SensitiveType type = recognizer.recognizeByColumnName("name", "姓名");
        assertEquals(SensitiveType.NAME, type);

        type = recognizer.recognizeByColumnName("username", null);
        assertEquals(SensitiveType.NAME, type);
    }

    @Test
    void testRecognizeByValue() {
        SensitiveType type = recognizer.recognizeByValue("110101199001011234");
        assertEquals(SensitiveType.ID_CARD, type);

        type = recognizer.recognizeByValue("13800138000");
        assertEquals(SensitiveType.PHONE, type);

        type = recognizer.recognizeByValue("6222021234567890123");
        assertEquals(SensitiveType.BANK_CARD, type);

        type = recognizer.recognizeByValue("test@example.com");
        assertEquals(SensitiveType.EMAIL, type);
    }

    @Test
    void testMaskIdCard() {
        String original = "110101199001011234";
        String masked = maskStrategyService.mask(original, SensitiveType.ID_CARD);
        assertEquals("110101********1234", masked);
        System.out.println("身份证脱敏: " + original + " -> " + masked);
    }

    @Test
    void testMaskPhone() {
        String original = "13800138000";
        String masked = maskStrategyService.mask(original, SensitiveType.PHONE);
        assertEquals("138****8000", masked);
        System.out.println("手机号脱敏: " + original + " -> " + masked);
    }

    @Test
    void testMaskBankCard() {
        String original = "6222021234567890123";
        String masked = maskStrategyService.mask(original, SensitiveType.BANK_CARD);
        assertEquals("6222***********0123", masked);
        System.out.println("银行卡脱敏: " + original + " -> " + masked);
    }

    @Test
    void testMaskName() {
        String original = "张三";
        String masked = maskStrategyService.mask(original, SensitiveType.NAME);
        assertEquals("张*", masked);
        System.out.println("姓名脱敏: " + original + " -> " + masked);

        original = "诸葛亮";
        masked = maskStrategyService.mask(original, SensitiveType.NAME);
        assertEquals("诸**", masked);
        System.out.println("姓名脱敏: " + original + " -> " + masked);
    }

    @Test
    void testMaskEmail() {
        String original = "zhangsan@example.com";
        String masked = maskStrategyService.mask(original, SensitiveType.EMAIL);
        assertEquals("zh*******@example.com", masked);
        System.out.println("邮箱脱敏: " + original + " -> " + masked);
    }

    @Test
    void testMaskAddress() {
        String original = "北京市朝阳区建国路88号";
        String masked = maskStrategyService.mask(original, SensitiveType.ADDRESS);
        assertEquals("北京市朝阳区***", masked);
        System.out.println("地址脱敏: " + original + " -> " + masked);
    }

    @Test
    void testCustomMaskPolicy() {
        String original = "13800138000";

        MaskPolicy replacePolicy = MaskPolicy.builder()
                .strategy(MaskStrategy.REPLACE)
                .replaceValue("[已隐藏]")
                .build();
        String replaced = maskStrategyService.mask(original, replacePolicy);
        assertEquals("[已隐藏]", replaced);
        System.out.println("替换策略: " + original + " -> " + replaced);

        MaskPolicy hashPolicy = MaskPolicy.builder()
                .strategy(MaskStrategy.HASH)
                .hashAlgorithm("MD5")
                .build();
        String hashed = maskStrategyService.mask(original, hashPolicy);
        assertNotNull(hashed);
        assertEquals(32, hashed.length());
        System.out.println("哈希策略: " + original + " -> " + hashed);

        MaskPolicy customMaskPolicy = MaskPolicy.builder()
                .strategy(MaskStrategy.MASK)
                .maskChar("#")
                .keepStart(5)
                .keepEnd(2)
                .build();
        String customMasked = maskStrategyService.mask(original, customMaskPolicy);
        assertEquals("13800##00", customMasked);
        System.out.println("自定义掩码: " + original + " -> " + customMasked);
    }

    @Test
    void testNullAndEmptyValue() {
        assertNull(maskStrategyService.mask(null, SensitiveType.PHONE));
        assertEquals("", maskStrategyService.mask("", SensitiveType.PHONE));
        assertEquals("   ", maskStrategyService.mask("   ", SensitiveType.PHONE));
    }

    @Test
    void testUnknownType() {
        String original = "some random text";
        String result = maskStrategyService.mask(original, SensitiveType.UNKNOWN);
        assertEquals(original, result);
    }
}
