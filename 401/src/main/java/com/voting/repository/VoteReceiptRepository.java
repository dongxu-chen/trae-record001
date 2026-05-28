package com.voting.repository;

import com.voting.entity.VoteReceipt;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface VoteReceiptRepository extends JpaRepository<VoteReceipt, Long> {

    Optional<VoteReceipt> findByRecordHash(String recordHash);

    List<VoteReceipt> findByVoteId(Long voteId);

    List<VoteReceipt> findByBlockHeightIsNull();

    List<VoteReceipt> findByVoteIdOrderByIdAsc(Long voteId);

    Optional<VoteReceipt> findByNullifier(String nullifier);
}
