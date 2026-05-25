package com.ticket.service;

import com.ticket.dto.CreateSlaDTO;
import com.ticket.entity.Sla;
import com.ticket.enums.TicketPriority;
import com.ticket.enums.TicketType;
import com.ticket.exception.BusinessException;
import com.ticket.repository.SlaRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

@Slf4j
@Service
@RequiredArgsConstructor
public class SlaService {

    private final SlaRepository slaRepository;

    @Transactional
    public Sla createSla(CreateSlaDTO dto) {
        slaRepository.findByName(dto.getName()).ifPresent(s -> {
            throw new BusinessException("SLA名称已存在: " + dto.getName());
        });

        slaRepository.findByTicketTypeAndPriorityAndEnabledTrue(dto.getTicketType(), dto.getPriority())
                .ifPresent(s -> {
                    throw new BusinessException("该工单类型和优先级的SLA已存在");
                });

        Sla sla = new Sla();
        sla.setName(dto.getName());
        sla.setDescription(dto.getDescription());
        sla.setTicketType(dto.getTicketType());
        sla.setPriority(dto.getPriority());
        sla.setResponseTime(dto.getResponseTime());
        sla.setResolutionTime(dto.getResolutionTime());
        sla.setWarningThreshold(dto.getWarningThreshold() != null ? dto.getWarningThreshold() : 30);
        sla.setEnabled(dto.getEnabled());

        return slaRepository.save(sla);
    }

    @Transactional
    public Sla updateSla(Long id, CreateSlaDTO dto) {
        Sla sla = getSlaById(id);

        if (!sla.getName().equals(dto.getName())) {
            slaRepository.findByName(dto.getName()).ifPresent(s -> {
                if (!s.getId().equals(id)) {
                    throw new BusinessException("SLA名称已存在: " + dto.getName());
                }
            });
        }

        sla.setName(dto.getName());
        sla.setDescription(dto.getDescription());
        sla.setTicketType(dto.getTicketType());
        sla.setPriority(dto.getPriority());
        sla.setResponseTime(dto.getResponseTime());
        sla.setResolutionTime(dto.getResolutionTime());
        if (dto.getWarningThreshold() != null) {
            sla.setWarningThreshold(dto.getWarningThreshold());
        }
        sla.setEnabled(dto.getEnabled());

        return slaRepository.save(sla);
    }

    @Transactional
    public void deleteSla(Long id) {
        Sla sla = getSlaById(id);
        slaRepository.delete(sla);
        log.info("SLA已删除: {}", id);
    }

    public Sla getSlaById(Long id) {
        return slaRepository.findById(id)
                .orElseThrow(() -> new BusinessException("SLA不存在: " + id));
    }

    public Optional<Sla> findMatchingSla(TicketType ticketType, TicketPriority priority) {
        return slaRepository.findByTicketTypeAndPriorityAndEnabledTrue(ticketType, priority);
    }

    public Page<Sla> getSlaList(Pageable pageable) {
        return slaRepository.findAll(pageable);
    }

    public List<Sla> getEnabledSlaList() {
        return slaRepository.findByEnabledTrue();
    }

    @Transactional
    public Sla toggleStatus(Long id) {
        Sla sla = getSlaById(id);
        sla.setEnabled(!sla.getEnabled());
        return slaRepository.save(sla);
    }
}
