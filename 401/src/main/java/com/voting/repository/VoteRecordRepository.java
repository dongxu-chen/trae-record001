package com.voting.repository;

import com.voting.entity.VoteRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface VoteRecordRepository extends JpaRepository<VoteRecord, Long> {

    @Query("SELECT COUNT(vr) FROM VoteRecord vr WHERE vr.voteId = ?1 AND vr.deviceFingerprint = ?2")
    Long countByVoteIdAndDeviceFingerprint(Long voteId, String deviceFingerprint);

    @Query("SELECT COUNT(vr) FROM VoteRecord vr WHERE vr.voteId = ?1 AND vr.ipAddress = ?2 AND vr.createdAt > ?3")
    Long countByVoteIdAndIpAddressAndTimeAfter(Long voteId, String ipAddress, LocalDateTime time);

    @Query("SELECT COUNT(vr) FROM VoteRecord vr WHERE vr.voteId = ?1 AND vr.voteCodeHash = ?2")
    Long countByVoteIdAndVoteCodeHash(Long voteId, String voteCodeHash);

    List<VoteRecord> findByVoteId(Long voteId);

    @Query("SELECT COUNT(DISTINCT vr.deviceFingerprint) FROM VoteRecord vr WHERE vr.voteId = ?1")
    Long countUniqueVotersByVoteId(Long voteId);
}
