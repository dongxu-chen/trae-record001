package com.ticket.service;

import com.ticket.dto.AddCommentDTO;
import com.ticket.entity.Ticket;
import com.ticket.entity.TicketComment;
import com.ticket.entity.User;
import com.ticket.exception.BusinessException;
import com.ticket.repository.TicketCommentRepository;
import com.ticket.repository.TicketRepository;
import com.ticket.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Slf4j
@Service
@RequiredArgsConstructor
public class TicketCommentService {

    private final TicketCommentRepository commentRepository;
    private final TicketRepository ticketRepository;
    private final UserRepository userRepository;

    @Transactional
    public TicketComment addComment(AddCommentDTO dto) {
        Ticket ticket = ticketRepository.findById(dto.getTicketId())
                .orElseThrow(() -> new BusinessException("工单不存在: " + dto.getTicketId()));

        User author = userRepository.findById(dto.getAuthorId())
                .orElseThrow(() -> new BusinessException("用户不存在: " + dto.getAuthorId()));

        TicketComment comment = new TicketComment();
        comment.setTicket(ticket);
        comment.setContent(dto.getContent());
        comment.setAuthor(author);
        comment.setInternal(dto.getInternal());

        return commentRepository.save(comment);
    }

    public Page<TicketComment> getTicketComments(Long ticketId, boolean includeInternal, Pageable pageable) {
        if (includeInternal) {
            return commentRepository.findByTicketId(ticketId, pageable);
        } else {
            return commentRepository.findByTicketIdAndInternalFalse(ticketId, pageable);
        }
    }

    public long getCommentCount(Long ticketId) {
        return commentRepository.countByTicketId(ticketId);
    }

    @Transactional
    public void deleteComment(Long id) {
        TicketComment comment = commentRepository.findById(id)
                .orElseThrow(() -> new BusinessException("评论不存在: " + id));
        commentRepository.delete(comment);
        log.info("评论已删除: {}", id);
    }
}
