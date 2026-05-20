package com.risk.engine.controller;

import com.risk.engine.entity.RiskList;
import com.risk.engine.service.RiskListService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/lists")
@Api(tags = "名单管理")
public class RiskListController {

    @Autowired
    private RiskListService riskListService;

    @PostMapping
    @ApiOperation("创建名单")
    public ResponseEntity<RiskList> createList(@RequestBody RiskList riskList) {
        return ResponseEntity.ok(riskListService.createList(riskList));
    }

    @GetMapping("/{id}")
    @ApiOperation("根据ID查询名单")
    public ResponseEntity<RiskList> getListById(@PathVariable Long id) {
        return riskListService.getListById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping
    @ApiOperation("查询所有名单")
    public ResponseEntity<List<RiskList>> getAllLists() {
        return ResponseEntity.ok(riskListService.getAllLists());
    }

    @GetMapping("/active")
    @ApiOperation("查询所有生效名单")
    public ResponseEntity<List<RiskList>> getActiveLists() {
        return ResponseEntity.ok(riskListService.getActiveLists());
    }

    @GetMapping("/active/type/{listType}")
    @ApiOperation("根据类型查询生效名单")
    public ResponseEntity<List<RiskList>> getActiveListsByType(@PathVariable String listType) {
        return ResponseEntity.ok(riskListService.getActiveListsByType(listType));
    }

    @PutMapping("/{id}")
    @ApiOperation("更新名单")
    public ResponseEntity<RiskList> updateList(@PathVariable Long id, @RequestBody RiskList riskList) {
        return ResponseEntity.ok(riskListService.updateList(id, riskList));
    }

    @DeleteMapping("/{id}")
    @ApiOperation("删除名单")
    public ResponseEntity<Void> deleteList(@PathVariable Long id) {
        riskListService.deleteList(id);
        return ResponseEntity.ok().build();
    }

    @PostMapping("/match")
    @ApiOperation("名单匹配")
    public ResponseEntity<List<String>> matchLists(@RequestBody Map<String, Object> data,
                                                   @RequestParam String listType) {
        return ResponseEntity.ok(riskListService.matchLists(data, listType));
    }

    @PostMapping("/blacklist/check")
    @ApiOperation("检查是否在黑名单")
    public ResponseEntity<Boolean> isInBlacklist(@RequestBody Map<String, Object> data) {
        return ResponseEntity.ok(riskListService.isInBlacklist(data));
    }

    @PostMapping("/whitelist/check")
    @ApiOperation("检查是否在白名单")
    public ResponseEntity<Boolean> isInWhitelist(@RequestBody Map<String, Object> data) {
        return ResponseEntity.ok(riskListService.isInWhitelist(data));
    }

    @PostMapping("/reload")
    @ApiOperation("重新加载名单缓存")
    public ResponseEntity<String> reloadCache() {
        riskListService.reloadCache();
        return ResponseEntity.ok("缓存重新加载成功");
    }
}
