package com.ticket.service;

import com.ticket.entity.Ticket;
import com.ticket.entity.TicketHistory;
import com.ticket.entity.User;
import com.ticket.enums.TicketStatus;
import com.ticket.repository.TicketHistoryRepository;
import com.ticket.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class TicketHistoryService {

    private final TicketHistoryRepository historyRepository;
    private final UserRepository userRepository;

    @Transactional
    public TicketHistory addHistory(Ticket ticket, String action, TicketStatus fromStatus,
                                    TicketStatus toStatus, String remark, Long operatorId) {
        TicketHistory history = new TicketHistory();
        history.setTicket(ticket);
        history.setAction(action);
        history.setFromStatus(fromStatus);
        history.setToStatus(toStatus);
        history.setRemark(remark);

        if (operatorId != null) {
            User operator = userRepository.findById(operatorId).orElse(null);
            history.setOperator(operator);
        }

        return historyRepository.save(history);
    }

    @Transactional
    public TicketHistory addHistory(Ticket ticket, String action, String remark, Long operatorId) {
        return addHistory(ticket, action, null, null, remark, operatorId);
    }

    @Transactional
    public TicketHistory addStatusChangeHistory(Ticket ticket, TicketStatus fromStatus,
                                                TicketStatus toStatus, String remark, Long operatorId) {
        String action = fromStatus == null ? "创建工单" : "状态变更: " + fromStatus.getName() + " -> " + toStatus.getName();
        return addHistory(ticket, action, fromStatus, toStatus, remark, operatorId);
    }

    public List<TicketHistory> getTicketHistory(Long ticketId) {
        return historyRepository.findByTicketIdOrderByCreatedAtDesc(ticketId);
    }

    public List<TicketHistory> getTicketHistoryByAction(Long ticketId, String action) {
        return historyRepository.findByTicketIdAndAction(ticketId, action);
    }
}
