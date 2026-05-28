package com.voting.entity;

import lombok.Data;

import javax.persistence.*;

@Data
@Entity
@Table(name = "vote_option")
public class VoteOption {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "vote_id", nullable = false)
    private Vote vote;

    @Column(nullable = false, length = 500)
    private String content;

    @Column(name = "sort_order")
    private Integer sortOrder = 0;

    @Column(name = "vote_count")
    private Long voteCount = 0L;

    @Column(name = "total_score")
    private Double totalScore = 0.0;

    @Column(name = "avg_score")
    private Double avgScore = 0.0;
}
