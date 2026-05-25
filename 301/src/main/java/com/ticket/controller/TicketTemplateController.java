package com.ticket.controller;

import com.ticket.common.PageResult;
import com.ticket.common.Result;
import com.ticket.dto.CreateTemplateDTO;
import com.ticket.entity.TicketTemplate;
import com.ticket.service.TicketTemplateService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/templates")
@RequiredArgsConstructor
public class TicketTemplateController {

    private final TicketTemplateService templateService;

    @PostMapping
    public Result<TicketTemplate> createTemplate(@Valid @RequestBody CreateTemplateDTO dto) {
        TicketTemplate template = templateService.createTemplate(dto);
        return Result.success(template);
    }

    @PutMapping("/{id}")
    public Result<TicketTemplate> updateTemplate(@PathVariable Long id, @Valid @RequestBody CreateTemplateDTO dto) {
        TicketTemplate template = templateService.updateTemplate(id, dto);
        return Result.success(template);
    }

    @DeleteMapping("/{id}")
    public Result<Void> deleteTemplate(@PathVariable Long id) {
        templateService.deleteTemplate(id);
        return Result.success();
    }

    @GetMapping("/{id}")
    public Result<TicketTemplate> getTemplateById(@PathVariable Long id) {
        TicketTemplate template = templateService.getTemplateById(id);
        return Result.success(template);
    }

    @GetMapping
    public Result<PageResult<TicketTemplate>> getTemplateList(
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize) {
        Pageable pageable = PageRequest.of(pageNum - 1, pageSize, Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<TicketTemplate> page = templateService.getTemplateList(pageable);
        return Result.success(PageResult.of(page));
    }

    @GetMapping("/enabled")
    public Result<List<TicketTemplate>> getEnabledTemplateList() {
        List<TicketTemplate> templates = templateService.getEnabledTemplateList();
        return Result.success(templates);
    }

    @PutMapping("/{id}/toggle")
    public Result<TicketTemplate> toggleStatus(@PathVariable Long id) {
        TicketTemplate template = templateService.toggleStatus(id);
        return Result.success(template);
    }
}
