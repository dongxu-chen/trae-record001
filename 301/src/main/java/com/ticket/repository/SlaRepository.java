package com.ticket.repository;

import com.ticket.entity.Sla;
import com.ticket.enums.TicketPriority;
import com.ticket.enums.TicketType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface SlaRepository extends JpaRepository<Sla, Long> {

    Optional<Sla> findByTicketTypeAndPriorityAndEnabledTrue(TicketType ticketType, TicketPriority priority);

    List<Sla> findByEnabledTrue();

    Optional<Sla> findByName(String name);
}
