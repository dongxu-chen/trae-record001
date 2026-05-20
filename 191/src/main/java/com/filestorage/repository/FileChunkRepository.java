package com.filestorage.repository;

import com.filestorage.entity.FileChunk;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface FileChunkRepository extends JpaRepository<FileChunk, Long> {
    List<FileChunk> findByTenantIdAndUploadIdOrderByChunkNumber(Long tenantId, String uploadId);
    List<FileChunk> findByTenantIdAndFileMd5AndStatus(Long tenantId, String fileMd5, Integer status);
    Optional<FileChunk> findByTenantIdAndUploadIdAndChunkNumber(Long tenantId, String uploadId, Integer chunkNumber);
    List<FileChunk> findByExpiredAtBefore(LocalDateTime expiredAt);

    @Modifying
    @Transactional
    @Query("DELETE FROM FileChunk f WHERE f.uploadId = :uploadId AND f.tenantId = :tenantId")
    void deleteByTenantIdAndUploadId(Long tenantId, String uploadId);

    @Modifying
    @Transactional
    @Query("DELETE FROM FileChunk f WHERE f.expiredAt < :now")
    int deleteExpiredChunks(LocalDateTime now);
}
