package com.ticket.controller;

import com.ticket.common.PageResult;
import com.ticket.common.Result;
import com.ticket.dto.CreateSlaDTO;
import com.ticket.entity.Sla;
import com.ticket.service.SlaService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/slas")
@RequiredArgsConstructor
public class SlaController {

    private final SlaService slaService;

    @PostMapping
    public Result<Sla> createSla(@Valid @RequestBody CreateSlaDTO dto) {
        Sla sla = slaService.createSla(dto);
        return Result.success(sla);
    }

    @PutMapping("/{id}")
    public Result<Sla> updateSla(@PathVariable Long id, @Valid @RequestBody CreateSlaDTO dto) {
        Sla sla = slaService.updateSla(id, dto);
        return Result.success(sla);
    }

    @DeleteMapping("/{id}")
    public Result<Void> deleteSla(@PathVariable Long id) {
        slaService.deleteSla(id);
        return Result.success();
    }

    @GetMapping("/{id}")
    public Result<Sla> getSlaById(@PathVariable Long id) {
        Sla sla = slaService.getSlaById(id);
        return Result.success(sla);
    }

    @GetMapping
    public Result<PageResult<Sla>> getSlaList(
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize) {
        Pageable pageable = PageRequest.of(pageNum - 1, pageSize, Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<Sla> page = slaService.getSlaList(pageable);
        return Result.success(PageResult.of(page));
    }

    @GetMapping("/enabled")
    public Result<List<Sla>> getEnabledSlaList() {
        List<Sla> slas = slaService.getEnabledSlaList();
        return Result.success(slas);
    }

    @PutMapping("/{id}/toggle")
    public Result<Sla> toggleStatus(@PathVariable Long id) {
        Sla sla = slaService.toggleStatus(id);
        return Result.success(sla);
    }
}
