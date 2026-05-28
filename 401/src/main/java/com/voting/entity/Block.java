package com.voting.entity;

import lombok.Data;

import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "block")
public class Block {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "block_height", nullable = false, unique = true)
    private Long blockHeight;

    @Column(name = "previous_hash", nullable = false, length = 64)
    private String previousHash;

    @Column(name = "merkle_root", nullable = false, length = 64)
    private String merkleRoot;

    @Column(nullable = false, length = 64)
    private String hash;

    @Column(name = "vote_count", nullable = false)
    private Integer voteCount = 0;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @Column(columnDefinition = "TEXT")
    private String data;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }
}
