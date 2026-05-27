package com.datasecurity.masking.config;

import com.datasecurity.masking.access.UserContext;
import com.datasecurity.masking.access.UserContextHolder;
import com.datasecurity.masking.enums.DatabaseType;
import com.datasecurity.masking.enums.SensitiveType;
import com.datasecurity.masking.model.DatabaseConfig;
import com.datasecurity.masking.model.SensitiveField;
import com.datasecurity.masking.service.MetadataService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

@Slf4j
@Component
public class StartupInitializer implements CommandLineRunner {

    @Autowired(required = false)
    private MetadataService metadataService;

    @Override
    public void run(String... args) {
        log.info("========================================");
        log.info("  敏感数据脱敏服务启动中...");
        log.info("========================================");
        log.info("");
        log.info("支持的数据库类型: MySQL, PostgreSQL, MongoDB");
        log.info("支持的敏感类型: 身份证号, 手机号, 银行卡号, 姓名, 邮箱, 地址");
        log.info("支持的脱敏策略: 掩码, 替换, 哈希, 截断");
        log.info("");
        log.info("REST API 端点:");
        log.info("  POST /api/metadata/scan - 扫描数据库元数据");
        log.info("  GET  /api/metadata/{databaseId} - 获取敏感字段列表");
        log.info("  POST /api/metadata/refresh - 刷新元数据");
        log.info("  POST /api/masking/mask/result - 批量脱敏");
        log.info("  POST /api/masking/mask/row - 单条数据脱敏");
        log.info("  GET  /api/demo/users - 演示: 获取用户列表");
        log.info("");
        log.info("默认脱敏规则:");
        log.info("  身份证号: 显示前6后4位，中间用*代替");
        log.info("  手机号: 显示前3后4位，中间用*代替");
        log.info("  银行卡号: 显示前4后4位，中间用*代替");
        log.info("  姓名: 显示第一个字，其余用*代替");
        log.info("  邮箱: 显示前2位，其余用*代替");
        log.info("  地址: 显示前6位，后面用...代替");
        log.info("");

        initDemoMetadata();

        log.info("========================================");
        log.info("  敏感数据脱敏服务启动完成!");
        log.info("========================================");
    }

    private void initDemoMetadata() {
        if (metadataService == null) {
            return;
        }

        try {
            List<SensitiveField> demoFields = new ArrayList<>();

            demoFields.add(SensitiveField.builder()
                    .tableName("user")
                    .columnName("name")
                    .sensitiveType(SensitiveType.NAME)
                    .comment("用户姓名")
                    .build());

            demoFields.add(SensitiveField.builder()
                    .tableName("user")
                    .columnName("id_card")
                    .sensitiveType(SensitiveType.ID_CARD)
                    .comment("身份证号")
                    .build());

            demoFields.add(SensitiveField.builder()
                    .tableName("user")
                    .columnName("phone")
                    .sensitiveType(SensitiveType.PHONE)
                    .comment("手机号码")
                    .build());

            demoFields.add(SensitiveField.builder()
                    .tableName("user")
                    .columnName("bank_card")
                    .sensitiveType(SensitiveType.BANK_CARD)
                    .comment("银行卡号")
                    .build());

            demoFields.add(SensitiveField.builder()
                    .tableName("user")
                    .columnName("email")
                    .sensitiveType(SensitiveType.EMAIL)
                    .comment("邮箱地址")
                    .build());

            demoFields.add(SensitiveField.builder()
                    .tableName("user")
                    .columnName("address")
                    .sensitiveType(SensitiveType.ADDRESS)
                    .comment("居住地址")
                    .build());

            java.lang.reflect.Field localCacheField = metadataService.getClass().getDeclaredField("localCache");
            localCacheField.setAccessible(true);
            @SuppressWarnings("unchecked")
            java.util.Map<String, List<SensitiveField>> localCache =
                    (java.util.Map<String, List<SensitiveField>>) localCacheField.get(metadataService);
            localCache.put("default", demoFields);

            UserContextHolder.set(UserContext.builder()
                    .userId("system")
                    .username("system")
                    .roles(Set.of("ADMIN"))
                    .needMasking(false)
                    .build());

            log.info("演示元数据已初始化，共 {} 个敏感字段", demoFields.size());
            log.info("默认角色: VIEWER (需要脱敏)，可通过 API 切换角色");
            log.info("  POST /api/demo/user/role/admin - 切换到管理员(可查看原始数据)");
            log.info("  POST /api/demo/user/role/viewer - 切换到查看者(数据脱敏)");
            log.info("  POST /api/demo/user/role/operator - 切换到操作员(部分脱敏)");

        } catch (Exception e) {
            log.warn("初始化演示元数据失败: {}", e.getMessage());
        } finally {
            UserContextHolder.clear();
        }
    }
}
