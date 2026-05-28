package com.voting.repository;

import com.voting.entity.VoteOption;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Repository
public interface VoteOptionRepository extends JpaRepository<VoteOption, Long> {

    List<VoteOption> findByVoteIdOrderBySortOrderAsc(Long voteId);

    @Modifying
    @Transactional
    @Query("UPDATE VoteOption vo SET vo.voteCount = vo.voteCount + 1 WHERE vo.id = ?1")
    void incrementVoteCount(Long optionId);

    @Modifying
    @Transactional
    @Query("UPDATE VoteOption vo SET vo.voteCount = vo.voteCount + 1, vo.totalScore = vo.totalScore + ?2, vo.avgScore = (vo.totalScore + ?2) / (vo.voteCount + 1) WHERE vo.id = ?1")
    void incrementVoteCountWithScore(Long optionId, Integer score);
}
