package com.voting.service;

import com.alibaba.fastjson.JSON;
import com.voting.dto.VoteResultDTO;
import com.voting.entity.Block;
import com.voting.entity.VoteOption;
import com.voting.entity.VoteReceipt;
import com.voting.entity.VoteRecord;
import com.voting.repository.VoteOptionRepository;
import com.voting.repository.VoteRecordRepository;
import com.voting.util.CryptoUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.stream.Collectors;

@Service
public class VerificationService {

    @Autowired
    private BlockchainService blockchainService;

    @Autowired
    private VoteRecordRepository voteRecordRepository;

    @Autowired
    private VoteOptionRepository voteOptionRepository;

    public Map<String, Object> generateVerificationData(Long voteId) {
        Map<String, Object> result = new LinkedHashMap<>();

        List<VoteReceipt> receipts = blockchainService.getReceiptsByVoteId(voteId);
        List<VoteRecord> records = voteRecordRepository.findByVoteId(voteId);
        List<VoteOption> options = voteOptionRepository.findByVoteIdOrderBySortOrderAsc(voteId);

        result.put("voteId", voteId);
        result.put("totalRecords", records.size());
        result.put("totalReceipts", receipts.size());
        result.put("generatedAt", System.currentTimeMillis());

        List<Map<String, Object>> receiptList = new ArrayList<>();
        for (VoteReceipt receipt : receipts) {
            Map<String, Object> r = new LinkedHashMap<>();
            r.put("recordHash", receipt.getRecordHash());
            r.put("blockHeight", receipt.getBlockHeight());
            r.put("nullifier", receipt.getNullifier());
            r.put("merkleProof", receipt.getMerkleProof() != null ?
                    JSON.parseObject(receipt.getMerkleProof(), String[].class) : null);
            receiptList.add(r);
        }
        result.put("receipts", receiptList);

        List<Map<String, Object>> optionSummary = new ArrayList<>();
        for (VoteOption option : options) {
            long count = records.stream()
                    .filter(r -> option.getId().equals(r.getOptionId()))
                    .count();

            double totalScore = records.stream()
                    .filter(r -> option.getId().equals(r.getOptionId()) && r.getVoteScore() != null)
                    .mapToInt(VoteRecord::getVoteScore)
                    .sum();

            Map<String, Object> o = new LinkedHashMap<>();
            o.put("optionId", option.getId());
            o.put("content", option.getContent());
            o.put("voteCount", count);
            o.put("totalScore", totalScore);
            o.put("avgScore", count > 0 ? totalScore / count : 0);
            optionSummary.add(o);
        }
        result.put("options", optionSummary);

        long totalVotes = records.size();
        List<Map<String, Object>> verification = new ArrayList<>();

        for (VoteOption option : options) {
            long expectedCount = option.getVoteCount();
            long actualCount = records.stream()
                    .filter(r -> option.getId().equals(r.getOptionId()))
                    .count();

            Map<String, Object> v = new LinkedHashMap<>();
            v.put("optionId", option.getId());
            v.put("optionContent", option.getContent());
            v.put("storedCount", expectedCount);
            v.put("recalculatedCount", actualCount);
            v.put("countMatch", expectedCount == actualCount);

            double expectedAvg = option.getAvgScore() != null ? option.getAvgScore() : 0;
            double actualTotal = records.stream()
                    .filter(r -> option.getId().equals(r.getOptionId()) && r.getVoteScore() != null)
                    .mapToInt(VoteRecord::getVoteScore)
                    .sum();
            double actualAvg = actualCount > 0 ? actualTotal / actualCount : 0;

            v.put("storedAvgScore", expectedAvg);
            v.put("recalculatedAvgScore", actualAvg);
            v.put("avgScoreMatch", Math.abs(expectedAvg - actualAvg) < 0.001);

            verification.add(v);
        }

        result.put("verification", verification);

        boolean allCountsMatch = verification.stream()
                .allMatch(v -> (Boolean) v.get("countMatch"));
        boolean allScoresMatch = verification.stream()
                .allMatch(v -> (Boolean) v.get("avgScoreMatch"));

        List<String> invalidReceipts = new ArrayList<>();
        for (VoteReceipt receipt : receipts) {
            if (receipt.getBlockHeight() != null) {
                boolean valid = blockchainService.verifyReceipt(receipt.getRecordHash());
                if (!valid) {
                    invalidReceipts.add(receipt.getRecordHash());
                }
            }
        }

        result.put("allCountsMatch", allCountsMatch);
        result.put("allScoresMatch", allScoresMatch);
        result.put("invalidReceipts", invalidReceipts);
        result.put("blockchainValid", blockchainService.verifyBlockchainIntegrity());
        result.put("overallValid", allCountsMatch && allScoresMatch && invalidReceipts.isEmpty());

        result.put("resultHash", CryptoUtil.sha256(JSON.toJSONString(result)));

        return result;
    }

    public Map<String, Object> verifyVoteResult(VoteResultDTO expectedResult) {
        Map<String, Object> verificationData = generateVerificationData(expectedResult.getVoteId());

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("expectedResult", expectedResult);
        result.put("verificationData", verificationData);

        List<Map<String, Object>> verification = (List<Map<String, Object>>) verificationData.get("verification");

        boolean overallMatch = true;
        List<Map<String, Object>> mismatches = new ArrayList<>();

        for (VoteResultDTO.OptionResult expectedOption : expectedResult.getOptions()) {
            Optional<Map<String, Object>> actualOpt = verification.stream()
                    .filter(v -> v.get("optionId").equals(expectedOption.getOptionId()))
                    .findFirst();

            if (actualOpt.isPresent()) {
                Map<String, Object> actual = actualOpt.get();
                long actualCount = ((Number) actual.get("recalculatedCount")).longValue();
                double actualPercentage = (double) actualCount / expectedResult.getTotalVotes() * 100;

                boolean countMatch = expectedOption.getVoteCount().equals(actualCount);
                boolean percentageMatch = Math.abs(expectedOption.getPercentage() - actualPercentage) < 0.01;

                if (!countMatch || !percentageMatch) {
                    overallMatch = false;
                    Map<String, Object> mismatch = new LinkedHashMap<>();
                    mismatch.put("optionId", expectedOption.getOptionId());
                    mismatch.put("optionContent", expectedOption.getContent());
                    mismatch.put("expectedCount", expectedOption.getVoteCount());
                    mismatch.put("actualCount", actualCount);
                    mismatch.put("expectedPercentage", expectedOption.getPercentage());
                    mismatch.put("actualPercentage", actualPercentage);
                    mismatches.add(mismatch);
                }
            } else {
                overallMatch = false;
                Map<String, Object> mismatch = new LinkedHashMap<>();
                mismatch.put("optionId", expectedOption.getOptionId());
                mismatch.put("optionContent", expectedOption.getContent());
                mismatch.put("error", "Option not found in verification data");
                mismatches.add(mismatch);
            }
        }

        result.put("overallMatch", overallMatch);
        result.put("mismatches", mismatches);
        result.put("blockchainValid", verificationData.get("blockchainValid"));
        result.put("allReceiptsValid", ((List<String>) verificationData.get("invalidReceipts")).isEmpty());

        return result;
    }

    public boolean verifyReceiptInclusion(String recordHash) {
        return blockchainService.verifyReceipt(recordHash);
    }

    public Map<String, Object> getBlockchainInfo() {
        Map<String, Object> info = new LinkedHashMap<>();

        Block latest = blockchainService.getLatestBlock();
        if (latest != null) {
            info.put("latestBlockHeight", latest.getBlockHeight());
            info.put("latestBlockHash", latest.getHash());
            info.put("latestBlockTime", latest.getCreatedAt());
            info.put("latestBlockTransactions", latest.getVoteCount());
        } else {
            info.put("latestBlockHeight", null);
        }

        info.put("blockchainValid", blockchainService.verifyBlockchainIntegrity());

        return info;
    }
}
