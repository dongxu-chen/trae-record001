package com.schemaregistry.repository;

import com.schemaregistry.model.SchemaVersion;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface SchemaVersionRepository extends JpaRepository<SchemaVersion, Long> {
    List<SchemaVersion> findBySchemaIdOrderByVersionDesc(Long schemaId);

    @Query("SELECT sv FROM SchemaVersion sv WHERE sv.schema.subject = :subject ORDER BY sv.version DESC")
    List<SchemaVersion> findBySubjectOrderByVersionDesc(@Param("subject") String subject);

    @Query("SELECT MAX(sv.version) FROM SchemaVersion sv WHERE sv.schema.id = :schemaId")
    Optional<Integer> findMaxVersionBySchemaId(@Param("schemaId") Long schemaId);

    @Query("SELECT sv FROM SchemaVersion sv WHERE sv.schema.subject = :subject AND sv.version = :version")
    Optional<SchemaVersion> findBySubjectAndVersion(@Param("subject") String subject, @Param("version") Integer version);
}
