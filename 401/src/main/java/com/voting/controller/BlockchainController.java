package com.voting.controller;

import com.voting.common.Result;
import com.voting.entity.Block;
import com.voting.entity.VoteReceipt;
import com.voting.service.BlockchainService;
import com.voting.service.VerificationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/blockchain")
@CrossOrigin(origins = "*")
public class BlockchainController {

    @Autowired
    private BlockchainService blockchainService;

    @Autowired
    private VerificationService verificationService;

    @GetMapping("/latest-block")
    public Result<Block> getLatestBlock() {
        Block block = blockchainService.getLatestBlock();
        return Result.success(block);
    }

    @GetMapping("/block/{height}")
    public Result<Block> getBlockByHeight(@PathVariable Long height) {
        Block block = blockchainService.getBlockByHeight(height);
        if (block == null) {
            return Result.error("区块不存在");
        }
        return Result.success(block);
    }

    @GetMapping("/receipt/{hash}")
    public Result<VoteReceipt> getReceiptByHash(@PathVariable String hash) {
        VoteReceipt receipt = blockchainService.getReceiptByHash(hash);
        if (receipt == null) {
            return Result.error("收据不存在");
        }
        return Result.success(receipt);
    }

    @GetMapping("/receipts/vote/{voteId}")
    public Result<List<VoteReceipt>> getReceiptsByVoteId(@PathVariable Long voteId) {
        List<VoteReceipt> receipts = blockchainService.getReceiptsByVoteId(voteId);
        return Result.success(receipts);
    }

    @GetMapping("/verify-receipt/{hash}")
    public Result<Boolean> verifyReceipt(@PathVariable String hash) {
        boolean valid = blockchainService.verifyReceipt(hash);
        return Result.success(valid);
    }

    @GetMapping("/verify-integrity")
    public Result<Boolean> verifyBlockchainIntegrity() {
        boolean valid = blockchainService.verifyBlockchainIntegrity();
        return Result.success(valid);
    }

    @GetMapping("/info")
    public Result<Map<String, Object>> getBlockchainInfo() {
        Map<String, Object> info = verificationService.getBlockchainInfo();
        return Result.success(info);
    }
}
