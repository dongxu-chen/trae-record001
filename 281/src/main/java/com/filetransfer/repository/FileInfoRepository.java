package com.filetransfer.repository;

import com.filetransfer.entity.FileInfo;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface FileInfoRepository extends JpaRepository<FileInfo, Long> {
    Optional<FileInfo> findByFileMd5(String fileMd5);
    Optional<FileInfo> findByFileMd5AndFileSize(String fileMd5, Long fileSize);
    List<FileInfo> findByUserIdAndIsDeletedFalse(Long userId);
    Optional<FileInfo> findByIdAndIsDeletedFalse(Long id);
    boolean existsByFileMd5(String fileMd5);
    boolean existsByFileMd5AndFileSize(String fileMd5, Long fileSize);
}
