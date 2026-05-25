package com.ticket.service;

import com.ticket.dto.CreateRelationDTO;
import com.ticket.entity.Ticket;
import com.ticket.entity.TicketRelation;
import com.ticket.entity.User;
import com.ticket.enums.RelationType;
import com.ticket.exception.BusinessException;
import com.ticket.repository.TicketRelationRepository;
import com.ticket.repository.TicketRepository;
import com.ticket.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class TicketRelationService {

    private final TicketRelationRepository relationRepository;
    private final TicketRepository ticketRepository;
    private final UserRepository userRepository;

    @Transactional
    public TicketRelation createRelation(CreateRelationDTO dto) {
        if (dto.getSourceTicketId().equals(dto.getTargetTicketId())) {
            throw new BusinessException("不能与自己建立关联");
        }

        Ticket sourceTicket = ticketRepository.findById(dto.getSourceTicketId())
                .orElseThrow(() -> new BusinessException("源工单不存在: " + dto.getSourceTicketId()));

        Ticket targetTicket = ticketRepository.findById(dto.getTargetTicketId())
                .orElseThrow(() -> new BusinessException("目标工单不存在: " + dto.getTargetTicketId()));

        if (relationRepository.existsRelation(dto.getSourceTicketId(), dto.getTargetTicketId(), dto.getRelationType())) {
            throw new BusinessException("该关联已存在");
        }

        if (dto.getRelationType() == RelationType.PARENT_CHILD) {
            checkCircularDependency(dto.getSourceTicketId(), dto.getTargetTicketId());
        }

        TicketRelation relation = new TicketRelation();
        relation.setSourceTicket(sourceTicket);
        relation.setTargetTicket(targetTicket);
        relation.setRelationType(dto.getRelationType());

        if (dto.getCreatedById() != null) {
            User createdBy = userRepository.findById(dto.getCreatedById())
                    .orElseThrow(() -> new BusinessException("创建人不存在: " + dto.getCreatedById()));
            relation.setCreatedBy(createdBy);
        }

        return relationRepository.save(relation);
    }

    private void checkCircularDependency(Long parentId, Long childId) {
        List<TicketRelation> relations = relationRepository.findBySourceTicketIdAndRelationType(childId, RelationType.PARENT_CHILD);
        for (TicketRelation relation : relations) {
            if (relation.getTargetTicket().getId().equals(parentId)) {
                throw new BusinessException("存在循环依赖，无法建立父子关系");
            }
            checkCircularDependency(parentId, relation.getTargetTicket().getId());
        }
    }

    @Transactional
    public void removeRelation(Long sourceTicketId, Long targetTicketId, RelationType relationType) {
        relationRepository.deleteBySourceTicketIdAndTargetTicketIdAndRelationType(
                sourceTicketId, targetTicketId, relationType
        );
        log.info("工单关联已删除: {} -> {}, 类型: {}", sourceTicketId, targetTicketId, relationType);
    }

    @Transactional
    public void removeRelation(Long id) {
        TicketRelation relation = relationRepository.findById(id)
                .orElseThrow(() -> new BusinessException("关联不存在: " + id));
        relationRepository.delete(relation);
        log.info("工单关联已删除: {}", id);
    }

    public List<TicketRelation> getTicketRelations(Long ticketId) {
        return relationRepository.findByTicketId(ticketId);
    }

    public List<TicketRelation> getChildTickets(Long parentTicketId) {
        return relationRepository.findBySourceTicketIdAndRelationType(parentTicketId, RelationType.PARENT_CHILD);
    }

    public List<TicketRelation> getParentTickets(Long childTicketId) {
        return relationRepository.findByTargetTicketIdAndRelationType(childTicketId, RelationType.PARENT_CHILD);
    }

    public List<TicketRelation> getRelatedTickets(Long ticketId, RelationType relationType) {
        return relationRepository.findBySourceTicketIdAndRelationType(ticketId, relationType);
    }
}
