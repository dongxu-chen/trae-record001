package com.checkin.util;

import javax.script.*;
import java.util.*;
import java.util.concurrent.*;
import java.security.Permission;
import java.security.Policy;
import java.security.ProtectionDomain;

public class SafeSandbox {

    private static final Set<String> ALLOWED_CLASSES = new HashSet<>(Arrays.asList(
        "java.lang.Math",
        "java.lang.Integer",
        "java.lang.Long",
        "java.lang.Double",
        "java.lang.Float",
        "java.lang.String",
        "java.lang.Boolean",
        "java.util.ArrayList",
        "java.util.HashMap",
        "java.util.List",
        "java.util.Map"
    ));

    private static final Set<String> FORBIDDEN_KEYWORDS = new HashSet<>(Arrays.asList(
        "java.lang.Runtime",
        "java.lang.ProcessBuilder",
        "java.lang.System",
        "java.io",
        "java.nio",
        "java.net",
        "java.sql",
        "javax.script",
        "reflect",
        "ClassLoader",
        "getClass",
        ".class",
        "forName",
        "newInstance",
        "exec",
        "exit",
        "shutdown",
        "halt",
        "load",
        "loadLibrary",
        "getProperty",
        "getenv",
        "setSecurityManager",
        "setAccessible",
        "File",
        "Socket",
        "ServerSocket",
        "URL",
        "URI",
        "Process",
        "Thread",
        "Executor",
        "Future"
    ));

    private static final long EXECUTION_TIMEOUT = 5000;

    public static Object executeExpression(String expression, Map<String, Object> variables) {
        validateExpression(expression);
        
        ExecutorService executor = Executors.newSingleThreadExecutor();
        Future<Object> future = executor.submit(() -> {
            ScriptEngineManager manager = new ScriptEngineManager();
            ScriptEngine engine = manager.getEngineByName("nashorn");
            
            if (variables != null) {
                for (Map.Entry<String, Object> entry : variables.entrySet()) {
                    engine.put(entry.getKey(), entry.getValue());
                }
            }
            
            String safeScript = buildSafeScript(expression);
            return engine.eval(safeScript);
        });

        try {
            return future.get(EXECUTION_TIMEOUT, TimeUnit.MILLISECONDS);
        } catch (TimeoutException e) {
            future.cancel(true);
            throw new RuntimeException("表达式执行超时");
        } catch (ExecutionException e) {
            throw new RuntimeException("表达式执行错误: " + e.getCause().getMessage());
        } catch (Exception e) {
            throw new RuntimeException("表达式执行失败: " + e.getMessage());
        } finally {
            executor.shutdownNow();
        }
    }

    public static void validateExpression(String expression) {
        if (expression == null || expression.trim().isEmpty()) {
            throw new IllegalArgumentException("表达式不能为空");
        }

        for (String forbidden : FORBIDDEN_KEYWORDS) {
            if (expression.toLowerCase().contains(forbidden.toLowerCase())) {
                throw new SecurityException(
                    "表达式包含不安全内容，禁止使用: " + forbidden);
            }
        }

        if (expression.length() > 1000) {
            throw new IllegalArgumentException("表达式长度不能超过1000字符");
        }

        int openBraces = countOccurrences(expression, '{');
        int closeBraces = countOccurrences(expression, '}');
        if (openBraces != closeBraces) {
            throw new IllegalArgumentException("表达式括号不匹配");
        }

        int openParens = countOccurrences(expression, '(');
        int closeParens = countOccurrences(expression, ')');
        if (openParens != closeParens) {
            throw new IllegalArgumentException("表达式括号不匹配");
        }
    }

    private static String buildSafeScript(String expression) {
        StringBuilder sb = new StringBuilder();
        sb.append("(function() {\n");
        sb.append("    var Java = null;\n");
        sb.append("    var Packages = null;\n");
        sb.append("    var java = null;\n");
        sb.append("    var javax = null;\n");
        sb.append("    var com = null;\n");
        sb.append("    var org = null;\n");
        sb.append("    var io = null;\n");
        sb.append("    var net = null;\n");
        sb.append("    var File = null;\n");
        sb.append("    var URL = null;\n");
        sb.append("    var Socket = null;\n");
        sb.append("    var Process = null;\n");
        sb.append("    var Runtime = null;\n");
        sb.append("    var System = null;\n");
        sb.append("    var Thread = null;\n");
        sb.append("    return ").append(expression).append(";\n");
        sb.append("})()\n");
        return sb.toString();
    }

    private static int countOccurrences(String str, char c) {
        int count = 0;
        for (int i = 0; i < str.length(); i++) {
            if (str.charAt(i) == c) {
                count++;
            }
        }
        return count;
    }

    public static Integer calculateReward(String expression, int continuousDays, int totalDays, int points) {
        Map<String, Object> vars = new HashMap<>();
        vars.put("continuousDays", continuousDays);
        vars.put("totalDays", totalDays);
        vars.put("points", points);
        
        Object result = executeExpression(expression, vars);
        if (result instanceof Number) {
            return ((Number) result).intValue();
        }
        throw new RuntimeException("表达式计算结果必须是数字类型");
    }

    public static boolean validateCondition(String expression, Map<String, Object> vars) {
        Object result = executeExpression(expression, vars);
        if (result instanceof Boolean) {
            return (Boolean) result;
        }
        throw new RuntimeException("条件表达式必须返回布尔值");
    }
}
