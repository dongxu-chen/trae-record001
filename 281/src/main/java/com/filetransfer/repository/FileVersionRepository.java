package com.filetransfer.repository;

import com.filetransfer.entity.FileVersion;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface FileVersionRepository extends JpaRepository<FileVersion, Long> {
    List<FileVersion> findByFileIdOrderByVersionNumberDesc(Long fileId);
    Optional<FileVersion> findByFileIdAndIsCurrentTrue(Long fileId);
    Optional<FileVersion> findByFileIdAndVersionNumber(Long fileId, Integer versionNumber);
    Optional<FileVersion> findByFileIdAndFileMd5(Long fileId, String fileMd5);
    Integer countByFileId(Long fileId);
}
