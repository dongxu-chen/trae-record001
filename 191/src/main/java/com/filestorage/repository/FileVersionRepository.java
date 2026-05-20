package com.filestorage.repository;

import com.filestorage.entity.FileVersion;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

@Repository
public interface FileVersionRepository extends JpaRepository<FileVersion, Long> {

    List<FileVersion> findByFileIdOrderByVersionNumberDesc(Long fileId);

    List<FileVersion> findByTenantIdAndFileIdOrderByVersionNumberDesc(Long tenantId, Long fileId);

    Optional<FileVersion> findByFileIdAndVersionNumber(Long fileId, Integer versionNumber);

    Optional<FileVersion> findByTenantIdAndFileIdAndVersionNumber(Long tenantId, Long fileId, Integer versionNumber);

    @Query("SELECT COALESCE(MAX(fv.versionNumber), 0) FROM FileVersion fv WHERE fv.fileId = :fileId")
    Integer findMaxVersionNumber(Long fileId);

    @Modifying
    @Transactional
    @Query("DELETE FROM FileVersion fv WHERE fv.fileId = :fileId AND fv.versionNumber <= :maxVersionToDelete")
    int deleteOldVersions(Long fileId, Integer maxVersionToDelete);

    @Modifying
    @Transactional
    void deleteByFileId(Long fileId);
}
