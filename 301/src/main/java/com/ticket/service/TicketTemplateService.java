package com.ticket.service;

import com.ticket.dto.CreateTemplateDTO;
import com.ticket.entity.Sla;
import com.ticket.entity.TicketTemplate;
import com.ticket.entity.User;
import com.ticket.exception.BusinessException;
import com.ticket.repository.SlaRepository;
import com.ticket.repository.TicketTemplateRepository;
import com.ticket.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class TicketTemplateService {

    private final TicketTemplateRepository templateRepository;
    private final UserRepository userRepository;
    private final SlaRepository slaRepository;

    @Transactional
    public TicketTemplate createTemplate(CreateTemplateDTO dto) {
        templateRepository.findByName(dto.getName()).ifPresent(t -> {
            throw new BusinessException("模板名称已存在: " + dto.getName());
        });

        TicketTemplate template = new TicketTemplate();
        template.setName(dto.getName());
        template.setDescription(dto.getDescription());
        template.setTicketType(dto.getTicketType());
        template.setDefaultPriority(dto.getDefaultPriority());
        template.setDefaultDescription(dto.getDefaultDescription());
        template.setCustomFields(dto.getCustomFields());
        template.setEnabled(dto.getEnabled());

        if (dto.getDefaultAssigneeId() != null) {
            User assignee = userRepository.findById(dto.getDefaultAssigneeId())
                    .orElseThrow(() -> new BusinessException("默认处理人不存在: " + dto.getDefaultAssigneeId()));
            template.setDefaultAssignee(assignee);
        }

        if (dto.getSlaId() != null) {
            Sla sla = slaRepository.findById(dto.getSlaId())
                    .orElseThrow(() -> new BusinessException("SLA不存在: " + dto.getSlaId()));
            template.setSla(sla);
        }

        return templateRepository.save(template);
    }

    @Transactional
    public TicketTemplate updateTemplate(Long id, CreateTemplateDTO dto) {
        TicketTemplate template = getTemplateById(id);

        if (!template.getName().equals(dto.getName())) {
            templateRepository.findByName(dto.getName()).ifPresent(t -> {
                if (!t.getId().equals(id)) {
                    throw new BusinessException("模板名称已存在: " + dto.getName());
                }
            });
        }

        template.setName(dto.getName());
        template.setDescription(dto.getDescription());
        template.setTicketType(dto.getTicketType());
        template.setDefaultPriority(dto.getDefaultPriority());
        template.setDefaultDescription(dto.getDefaultDescription());
        template.setCustomFields(dto.getCustomFields());
        template.setEnabled(dto.getEnabled());

        if (dto.getDefaultAssigneeId() != null) {
            User assignee = userRepository.findById(dto.getDefaultAssigneeId())
                    .orElseThrow(() -> new BusinessException("默认处理人不存在: " + dto.getDefaultAssigneeId()));
            template.setDefaultAssignee(assignee);
        } else {
            template.setDefaultAssignee(null);
        }

        if (dto.getSlaId() != null) {
            Sla sla = slaRepository.findById(dto.getSlaId())
                    .orElseThrow(() -> new BusinessException("SLA不存在: " + dto.getSlaId()));
            template.setSla(sla);
        } else {
            template.setSla(null);
        }

        return templateRepository.save(template);
    }

    @Transactional
    public void deleteTemplate(Long id) {
        TicketTemplate template = getTemplateById(id);
        templateRepository.delete(template);
        log.info("工单模板已删除: {}", id);
    }

    public TicketTemplate getTemplateById(Long id) {
        return templateRepository.findById(id)
                .orElseThrow(() -> new BusinessException("工单模板不存在: " + id));
    }

    public Page<TicketTemplate> getTemplateList(Pageable pageable) {
        return templateRepository.findAll(pageable);
    }

    public Page<TicketTemplate> getEnabledTemplateList(Pageable pageable) {
        return templateRepository.findByEnabledTrue(pageable);
    }

    public List<TicketTemplate> getEnabledTemplateList() {
        return templateRepository.findByEnabledTrue();
    }

    @Transactional
    public TicketTemplate toggleStatus(Long id) {
        TicketTemplate template = getTemplateById(id);
        template.setEnabled(!template.getEnabled());
        return templateRepository.save(template);
    }
}
