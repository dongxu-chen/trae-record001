package com.ticket.controller;

import com.ticket.common.Result;
import com.ticket.dto.CreateRelationDTO;
import com.ticket.entity.TicketRelation;
import com.ticket.enums.RelationType;
import com.ticket.service.TicketRelationService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/relations")
@RequiredArgsConstructor
public class TicketRelationController {

    private final TicketRelationService relationService;

    @PostMapping
    public Result<TicketRelation> createRelation(@Valid @RequestBody CreateRelationDTO dto) {
        TicketRelation relation = relationService.createRelation(dto);
        return Result.success(relation);
    }

    @DeleteMapping("/{id}")
    public Result<Void> removeRelation(@PathVariable Long id) {
        relationService.removeRelation(id);
        return Result.success();
    }

    @DeleteMapping
    public Result<Void> removeRelation(
            @RequestParam Long sourceTicketId,
            @RequestParam Long targetTicketId,
            @RequestParam RelationType relationType) {
        relationService.removeRelation(sourceTicketId, targetTicketId, relationType);
        return Result.success();
    }

    @GetMapping("/ticket/{ticketId}")
    public Result<List<TicketRelation>> getTicketRelations(@PathVariable Long ticketId) {
        List<TicketRelation> relations = relationService.getTicketRelations(ticketId);
        return Result.success(relations);
    }

    @GetMapping("/parent/{parentId}")
    public Result<List<TicketRelation>> getChildTickets(@PathVariable Long parentId) {
        List<TicketRelation> relations = relationService.getChildTickets(parentId);
        return Result.success(relations);
    }

    @GetMapping("/child/{childId}")
    public Result<List<TicketRelation>> getParentTickets(@PathVariable Long childId) {
        List<TicketRelation> relations = relationService.getParentTickets(childId);
        return Result.success(relations);
    }

    @GetMapping("/related/{ticketId}")
    public Result<List<TicketRelation>> getRelatedTickets(
            @PathVariable Long ticketId,
            @RequestParam RelationType relationType) {
        List<TicketRelation> relations = relationService.getRelatedTickets(ticketId, relationType);
        return Result.success(relations);
    }
}
