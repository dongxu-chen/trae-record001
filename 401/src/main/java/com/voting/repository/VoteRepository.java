package com.voting.repository;

import com.voting.entity.Vote;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface VoteRepository extends JpaRepository<Vote, Long> {

    List<Vote> findByActiveTrueOrderByCreatedAtDesc();

    Optional<Vote> findByIdAndActiveTrue(Long id);

    @Query("SELECT v FROM Vote v WHERE v.active = true AND v.createdBy = ?1 ORDER BY v.createdAt DESC")
    List<Vote> findByCreator(String createdBy);
}
