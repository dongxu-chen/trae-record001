package com.ticket.repository;

import com.ticket.entity.TicketComment;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface TicketCommentRepository extends JpaRepository<TicketComment, Long> {

    List<TicketComment> findByTicketIdOrderByCreatedAtDesc(Long ticketId);

    Page<TicketComment> findByTicketIdAndInternalFalse(Long ticketId, Pageable pageable);

    Page<TicketComment> findByTicketId(Long ticketId, Pageable pageable);

    long countByTicketId(Long ticketId);
}
