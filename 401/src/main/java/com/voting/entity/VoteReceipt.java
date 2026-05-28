package com.voting.entity;

import lombok.Data;

import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "vote_receipt")
public class VoteReceipt {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "vote_id", nullable = false)
    private Long voteId;

    @Column(name = "record_hash", nullable = false, unique = true, length = 64)
    private String recordHash;

    @Column(name = "block_height")
    private Long blockHeight;

    @Column(name = "merkle_proof", columnDefinition = "TEXT")
    private String merkleProof;

    @Column(name = "nullifier", unique = true, length = 64)
    private String nullifier;

    @Column(name = "commitment", length = 64)
    private String commitment;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }
}
