package com.pushplatform.controller;

import com.pushplatform.common.core.Result;
import com.pushplatform.dto.TagCondition;
import com.pushplatform.entity.AbTest;
import com.pushplatform.entity.TagGroup;
import com.pushplatform.entity.UserTag;
import com.pushplatform.service.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/advanced")
public class PushAdvancedController {

    @Autowired
    private UserTagService userTagService;

    @Autowired
    private TagGroupService tagGroupService;

    @Autowired
    private AbTestService abTestService;

    @Autowired
    private ScheduledPushService scheduledPushService;

    @Autowired
    private MessageAggregateService messageAggregateService;

    @PostMapping("/user/tag")
    public Result<Boolean> addUserTag(@RequestParam String userId,
                                       @RequestParam String tagCode,
                                       @RequestParam(required = false) String tagName,
                                       @RequestParam String tagValue) {
        userTagService.addUserTag(userId, tagCode, tagName != null ? tagName : tagCode, tagValue);
        return Result.success(true);
    }

    @PostMapping("/user/tags")
    public Result<Boolean> batchAddUserTags(@RequestParam String userId,
                                            @RequestBody Map<String, String> tags) {
        userTagService.batchAddUserTags(userId, tags);
        return Result.success(true);
    }

    @GetMapping("/user/tags/{userId}")
    public Result<List<UserTag>> getUserTags(@PathVariable String userId) {
        return Result.success(userTagService.getUserTags(userId));
    }

    @DeleteMapping("/user/tag")
    public Result<Boolean> removeUserTag(@RequestParam String userId,
                                         @RequestParam String tagCode) {
        userTagService.removeUserTag(userId, tagCode);
        return Result.success(true);
    }

    @GetMapping("/tag/users")
    public Result<List<String>> getUserIdsByTag(@RequestParam String tagCode) {
        return Result.success(userTagService.getUserIdsByTag(tagCode));
    }

    @GetMapping("/tag/stats")
    public Result<Map<String, Long>> getTagStats() {
        return Result.success(userTagService.getTagStats());
    }

    @PostMapping("/group")
    public Result<TagGroup> createGroup(@RequestParam String groupCode,
                                        @RequestParam String groupName,
                                        @RequestBody List<TagCondition> conditions,
                                        @RequestParam(required = false) String remark) {
        return Result.success(tagGroupService.createGroup(groupCode, groupName, conditions, remark));
    }

    @GetMapping("/group/list")
    public Result<List<TagGroup>> listGroups() {
        return Result.success(tagGroupService.listActiveGroups());
    }

    @GetMapping("/group/users/{groupId}")
    public Result<List<String>> getGroupUsers(@PathVariable Long groupId) {
        return Result.success(tagGroupService.getGroupUserIds(groupId));
    }

    @PostMapping("/group/status/{groupId}")
    public Result<Boolean> updateGroupStatus(@PathVariable Long groupId,
                                              @RequestParam Integer status) {
        return Result.success(tagGroupService.updateGroupStatus(groupId, status));
    }

    @PostMapping("/abtest")
    public Result<AbTest> createAbTest(@RequestParam String testCode,
                                       @RequestParam String testName,
                                       @RequestParam String channel,
                                       @RequestParam Long templateAId,
                                       @RequestParam Long templateBId,
                                       @RequestParam(defaultValue = "50") Integer splitRatio,
                                       @RequestParam(required = false) String remark) {
        return Result.success(abTestService.createTest(testCode, testName, channel,
                templateAId, templateBId, splitRatio, remark));
    }

    @PostMapping("/abtest/start/{testId}")
    public Result<Boolean> startAbTest(@PathVariable Long testId) {
        return Result.success(abTestService.startTest(testId));
    }

    @PostMapping("/abtest/end/{testId}")
    public Result<Boolean> endAbTest(@PathVariable Long testId) {
        return Result.success(abTestService.endTest(testId));
    }

    @GetMapping("/abtest/list")
    public Result<List<AbTest>> listAbTests() {
        return Result.success(abTestService.listActiveTests());
    }

    @GetMapping("/abtest/winner/{testId}")
    public Result<String> getWinningGroup(@PathVariable Long testId) {
        return Result.success(abTestService.getWinningGroup(testId));
    }

    @PostMapping("/abtest/click/{recordId}")
    public Result<Boolean> recordClick(@PathVariable Long recordId) {
        abTestService.recordClick(recordId);
        return Result.success(true);
    }

    @PostMapping("/message/aggregate")
    public Result<Boolean> addAggregateMessage(@RequestParam String userId,
                                                @RequestParam String channel,
                                                @RequestParam(required = false) String title,
                                                @RequestParam String content,
                                                @RequestParam(required = false) Map<String, Object> extParams) {
        messageAggregateService.addMessage(userId, channel, title, content, extParams);
        return Result.success(true);
    }

    @GetMapping("/scheduled/list")
    public Result<List<com.pushplatform.entity.PushTask>> listScheduledTasks() {
        return Result.success(scheduledPushService.getPendingScheduledTasks());
    }

    @PostMapping("/scheduled/cancel/{taskId}")
    public Result<Boolean> cancelScheduledTask(@PathVariable Long taskId) {
        return Result.success(scheduledPushService.cancelScheduledTask(taskId));
    }
}
