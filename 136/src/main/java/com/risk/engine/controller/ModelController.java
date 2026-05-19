package com.risk.engine.controller;

import com.risk.engine.entity.MlModel;
import com.risk.engine.service.PmmlModelService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;
import java.util.Set;

@RestController
@RequestMapping("/api/models")
@Api(tags = "模型管理")
public class ModelController {

    @Autowired
    private PmmlModelService pmmlModelService;

    @PostMapping
    @ApiOperation("上传并保存PMML模型")
    public ResponseEntity<MlModel> saveModel(@RequestPart("model") MlModel model,
                                             @RequestPart(value = "file", required = false) MultipartFile file) throws Exception {
        return ResponseEntity.ok(pmmlModelService.saveModel(model, file));
    }

    @GetMapping("/{id}")
    @ApiOperation("根据ID查询模型")
    public ResponseEntity<MlModel> getModelById(@PathVariable Long id) {
        return pmmlModelService.getModelById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping
    @ApiOperation("查询所有模型")
    public ResponseEntity<List<MlModel>> getAllModels() {
        return ResponseEntity.ok(pmmlModelService.getAllModels());
    }

    @DeleteMapping("/{id}")
    @ApiOperation("删除模型")
    public ResponseEntity<Void> deleteModel(@PathVariable Long id) {
        pmmlModelService.deleteModel(id);
        return ResponseEntity.ok().build();
    }

    @PatchMapping("/{id}/status")
    @ApiOperation("更新模型状态")
    public ResponseEntity<MlModel> updateModelStatus(@PathVariable Long id, @RequestParam String status) {
        return ResponseEntity.ok(pmmlModelService.updateModelStatus(id, status));
    }

    @GetMapping("/loaded")
    @ApiOperation("获取已加载的模型编码列表")
    public ResponseEntity<Set<String>> getLoadedModels() {
        return ResponseEntity.ok(pmmlModelService.getLoadedModelCodes());
    }

    @GetMapping("/features/{modelCode}")
    @ApiOperation("获取模型输入特征列表")
    public ResponseEntity<List<String>> getModelFeatures(@PathVariable String modelCode) {
        return ResponseEntity.ok(pmmlModelService.getModelFeatures(modelCode));
    }

    @PostMapping("/evaluate/{modelCode}")
    @ApiOperation("评估单模型")
    public ResponseEntity<Map<String, Object>> evaluateModel(@PathVariable String modelCode,
                                                              @RequestBody Map<String, Object> features) {
        return ResponseEntity.ok(pmmlModelService.evaluate(modelCode, features));
    }

    @PostMapping("/evaluate/scene/{scene}")
    @ApiOperation("按场景评估所有模型")
    public ResponseEntity<Map<String, Object>> evaluateByScene(@PathVariable String scene,
                                                                @RequestBody Map<String, Object> features) {
        return ResponseEntity.ok(pmmlModelService.evaluateByScene(scene, features));
    }
}
