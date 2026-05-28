package com.voting.repository;

import com.voting.entity.AnonymousCredential;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.Optional;

@Repository
public interface AnonymousCredentialRepository extends JpaRepository<AnonymousCredential, Long> {

    Optional<AnonymousCredential> findByCommitment(String commitment);

    Optional<AnonymousCredential> findByNullifier(String nullifier);

    @Query("SELECT COUNT(ac) > 0 FROM AnonymousCredential ac WHERE ac.commitment = ?1 AND ac.used = false AND ac.expireAt > ?2")
    boolean isCommitmentValid(String commitment, LocalDateTime now);

    @Query("SELECT COUNT(ac) > 0 FROM AnonymousCredential ac WHERE ac.nullifier = ?1 AND ac.used = true")
    boolean isNullifierUsed(String nullifier);

    @Modifying
    @Transactional
    @Query("UPDATE AnonymousCredential ac SET ac.used = true, ac.usedAt = ?3 WHERE ac.commitment = ?1 AND ac.used = false AND ac.expireAt > ?2")
    int markAsUsed(String commitment, LocalDateTime now, LocalDateTime usedAt);
}
