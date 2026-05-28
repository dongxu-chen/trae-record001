package com.voting.entity;

import lombok.Data;

import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "anonymous_credential")
public class AnonymousCredential {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "vote_id", nullable = false)
    private Long voteId;

    @Column(name = "commitment", nullable = false, unique = true, length = 64)
    private String commitment;

    @Column(name = "nullifier", unique = true, length = 64)
    private String nullifier;

    @Column(name = "used", nullable = false)
    private Boolean used = false;

    @Column(name = "used_at")
    private LocalDateTime usedAt;

    @Column(name = "expire_at", nullable = false)
    private LocalDateTime expireAt;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @Column(name = "zk_proof", columnDefinition = "TEXT")
    private String zkProof;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }
}
