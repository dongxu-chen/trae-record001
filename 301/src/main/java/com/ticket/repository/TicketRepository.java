package com.ticket.repository;

import com.ticket.entity.Ticket;
import com.ticket.enums.SlaStatus;
import com.ticket.enums.TicketPriority;
import com.ticket.enums.TicketStatus;
import com.ticket.enums.TicketType;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface TicketRepository extends JpaRepository<Ticket, Long> {

    Optional<Ticket> findByTicketNo(String ticketNo);

    Page<Ticket> findByCreatorId(Long creatorId, Pageable pageable);

    Page<Ticket> findByAssigneeId(Long assigneeId, Pageable pageable);

    Page<Ticket> findByStatus(TicketStatus status, Pageable pageable);

    Page<Ticket> findByStatusIn(List<TicketStatus> statuses, Pageable pageable);

    Page<Ticket> findByAssigneeIdAndStatus(Long assigneeId, TicketStatus status, Pageable pageable);

    List<Ticket> findByStatusInAndSlaStatusNotIn(List<TicketStatus> statuses, List<SlaStatus> slaStatuses);

    @Query("SELECT t FROM Ticket t WHERE t.status IN :statuses AND " +
           "(t.responseDeadline < :now OR t.resolutionDeadline < :now) AND " +
           "t.slaStatus NOT IN ('MET', 'VIOLATED')")
    List<Ticket> findOverdueTickets(@Param("statuses") List<TicketStatus> statuses, @Param("now") LocalDateTime now);

    @Query("SELECT t FROM Ticket t WHERE t.status IN :statuses AND " +
           "t.responseDeadline BETWEEN :now AND :warningTime AND " +
           "t.slaStatus = 'NORMAL'")
    List<Ticket> findWarningTickets(@Param("statuses") List<TicketStatus> statuses,
                                     @Param("now") LocalDateTime now,
                                     @Param("warningTime") LocalDateTime warningTime);

    long countByStatus(TicketStatus status);

    long countByAssigneeIdAndStatus(Long assigneeId, TicketStatus status);

    long countByPriorityAndStatusNot(TicketPriority priority, TicketStatus status);

    Page<Ticket> findByTicketType(TicketType ticketType, Pageable pageable);

    Page<Ticket> findByPriority(TicketPriority priority, Pageable pageable);

    @Query("SELECT t FROM Ticket t WHERE " +
           "(:title IS NULL OR t.title LIKE %:title%) AND " +
           "(:status IS NULL OR t.status = :status) AND " +
           "(:priority IS NULL OR t.priority = :priority) AND " +
           "(:ticketType IS NULL OR t.ticketType = :ticketType) AND " +
           "(:assigneeId IS NULL OR t.assignee.id = :assigneeId)")
    Page<Ticket> findByConditions(@Param("title") String title,
                           @Param("status") TicketStatus status,
                           @Param("priority") TicketPriority priority,
                           @Param("ticketType") TicketType ticketType,
                           @Param("assigneeId") Long assigneeId,
                           Pageable pageable);
}
