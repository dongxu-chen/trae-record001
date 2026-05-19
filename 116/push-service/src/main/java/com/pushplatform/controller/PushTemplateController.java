package com.pushplatform.controller;

import com.pushplatform.common.core.Result;
import com.pushplatform.dto.PushTemplateDTO;
import com.pushplatform.entity.PushTemplate;
import com.pushplatform.service.PushTemplateService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/template")
public class PushTemplateController {

    @Autowired
    private PushTemplateService pushTemplateService;

    @GetMapping("/list")
    public Result<List<PushTemplate>> list(@RequestParam(required = false) String channel,
                                           @RequestParam(required = false) Integer status) {
        return Result.success(pushTemplateService.list(channel, status));
    }

    @GetMapping("/{id}")
    public Result<PushTemplate> getById(@PathVariable Long id) {
        return Result.success(pushTemplateService.getById(id));
    }

    @GetMapping("/code/{templateCode}")
    public Result<PushTemplate> getByCode(@PathVariable String templateCode) {
        return Result.success(pushTemplateService.getByCode(templateCode));
    }

    @PostMapping("/create")
    public Result<Boolean> create(@Validated @RequestBody PushTemplateDTO dto) {
        return Result.success(pushTemplateService.create(dto));
    }

    @PostMapping("/update")
    public Result<Boolean> update(@Validated @RequestBody PushTemplateDTO dto) {
        return Result.success(pushTemplateService.update(dto));
    }

    @PostMapping("/delete/{id}")
    public Result<Boolean> delete(@PathVariable Long id) {
        return Result.success(pushTemplateService.delete(id));
    }
}
