package com.filestorage.repository;

import com.filestorage.entity.RecycleBin;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface RecycleBinRepository extends JpaRepository<RecycleBin, Long> {
    Page<RecycleBin> findByTenantId(Long tenantId, Pageable pageable);
    Optional<RecycleBin> findByTenantIdAndId(Long tenantId, Long id);
    Optional<RecycleBin> findByTenantIdAndFileId(Long tenantId, Long fileId);
    List<RecycleBin> findByExpiredAtBefore(LocalDateTime now);

    @Modifying
    @Transactional
    @Query("DELETE FROM RecycleBin r WHERE r.expireAt < :now")
    int deleteExpiredFiles(LocalDateTime now);
}
