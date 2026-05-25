package com.filetransfer.repository;

import com.filetransfer.entity.UploadedChunk;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface UploadedChunkRepository extends JpaRepository<UploadedChunk, Long> {
    List<UploadedChunk> findByUploadIdOrderByChunkNumberAsc(String uploadId);
    Optional<UploadedChunk> findByUploadIdAndChunkNumber(String uploadId, Integer chunkNumber);
    long countByUploadId(String uploadId);
    void deleteByUploadId(String uploadId);
    boolean existsByUploadIdAndChunkNumber(String uploadId, Integer chunkNumber);
}
