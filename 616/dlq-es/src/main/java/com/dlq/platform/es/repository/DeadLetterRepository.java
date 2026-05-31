package com.dlq.platform.es.repository;

import com.dlq.platform.common.dto.DeadLetterQueryDTO;
import com.dlq.platform.common.entity.DeadLetterMessage;
import com.dlq.platform.common.enums.ProcessStatusEnum;
import org.springframework.data.domain.Page;

import java.util.List;
import java.util.Optional;

public interface DeadLetterRepository {

    DeadLetterMessage save(DeadLetterMessage message);

    List<DeadLetterMessage> saveBatch(List<DeadLetterMessage> messages);

    Optional<DeadLetterMessage> findById(String id);

    Page<DeadLetterMessage> search(DeadLetterQueryDTO query);

    boolean updateStatus(String id, ProcessStatusEnum status);

    boolean deleteById(String id);

    long countByQuery(DeadLetterQueryDTO query);

    boolean archive(String id, String archiveIndex);

    boolean batchArchive(List<String> ids, String archiveIndex);
}
