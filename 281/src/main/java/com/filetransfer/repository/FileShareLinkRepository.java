package com.filetransfer.repository;

import com.filetransfer.entity.FileShareLink;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface FileShareLinkRepository extends JpaRepository<FileShareLink, Long> {
    Optional<FileShareLink> findByShareCode(String shareCode);
    List<FileShareLink> findByUserIdOrderByCreatedAtDesc(Long userId);
    List<FileShareLink> findByFileId(Long fileId);
}
