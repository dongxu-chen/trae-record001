package com.ticket.repository;

import com.ticket.entity.TicketTemplate;
import com.ticket.enums.TicketType;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface TicketTemplateRepository extends JpaRepository<TicketTemplate, Long> {

    Optional<TicketTemplate> findByName(String name);

    List<TicketTemplate> findByEnabledTrue();

    Page<TicketTemplate> findByTicketType(TicketType ticketType, Pageable pageable);

    Page<TicketTemplate> findByEnabledTrue(Pageable pageable);
}
