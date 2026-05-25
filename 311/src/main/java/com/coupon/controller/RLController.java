package com.coupon.controller;

import com.coupon.common.ApiResponse;
import com.coupon.model.UserProfile;
import com.coupon.redis.service.CouponStockService;
import com.coupon.redis.service.UserProfileCacheService;
import com.coupon.rl.agent.DQNAgent;
import com.coupon.rl.model.CouponAction;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/v1/rl")
public class RLController {

    private final DQNAgent dqnAgent;
    private final UserProfileCacheService userProfileCacheService;
    private final CouponStockService couponStockService;

    public RLController(DQNAgent dqnAgent,
                        UserProfileCacheService userProfileCacheService,
                        CouponStockService couponStockService) {
        this.dqnAgent = dqnAgent;
        this.userProfileCacheService = userProfileCacheService;
        this.couponStockService = couponStockService;
    }

    @GetMapping("/status")
    public ApiResponse<Map<String, Object>> getRLStatus() {
        return ApiResponse.success(Map.of(
                "trainStepCount", dqnAgent.getTrainStepCount(),
                "replayBufferSize", dqnAgent.getReplayBufferSize(),
                "epsilon", dqnAgent.getEpsilon(),
                "dailyBudgetUsed", couponStockService.getDailyBudgetUsed(),
                "remainingBudget", couponStockService.getRemainingBudget()
        ));
    }

    @PostMapping("/train")
    public ApiResponse<Map<String, Object>> triggerTrain() {
        log.info("Trigger RL training manually");
        boolean success = dqnAgent.train();
        return ApiResponse.success(Map.of(
                "success", success,
                "trainStepCount", dqnAgent.getTrainStepCount(),
                "replayBufferSize", dqnAgent.getReplayBufferSize()
        ));
    }

    @PostMapping("/model/save")
    public ApiResponse<Map<String, Object>> saveModel() {
        log.info("Save RL model manually");
        dqnAgent.saveModel();
        return ApiResponse.success(Map.of(
                "success", true,
                "trainStepCount", dqnAgent.getTrainStepCount()
        ));
    }

    @PostMapping("/model/load")
    public ApiResponse<Map<String, Object>> loadModel() {
        log.info("Load RL model manually");
        dqnAgent.loadModel();
        return ApiResponse.success(Map.of(
                "success", true
        ));
    }

    @PostMapping("/predict")
    public ApiResponse<CouponAction> predictAction(@RequestBody UserProfile profile) {
        log.info("Predict coupon action for user: {}", profile.getUserId());
        CouponAction action = dqnAgent.selectGreedyAction(profile);
        return ApiResponse.success(action);
    }

    @GetMapping("/predict/{userId}")
    public ApiResponse<CouponAction> predictActionForUser(@PathVariable String userId) {
        log.info("Predict coupon action for user: {}", userId);
        UserProfile profile = userProfileCacheService.getOrCreateDefault(userId);
        CouponAction action = dqnAgent.selectGreedyAction(profile);
        return ApiResponse.success(action);
    }

    @GetMapping("/actions")
    public ApiResponse<Map<String, Object>> getAllActions() {
        int totalActions = CouponAction.getTotalActions();
        CouponAction[] actions = new CouponAction[totalActions];
        for (int i = 0; i < totalActions; i++) {
            actions[i] = CouponAction.fromIndex(i);
        }
        return ApiResponse.success(Map.of(
                "total", totalActions,
                "actions", actions
        ));
    }

    @GetMapping("/action/{actionIndex}")
    public ApiResponse<CouponAction> getAction(@PathVariable int actionIndex) {
        if (actionIndex < 0 || actionIndex >= CouponAction.getTotalActions()) {
            return ApiResponse.badRequest("无效的动作索引");
        }
        return ApiResponse.success(CouponAction.fromIndex(actionIndex));
    }

    @GetMapping("/state/{userId}")
    public ApiResponse<Map<String, Object>> getUserState(@PathVariable String userId) {
        UserProfile profile = userProfileCacheService.getOrCreateDefault(userId);
        double[] stateVector = profile.toStateVector();

        String[] featureNames = {
                "消费频次", "客单价", "活跃度", "30天订单数",
                "距上次订单天数", "券使用率", "折扣敏感度", "是否新用户"
        };

        Map<String, Object> features = new java.util.LinkedHashMap<>();
        for (int i = 0; i < featureNames.length; i++) {
            features.put(featureNames[i], stateVector[i]);
        }

        return ApiResponse.success(Map.of(
                "userId", userId,
                "rawProfile", profile,
                "normalizedState", features
        ));
    }
}
