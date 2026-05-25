package com.apigateway.core.gray;

import com.apigateway.core.dto.ApiResponse;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Mono;

import java.util.List;

/**
 * 灰度路由REST API控制器
 * 提供灰度规则的增删改查和统计信息查询接口
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Slf4j
@RestController
@RequestMapping("/api/gray")
@RequiredArgsConstructor
public class GrayRouteController {

    private final GrayRouteService grayRouteService;

    /**
     * 获取所有灰度规则
     * GET /api/gray/rules
     *
     * @return 灰度规则列表
     */
    @GetMapping("/rules")
    public Mono<ResponseEntity<ApiResponse<List<GrayRule>>>> getRules() {
        return Mono.fromCallable(() -> {
            List<GrayRule> rules = grayRouteService.getAllRules();
            log.info("查询灰度规则列表，数量: {}", rules.size());
            return ResponseEntity.ok(ApiResponse.success("查询成功", rules));
        });
    }

    /**
     * 根据ID获取灰度规则
     * GET /api/gray/rules/{id}
     *
     * @param id 规则ID
     * @return 灰度规则
     */
    @GetMapping("/rules/{id}")
    public Mono<ResponseEntity<ApiResponse<GrayRule>>> getRuleById(@PathVariable String id) {
        return Mono.fromCallable(() -> {
            GrayRule rule = grayRouteService.getRule(id);
            if (rule == null) {
                return ResponseEntity.status(HttpStatus.NOT_FOUND)
                        .body(ApiResponse.error(404, "规则不存在: " + id));
            }
            log.info("查询灰度规则: id={}", id);
            return ResponseEntity.ok(ApiResponse.success("查询成功", rule));
        });
    }

    /**
     * 新增/修改灰度规则
     * POST /api/gray/rules
     * 支持热更新，无需重启服务
     *
     * @param rule 灰度规则
     * @return 保存后的规则
     */
    @PostMapping("/rules")
    public Mono<ResponseEntity<ApiResponse<GrayRule>>> saveRule(@Valid @RequestBody GrayRule rule) {
        return Mono.fromCallable(() -> {
            if (rule.getType() == null) {
                return ResponseEntity.badRequest()
                        .body(ApiResponse.error(400, "规则类型不能为空"));
            }
            if (rule.getCondition() == null) {
                return ResponseEntity.badRequest()
                        .body(ApiResponse.error(400, "规则条件不能为空"));
            }
            if (rule.getTargetVersion() == null) {
                return ResponseEntity.badRequest()
                        .body(ApiResponse.error(400, "目标版本不能为空"));
            }

            GrayRule savedRule = grayRouteService.saveRule(rule);
            log.info("保存灰度规则成功: id={}, name={}", savedRule.getId(), savedRule.getName());
            return ResponseEntity.ok(ApiResponse.success("保存成功", savedRule));
        });
    }

    /**
     * 删除灰度规则
     * DELETE /api/gray/rules/{id}
     *
     * @param id 规则ID
     * @return 操作结果
     */
    @DeleteMapping("/rules/{id}")
    public Mono<ResponseEntity<ApiResponse<Void>>> deleteRule(@PathVariable String id) {
        return Mono.fromCallable(() -> {
            boolean deleted = grayRouteService.deleteRule(id);
            if (!deleted) {
                return ResponseEntity.status(HttpStatus.NOT_FOUND)
                        .body(ApiResponse.error(404, "规则不存在: " + id));
            }
            log.info("删除灰度规则成功: id={}", id);
            return ResponseEntity.ok(ApiResponse.success("删除成功"));
        });
    }

    /**
     * 刷新灰度规则
     * POST /api/gray/rules/refresh
     * 重新从配置文件加载规则
     *
     * @return 操作结果
     */
    @PostMapping("/rules/refresh")
    public Mono<ResponseEntity<ApiResponse<Void>>> refreshRules() {
        return Mono.fromCallable(() -> {
            grayRouteService.refreshRules();
            log.info("刷新灰度规则成功");
            return ResponseEntity.ok(ApiResponse.success("刷新成功"));
        });
    }

    /**
     * 获取灰度统计信息
     * GET /api/gray/stats
     *
     * @return 灰度统计快照
     */
    @GetMapping("/stats")
    public Mono<ResponseEntity<ApiResponse<GrayStats.StatsSnapshot>>> getStats() {
        return Mono.fromCallable(() -> {
            GrayStats.StatsSnapshot stats = grayRouteService.getGrayStats();
            log.debug("查询灰度统计: v1Requests={}, v2Requests={}", 
                    stats.getV1Requests(), stats.getV2Requests());
            return ResponseEntity.ok(ApiResponse.success("查询成功", stats));
        });
    }

    /**
     * 重置灰度统计
     * POST /api/gray/stats/reset
     *
     * @return 操作结果
     */
    @PostMapping("/stats/reset")
    public Mono<ResponseEntity<ApiResponse<Void>>> resetStats() {
        return Mono.fromCallable(() -> {
            grayRouteService.resetStats();
            log.info("重置灰度统计成功");
            return ResponseEntity.ok(ApiResponse.success("重置成功"));
        });
    }

    /**
     * 检查请求是否符合灰度条件
     * GET /api/gray/check
     * 用于测试灰度规则匹配
     *
     * @param headerName  请求头名称（可选）
     * @param headerValue 请求头值（可选）
     * @param userId      用户ID（可选）
     * @param clientIp    客户端IP（可选）
     * @param path        请求路径（可选）
     * @return 检查结果
     */
    @GetMapping("/check")
    public Mono<ResponseEntity<ApiResponse<GrayRouteService.RouteVersion>>> checkGrayEligibility(
            @RequestHeader(value = "X-Gray-User", required = false) String grayUser,
            @RequestHeader(value = "X-User-Id", required = false) String userId,
            @RequestHeader(value = "X-Forwarded-For", required = false) String clientIp,
            @RequestParam(required = false) String path) {
        return Mono.fromCallable(() -> {
            // 这里只是模拟检查，实际使用时由过滤器自动处理
            // 返回当前的灰度配置状态
            GrayRouteService.RouteVersion version = GrayRouteService.RouteVersion.builder()
                    .version("v1")
                    .uri("http://localhost:8081")
                    .matched(false)
                    .build();
            return ResponseEntity.ok(ApiResponse.success("检查成功", version));
        });
    }
}
