package com.filestorage.repository;

import com.filestorage.entity.FileInfo;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface FileInfoRepository extends JpaRepository<FileInfo, Long> {
    Optional<FileInfo> findByTenantIdAndIdAndIsDeleted(Long tenantId, Long id, Integer isDeleted);
    Page<FileInfo> findByTenantIdAndIsDeleted(Long tenantId, Integer isDeleted, Pageable pageable);
    List<FileInfo> findByTenantIdAndFileMd5AndIsDeleted(Long tenantId, String fileMd5, Integer isDeleted);
    Optional<FileInfo> findByIdAndIsDeleted(Long id, Integer isDeleted);
}
