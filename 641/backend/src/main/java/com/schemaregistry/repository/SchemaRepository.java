package com.schemaregistry.repository;

import com.schemaregistry.model.SchemaEntity;
import com.schemaregistry.model.SchemaType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface SchemaRepository extends JpaRepository<SchemaEntity, Long> {
    Optional<SchemaEntity> findBySubject(String subject);
    List<SchemaEntity> findByType(SchemaType type);
    boolean existsBySubject(String subject);

    @Query("SELECT DISTINCT s.subject FROM SchemaEntity s")
    List<String> findAllSubjects();
}
