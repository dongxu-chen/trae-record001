package com.voting.repository;

import com.voting.entity.VoteCode;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface VoteCodeRepository extends JpaRepository<VoteCode, Long> {

    Optional<VoteCode> findByCodeHash(String codeHash);

    Optional<VoteCode> findByCode(String code);

    List<VoteCode> findByVoteId(Long voteId);

    @Query("SELECT vc FROM VoteCode vc WHERE vc.voteId = ?1 AND vc.used = false AND vc.expireAt > ?2")
    List<VoteCode> findAvailableCodesByVoteId(Long voteId, LocalDateTime now);

    @Modifying
    @Transactional
    @Query("UPDATE VoteCode vc SET vc.used = true, vc.usedAt = ?3 WHERE vc.id = ?1 AND vc.used = false")
    int markAsUsed(Long id, LocalDateTime usedAt);

    @Query("SELECT COUNT(vc) FROM VoteCode vc WHERE vc.voteId = ?1 AND vc.used = true")
    Long countUsedCodesByVoteId(Long voteId);
}
