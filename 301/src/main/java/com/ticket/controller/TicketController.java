package com.ticket.controller;

import com.ticket.common.PageResult;
import com.ticket.common.Result;
import com.ticket.dto.AddCommentDTO;
import com.ticket.dto.AssignTicketDTO;
import com.ticket.dto.CreateTicketDTO;
import com.ticket.dto.TicketQueryDTO;
import com.ticket.dto.UpdateTicketStatusDTO;
import com.ticket.entity.Ticket;
import com.ticket.entity.TicketComment;
import com.ticket.entity.TicketHistory;
import com.ticket.entity.TicketRelation;
import com.ticket.service.TicketCommentService;
import com.ticket.service.TicketHistoryService;
import com.ticket.service.TicketRelationService;
import com.ticket.service.TicketService;
import com.ticket.vo.TicketVO;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/tickets")
@RequiredArgsConstructor
public class TicketController {

    private final TicketService ticketService;
    private final TicketHistoryService historyService;
    private final TicketCommentService commentService;
    private final TicketRelationService relationService;

    @PostMapping
    public Result<Ticket> createTicket(@Valid @RequestBody CreateTicketDTO dto) {
        Ticket ticket = ticketService.createTicket(dto);
        return Result.success(ticket);
    }

    @PostMapping("/assign")
    public Result<Ticket> assignTicket(@Valid @RequestBody AssignTicketDTO dto) {
        Ticket ticket = ticketService.assignTicket(dto);
        return Result.success(ticket);
    }

    @PostMapping("/status")
    public Result<Ticket> updateStatus(@Valid @RequestBody UpdateTicketStatusDTO dto) {
        Ticket ticket = ticketService.updateStatus(dto);
        return Result.success(ticket);
    }

    @GetMapping("/{id}")
    public Result<TicketVO> getTicketById(@PathVariable Long id) {
        TicketVO ticket = ticketService.getTicketVOById(id);
        return Result.success(ticket);
    }

    @GetMapping("/no/{ticketNo}")
    public Result<Ticket> getTicketByNo(@PathVariable String ticketNo) {
        Ticket ticket = ticketService.getTicketByNo(ticketNo);
        return Result.success(ticket);
    }

    @GetMapping
    public Result<PageResult<TicketVO>> getTicketList(TicketQueryDTO dto) {
        Page<TicketVO> page = ticketService.getTicketList(dto);
        return Result.success(PageResult.of(page));
    }

    @GetMapping("/created/{creatorId}")
    public Result<PageResult<TicketVO>> getMyCreatedTickets(
            @PathVariable Long creatorId,
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize) {
        Pageable pageable = PageRequest.of(pageNum - 1, pageSize);
        Page<TicketVO> page = ticketService.getMyCreatedTickets(creatorId, pageable);
        return Result.success(PageResult.of(page));
    }

    @GetMapping("/assigned/{assigneeId}")
    public Result<PageResult<TicketVO>> getMyAssignedTickets(
            @PathVariable Long assigneeId,
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize) {
        Pageable pageable = PageRequest.of(pageNum - 1, pageSize);
        Page<TicketVO> page = ticketService.getMyAssignedTickets(assigneeId, pageable);
        return Result.success(PageResult.of(page));
    }

    @GetMapping("/statistics")
    public Result<Map<String, Object>> getStatistics() {
        Map<String, Object> stats = ticketService.getTicketStatistics();
        return Result.success(stats);
    }

    @GetMapping("/statistics/user/{userId}")
    public Result<Map<String, Object>> getUserStatistics(@PathVariable Long userId) {
        Map<String, Object> stats = ticketService.getUserTicketStatistics(userId);
        return Result.success(stats);
    }

    @GetMapping("/{id}/history")
    public Result<List<TicketHistory>> getTicketHistory(@PathVariable Long id) {
        List<TicketHistory> history = historyService.getTicketHistory(id);
        return Result.success(history);
    }

    @PostMapping("/comments")
    public Result<TicketComment> addComment(@Valid @RequestBody AddCommentDTO dto) {
        TicketComment comment = commentService.addComment(dto);
        return Result.success(comment);
    }

    @GetMapping("/{id}/comments")
    public Result<PageResult<TicketComment>> getTicketComments(
            @PathVariable Long id,
            @RequestParam(defaultValue = "false") Boolean includeInternal,
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize) {
        Pageable pageable = PageRequest.of(pageNum - 1, pageSize);
        Page<TicketComment> page = commentService.getTicketComments(id, includeInternal, pageable);
        return Result.success(PageResult.of(page));
    }

    @DeleteMapping("/comments/{id}")
    public Result<Void> deleteComment(@PathVariable Long id) {
        commentService.deleteComment(id);
        return Result.success();
    }

    @GetMapping("/{id}/relations")
    public Result<List<TicketRelation>> getTicketRelations(@PathVariable Long id) {
        List<TicketRelation> relations = relationService.getTicketRelations(id);
        return Result.success(relations);
    }

    @GetMapping("/{id}/children")
    public Result<List<TicketRelation>> getChildTickets(@PathVariable Long id) {
        List<TicketRelation> relations = relationService.getChildTickets(id);
        return Result.success(relations);
    }

    @GetMapping("/{id}/parents")
    public Result<List<TicketRelation>> getParentTickets(@PathVariable Long id) {
        List<TicketRelation> relations = relationService.getParentTickets(id);
        return Result.success(relations);
    }

    @GetMapping("/{id}/progress")
    public Result<Map<String, Object>> getTicketProgress(@PathVariable Long id) {
        Map<String, Object> progress = ticketService.getTicketProgress(id);
        return Result.success(progress);
    }

    @PostMapping("/{id}/progress/refresh")
    public Result<Void> refreshParentProgress(@PathVariable Long id) {
        ticketService.updateParentTicketProgress(id);
        return Result.success();
    }
}
