package com.filetransfer.repository;

import com.filetransfer.entity.FileCollectionLink;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface FileCollectionLinkRepository extends JpaRepository<FileCollectionLink, Long> {
    Optional<FileCollectionLink> findByLinkCode(String linkCode);
    List<FileCollectionLink> findByUserIdOrderByCreatedAtDesc(Long userId);
    List<FileCollectionLink> findByUserIdAndIsActiveTrueOrderByCreatedAtDesc(Long userId);
}
