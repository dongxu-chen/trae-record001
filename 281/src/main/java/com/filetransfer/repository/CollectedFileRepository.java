package com.filetransfer.repository;

import com.filetransfer.entity.CollectedFile;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface CollectedFileRepository extends JpaRepository<CollectedFile, Long> {
    List<CollectedFile> findByLinkIdOrderByCreatedAtDesc(Long linkId);
    List<CollectedFile> findByLinkCodeOrderByCreatedAtDesc(String linkCode);
    long countByLinkId(Long linkId);
}
