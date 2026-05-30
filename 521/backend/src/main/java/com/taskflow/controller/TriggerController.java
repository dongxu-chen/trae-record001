package com.taskflow.controller;

import com.taskflow.dto.ApiResponse;
import com.taskflow.dto.TriggerDto;
import com.taskflow.service.TriggerService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/triggers")
@RequiredArgsConstructor
public class TriggerController {

    private final TriggerService triggerService;

    @PostMapping
    public ApiResponse<TriggerDto> create(@RequestBody TriggerDto.CreateRequest request) {
        return ApiResponse.success(triggerService.createTrigger(request));
    }

    @GetMapping("/{id}")
    public ApiResponse<TriggerDto> get(@PathVariable Long id) {
        return ApiResponse.success(triggerService.getTrigger(id));
    }

    @GetMapping
    public ApiResponse<List<TriggerDto>> list(@RequestParam(required = false) Long workflowId) {
        return ApiResponse.success(triggerService.listTriggers(workflowId));
    }

    @PutMapping("/{id}")
    public ApiResponse<TriggerDto> update(@PathVariable Long id,
                                           @RequestBody TriggerDto.CreateRequest request) {
        return ApiResponse.success(triggerService.updateTrigger(id, request));
    }

    @PostMapping("/{id}/toggle")
    public ApiResponse<TriggerDto> toggle(@PathVariable Long id,
                                           @RequestParam boolean enabled) {
        return ApiResponse.success(triggerService.toggleTrigger(id, enabled));
    }

    @DeleteMapping("/{id}")
    public ApiResponse<Void> delete(@PathVariable Long id) {
        triggerService.deleteTrigger(id);
        return ApiResponse.success(null);
    }

    @PostMapping("/event/{topic}")
    public ApiResponse<Void> fireEvent(@PathVariable String topic) {
        triggerService.fireEventTrigger(topic);
        return ApiResponse.success(null);
    }
}
