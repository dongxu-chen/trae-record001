package com.voting.repository;

import com.voting.entity.Block;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface BlockRepository extends JpaRepository<Block, Long> {

    Optional<Block> findTopByOrderByBlockHeightDesc();

    Optional<Block> findByBlockHeight(Long blockHeight);

    @Query("SELECT MAX(b.blockHeight) FROM Block b")
    Long getMaxBlockHeight();
}
