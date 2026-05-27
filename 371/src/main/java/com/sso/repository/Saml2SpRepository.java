package com.sso.repository;

import com.sso.entity.Saml2Sp;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface Saml2SpRepository extends JpaRepository<Saml2Sp, Long> {

    Optional<Saml2Sp> findByEntityId(String entityId);

    boolean existsByEntityId(String entityId);
}
