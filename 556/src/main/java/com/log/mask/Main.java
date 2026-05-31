package com.log.mask;

import com.log.mask.audit.*;
import com.log.mask.core.MaskRule;
import com.log.mask.discovery.*;
import com.log.mask.dynamic.*;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.util.List;

public class Main {

    public static void main(String[] args) {
        System.out.println("=== 日志脱敏清洗工具 ===");
        System.out.println();

        LogDesensitizationService service = new LogDesensitizationService();

        if (args.length == 0) {
            runDemo(service);
            return;
        }

        String inputFile = null;
        String outputFile = null;
        String format = "text";
        String configFile = null;
        boolean benchmark = false;
        int benchmarkIterations = 1000;
        boolean useNFA = false;
        boolean scan = false;
        String auditFile = null;
        String role = "ANONYMOUS";

        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "-i":
                case "--input":
                    if (i + 1 < args.length) inputFile = args[++i];
                    break;
                case "-o":
                case "--output":
                    if (i + 1 < args.length) outputFile = args[++i];
                    break;
                case "-f":
                case "--format":
                    if (i + 1 < args.length) format = args[++i];
                    break;
                case "-c":
                case "--config":
                    if (i + 1 < args.length) configFile = args[++i];
                    break;
                case "-h":
                case "--help":
                    printHelp();
                    return;
                case "-d":
                case "--demo":
                    runDemo(service);
                    return;
                case "-l":
                case "--list-rules":
                    listRules(service);
                    return;
                case "-b":
                case "--benchmark":
                    benchmark = true;
                    if (i + 1 < args.length && !args[i + 1].startsWith("-")) {
                        benchmarkIterations = Integer.parseInt(args[++i]);
                    }
                    break;
                case "--nfa":
                    useNFA = true;
                    break;
                case "--dfa":
                    useNFA = false;
                    break;
                case "-s":
                case "--scan":
                    scan = true;
                    break;
                case "--audit":
                    if (i + 1 < args.length) auditFile = args[++i];
                    break;
                case "-r":
                case "--role":
                    if (i + 1 < args.length) role = args[++i].toUpperCase();
                    break;
                case "--audit-stats":
                    printAuditStats(service);
                    return;
            }
        }

        if (benchmark) {
            runBenchmark(service, benchmarkIterations);
            return;
        }

        if (useNFA) {
            service.getRuleEngine().getMaskEngine().setUseDFA(false);
            System.out.println("使用 NFA 正则引擎");
        } else {
            System.out.println("使用 DFA 正则引擎（高性能）");
        }

        if (auditFile != null) {
            service.setAuditStorage(new FileAuditStorage(auditFile));
            System.out.println("审计日志输出到: " + auditFile);
        }

        if (inputFile != null) {
            try {
                if (configFile != null) {
                    service = new LogDesensitizationService(configFile);
                    service.getRuleEngine().getMaskEngine().setUseDFA(!useNFA);
                    if (auditFile != null) service.setAuditStorage(new FileAuditStorage(auditFile));
                }

                AccessContext context = createAccessContext(role);

                if (scan) {
                    scanFile(service, inputFile, format);
                } else {
                    processFile(service, inputFile, outputFile, format, context);
                }
            } catch (IOException e) {
                System.err.println("Error: " + e.getMessage());
                System.exit(1);
            }
        } else {
            printHelp();
        }
    }

    private static AccessContext createAccessContext(String role) {
        switch (role) {
            case "ADMIN": return AccessContext.admin("cli-admin");
            case "OPERATOR": return AccessContext.operator("cli-operator");
            case "VIEWER": return AccessContext.viewer("cli-viewer");
            default: return AccessContext.anonymous();
        }
    }

    private static void printHelp() {
        System.out.println("用法: java -jar log-desensitization-tool.jar [选项]");
        System.out.println();
        System.out.println("选项:");
        System.out.println("  -i, --input <文件>     输入日志文件路径");
        System.out.println("  -o, --output <文件>    输出文件路径（可选）");
        System.out.println("  -f, --format <格式>    日志格式: text, json, xml（默认: text）");
        System.out.println("  -c, --config <文件>    配置文件路径");
        System.out.println("  -d, --demo             运行演示示例");
        System.out.println("  -l, --list-rules       列出所有脱敏规则（按优先级排序）");
        System.out.println("  -b, --benchmark [N]    运行性能基准测试");
        System.out.println("  -s, --scan             扫描敏感信息（不脱敏，仅发现）");
        System.out.println("  -r, --role <角色>      访问角色: ADMIN, OPERATOR, VIEWER, ANONYMOUS");
        System.out.println("      --audit <文件>     审计日志输出文件路径");
        System.out.println("      --audit-stats      查看审计统计");
        System.out.println("      --dfa              使用 DFA 正则引擎（默认）");
        System.out.println("      --nfa              使用 NFA 正则引擎");
        System.out.println("  -h, --help             显示帮助信息");
        System.out.println();
        System.out.println("角色脱敏策略:");
        System.out.println("  ADMIN    - 不脱敏，可查看原始数据");
        System.out.println("  OPERATOR - 部分脱敏，保留前后若干位");
        System.out.println("  VIEWER   - 部分脱敏（受限）");
        System.out.println("  ANONYMOUS- 完全脱敏（默认）");
        System.out.println();
    }

    private static void runDemo(LogDesensitizationService service) {
        System.out.println("=== 脱敏规则列表 ===");
        List<MaskRule> rules = service.getAllRules();
        for (MaskRule rule : rules) {
            System.out.printf("  - %s: 优先级=%d %s%n", rule.getName(), rule.getPriority(), rule.isEnabled() ? "启用" : "禁用");
        }
        System.out.println();

        System.out.println("=== 1. 基础脱敏 ===");
        String textLog = "用户登录: username=张三, password=123456, 手机号=13812345678, 身份证=110101199001011234";
        System.out.println("原始: " + textLog);
        System.out.println("脱敏: " + service.mask(textLog, "text"));
        System.out.println();

        System.out.println("=== 2. 敏感信息发现 ===");
        String scanTarget = "contact: 13987654321, id=310101198505056789, pwd=abc123, email=user@test.com, card=6222021234567890123";
        System.out.println("扫描内容: " + scanTarget);
        DiscoveryReport report = service.scan(scanTarget);
        System.out.println(report.toTextReport());
        System.out.println();

        System.out.println("=== 3. 动态脱敏 ===");
        String sensitiveLog = "用户: 张三, 手机号: 13812345678, 身份证: 110101199001011234, 邮箱: test@example.com";
        System.out.println("原始数据: " + sensitiveLog);

        AccessContext admin = AccessContext.admin("admin1");
        String adminResult = service.maskDynamic(sensitiveLog, admin);
        System.out.println("ADMIN  (不脱敏): " + adminResult);

        AccessContext operator = AccessContext.operator("op1");
        String opResult = service.maskDynamic(sensitiveLog, operator);
        System.out.println("OPERATOR(部分): " + opResult);

        AccessContext viewer = AccessContext.viewer("viewer1");
        String viewerResult = service.maskDynamic(sensitiveLog, viewer);
        System.out.println("VIEWER  (受限): " + viewerResult);

        AccessContext anon = AccessContext.anonymous();
        String anonResult = service.maskDynamic(sensitiveLog, anon);
        System.out.println("ANONYMOUS(完全): " + anonResult);
        System.out.println();

        System.out.println("=== 4. 脱敏审计 ===");
        System.out.println("审计记录数: " + service.getAuditLogger().getRecordCount());
        AuditStatistics stats = service.getAuditStatistics();
        System.out.println(stats.toTextReport());

        System.out.println("=== 演示完成 ===");
    }

    private static void listRules(LogDesensitizationService service) {
        System.out.println("=== 脱敏规则列表（按优先级降序排列） ===");
        List<MaskRule> rules = service.getAllRules();
        for (MaskRule rule : rules) {
            System.out.printf("名称: %s (优先级: %d)%n", rule.getName(), rule.getPriority());
            System.out.printf("  正则: %s%n", rule.getRegex());
            System.out.printf("  替换: %s%n", rule.getReplacement());
            System.out.printf("  状态: %s%n", rule.isEnabled() ? "启用" : "禁用");
            System.out.println();
        }
    }

    private static void runBenchmark(LogDesensitizationService service, int iterations) {
        System.out.println("=== 性能基准测试 ===");
        System.out.println("迭代次数: " + iterations);

        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < 100; i++) {
            sb.append("用户").append(i).append(": 手机号=").append(13800000000L + i)
              .append(", 身份证=").append(110101199001010000L + i)
              .append(", 密码=pass").append(i)
              .append(", 邮箱=user").append(i).append("@example.com\n");
        }
        String testData = sb.toString();
        System.out.println("测试数据长度: " + testData.length() + " 字符");
        System.out.println();
        System.out.println(service.getRuleEngine().getMaskEngine().getPerformanceReport(testData, iterations));
    }

    private static void scanFile(LogDesensitizationService service, String inputFile, String format) throws IOException {
        System.out.println("=== 敏感信息扫描 ===");
        System.out.println("扫描文件: " + inputFile);
        System.out.println("格式: " + format);

        BufferedReader reader = new BufferedReader(new FileReader(inputFile));
        try {
            StringBuilder content = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                content.append(line).append("\n");
            }
            DiscoveryReport report = service.scan(content.toString(), inputFile);
            System.out.println(report.toTextReport());
        } finally {
            reader.close();
        }
    }

    private static void processFile(LogDesensitizationService service, String inputFile, String outputFile, String format, AccessContext context) throws IOException {
        System.out.println("处理文件: " + inputFile);
        System.out.println("格式: " + format);
        System.out.println("访问角色: " + context.getRole());

        BufferedReader reader = new BufferedReader(new FileReader(inputFile));
        FileWriter writer = null;

        try {
            if (outputFile != null) {
                writer = new FileWriter(outputFile);
                System.out.println("输出到: " + outputFile);
            }

            String line;
            int count = 0;
            while ((line = reader.readLine()) != null) {
                String masked = service.maskDynamic(line, format, context);
                if (writer != null) {
                    writer.write(masked);
                    writer.write(System.lineSeparator());
                } else {
                    System.out.println(masked);
                }
                count++;
            }

            System.out.println();
            System.out.println("处理完成: " + count + " 行");
            System.out.println("审计记录: " + service.getAuditLogger().getRecordCount() + " 条");
        } finally {
            reader.close();
            if (writer != null) writer.close();
        }
    }

    private static void printAuditStats(LogDesensitizationService service) {
        AuditStatistics stats = service.getAuditStatistics();
        System.out.println(stats.toTextReport());

        System.out.println("最近 20 条审计记录:");
        List<AuditRecord> records = service.getAuditLogger().getRecords();
        int start = Math.max(0, records.size() - 20);
        for (int i = start; i < records.size(); i++) {
            System.out.println("  " + records.get(i));
        }
    }
}
