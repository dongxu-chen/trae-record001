package com.checkin.controller;

import com.checkin.common.Result;
import com.checkin.util.SafeSandbox;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/sandbox")
public class SandboxController {

    @PostMapping("/validate")
    public Result<Map<String, Object>> validateExpression(@RequestBody Map<String, String> params) {
        try {
            String expression = params.get("expression");
            SafeSandbox.validateExpression(expression);
            
            Map<String, Object> result = new HashMap<>();
            result.put("valid", true);
            result.put("message", "表达式验证通过");
            return Result.success(result);
        } catch (Exception e) {
            Map<String, Object> result = new HashMap<>();
            result.put("valid", false);
            result.put("message", e.getMessage());
            return Result.success(result);
        }
    }

    @PostMapping("/execute")
    public Result<Map<String, Object>> executeExpression(@RequestBody Map<String, Object> params) {
        try {
            String expression = (String) params.get("expression");
            @SuppressWarnings("unchecked")
            Map<String, Object> variables = (Map<String, Object>) params.get("variables");
            
            Object result = SafeSandbox.executeExpression(expression, variables);
            
            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("result", result);
            response.put("type", result != null ? result.getClass().getSimpleName() : "null");
            return Result.success(response);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/calculate-reward")
    public Result<Map<String, Object>> calculateReward(@RequestBody Map<String, Object> params) {
        try {
            String expression = (String) params.get("expression");
            int continuousDays = params.get("continuousDays") != null ? 
                    ((Number) params.get("continuousDays")).intValue() : 0;
            int totalDays = params.get("totalDays") != null ? 
                    ((Number) params.get("totalDays")).intValue() : 0;
            int points = params.get("points") != null ? 
                    ((Number) params.get("points")).intValue() : 0;
            
            Integer result = SafeSandbox.calculateReward(expression, continuousDays, totalDays, points);
            
            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("reward", result);
            return Result.success(response);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/forbidden-keywords")
    public Result<Map<String, Object>> getForbiddenKeywords() {
        Map<String, Object> result = new HashMap<>();
        result.put("description", "以下关键字和操作在表达式中被禁止使用");
        result.put("forbidden", new String[]{
            "Runtime", "ProcessBuilder", "System", "File", "Socket", "URL",
            "Thread", "Executor", "ClassLoader", "Reflection", "JNI",
            "java.io", "java.net", "java.sql", "javax.script",
            "exec", "exit", "shutdown", "load", "loadLibrary",
            "getProperty", "getenv", "setSecurityManager", "setAccessible"
        });
        result.put("allowed-variables", new String[]{
            "continuousDays (int)",
            "totalDays (int)",
            "points (int)",
            "recheckCount (int)"
        });
        result.put("examples", new String[]{
            "基础奖励: 10 + continuousDays * 5",
            "阶梯奖励: continuousDays <= 7 ? 10 : continuousDays <= 14 ? 20 : 30",
            "累计奖励: Math.floor(totalDays / 7) * 50",
            "复合条件: continuousDays > 3 ? Math.min(continuousDays * 10, 100) : 10"
        });
        return Result.success(result);
    }
}
