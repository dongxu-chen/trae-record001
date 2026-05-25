package com.ticket.repository;

import com.ticket.entity.TicketRelation;
import com.ticket.enums.RelationType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface TicketRelationRepository extends JpaRepository<TicketRelation, Long> {

    @Query("SELECT tr FROM TicketRelation tr WHERE tr.sourceTicket.id = :ticketId OR tr.targetTicket.id = :ticketId")
    List<TicketRelation> findByTicketId(@Param("ticketId") Long ticketId);

    List<TicketRelation> findBySourceTicketIdAndRelationType(Long sourceTicketId, RelationType relationType);

    List<TicketRelation> findByTargetTicketIdAndRelationType(Long targetTicketId, RelationType relationType);

    void deleteBySourceTicketIdAndTargetTicketIdAndRelationType(Long sourceTicketId, Long targetTicketId, RelationType relationType);

    @Query("SELECT CASE WHEN COUNT(tr) > 0 THEN true ELSE false END FROM TicketRelation tr WHERE " +
           "((tr.sourceTicket.id = :ticket1Id AND tr.targetTicket.id = :ticket2Id) OR " +
           "((tr.sourceTicket.id = :ticket2Id AND tr.targetTicket.id = :ticket1Id) AND tr.relationType = :relationType)")
    boolean existsRelation(@Param("ticket1Id") Long ticket1Id,
                       @Param("ticket2Id") Long ticket2Id,
                       @Param("relationType") RelationType relationType);
}
