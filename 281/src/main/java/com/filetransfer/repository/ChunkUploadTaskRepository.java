package com.filetransfer.repository;

import com.filetransfer.entity.ChunkUploadTask;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface ChunkUploadTaskRepository extends JpaRepository<ChunkUploadTask, Long> {
    Optional<ChunkUploadTask> findByUploadId(String uploadId);
    Optional<ChunkUploadTask> findByFileMd5AndStatus(String fileMd5, String status);
    List<ChunkUploadTask> findByUserIdAndStatus(Long userId, String status);
    List<ChunkUploadTask> findByStatusAndExpiredAtBefore(String status, LocalDateTime expiredAt);
    void deleteByUploadId(String uploadId);
}
