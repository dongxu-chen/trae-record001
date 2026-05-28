package com.voting.controller;

import com.voting.common.Result;
import com.voting.dto.CreateVoteRequest;
import com.voting.dto.SubmitVoteRequest;
import com.voting.dto.VoteResultDTO;
import com.voting.entity.Vote;
import com.voting.service.VoteService;
import com.voting.util.DeviceFingerprintUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import javax.validation.Valid;
import java.util.List;
import java.util.Optional;

@RestController
@RequestMapping("/api/votes")
@CrossOrigin(origins = "*")
public class VoteController {

    @Autowired
    private VoteService voteService;

    @PostMapping
    public Result<Vote> createVote(@Valid @RequestBody CreateVoteRequest request) {
        Vote vote = voteService.createVote(request);
        return Result.success(vote);
    }

    @GetMapping("/{id}")
    public Result<Vote> getVoteById(@PathVariable Long id) {
        Optional<Vote> voteOpt = voteService.getVoteById(id);
        return voteOpt.map(Result::success)
                .orElse(Result.error("投票不存在"));
    }

    @GetMapping
    public Result<List<Vote>> getAllVotes() {
        List<Vote> votes = voteService.getAllVotes();
        return Result.success(votes);
    }

    @PostMapping("/submit")
    public Result<Boolean> submitVote(@Valid @RequestBody SubmitVoteRequest request,
                                       HttpServletRequest httpRequest) {
        try {
            String ipAddress = DeviceFingerprintUtil.getClientIp(httpRequest);
            String deviceFingerprint = DeviceFingerprintUtil.generateFingerprint(httpRequest);

            boolean success = voteService.submitVote(request, ipAddress, deviceFingerprint);
            return Result.success(success);
        } catch (IllegalArgumentException e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/{id}/result")
    public Result<VoteResultDTO> getVoteResult(@PathVariable Long id) {
        try {
            VoteResultDTO result = voteService.getVoteResult(id);
            return Result.success(result);
        } catch (IllegalArgumentException e) {
            return Result.error(e.getMessage());
        }
    }
}
