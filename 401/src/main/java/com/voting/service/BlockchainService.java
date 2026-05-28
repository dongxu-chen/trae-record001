package com.voting.service;

import com.alibaba.fastjson.JSON;
import com.voting.entity.Block;
import com.voting.entity.VoteReceipt;
import com.voting.entity.VoteRecord;
import com.voting.repository.BlockRepository;
import com.voting.repository.VoteReceiptRepository;
import com.voting.util.CryptoUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Service
public class BlockchainService {

    @Autowired
    private BlockRepository blockRepository;

    @Autowired
    private VoteReceiptRepository voteReceiptRepository;

    private static final int BLOCK_SIZE = 10;
    private static final String GENESIS_PREV_HASH = "0000000000000000000000000000000000000000000000000000000000000000";

    @Transactional
    public VoteReceipt createVoteReceipt(VoteRecord record, String commitment, String nullifier) {
        String recordHash = generateRecordHash(record);

        VoteReceipt receipt = new VoteReceipt();
        receipt.setVoteId(record.getVoteId());
        receipt.setRecordHash(recordHash);
        receipt.setCommitment(commitment);
        receipt.setNullifier(nullifier);

        return voteReceiptRepository.save(receipt);
    }

    private String generateRecordHash(VoteRecord record) {
        StringBuilder sb = new StringBuilder();
        sb.append(record.getVoteId()).append("|");
        sb.append(record.getOptionId() != null ? record.getOptionId() : "").append("|");
        sb.append(record.getVoteScore() != null ? record.getVoteScore() : "").append("|");
        sb.append(record.getDeviceFingerprint() != null ? record.getDeviceFingerprint() : "").append("|");
        sb.append(record.getIpAddress() != null ? record.getIpAddress() : "").append("|");
        sb.append(record.getVoteCodeHash() != null ? record.getVoteCodeHash() : "").append("|");
        sb.append(record.getCreatedAt() != null ? record.getCreatedAt().toString() : "");

        return CryptoUtil.doubleSha256(sb.toString());
    }

    @Scheduled(fixedDelay = 5000)
    @Transactional
    public void mineBlock() {
        List<VoteReceipt> pendingReceipts = voteReceiptRepository.findByBlockHeightIsNull();

        if (pendingReceipts.isEmpty()) {
            return;
        }

        int count = Math.min(pendingReceipts.size(), BLOCK_SIZE);
        List<VoteReceipt> batch = pendingReceipts.subList(0, count);

        List<String> hashes = new ArrayList<>();
        for (VoteReceipt receipt : batch) {
            hashes.add(receipt.getRecordHash());
        }

        String merkleRoot = CryptoUtil.computeMerkleRoot(hashes);

        Long currentHeight = blockRepository.getMaxBlockHeight();
        Long newHeight = currentHeight == null ? 0 : currentHeight + 1;

        String previousHash = currentHeight == null
                ? GENESIS_PREV_HASH
                : blockRepository.findByBlockHeight(currentHeight).get().getHash();

        Block block = new Block();
        block.setBlockHeight(newHeight);
        block.setPreviousHash(previousHash);
        block.setMerkleRoot(merkleRoot);
        block.setVoteCount(batch.size());
        block.setData(JSON.toJSONString(hashes));

        String blockHash = generateBlockHash(block);
        block.setHash(blockHash);

        blockRepository.save(block);

        for (int i = 0; i < batch.size(); i++) {
            VoteReceipt receipt = batch.get(i);
            receipt.setBlockHeight(newHeight);
            String[] proof = CryptoUtil.generateMerkleProof(hashes, i);
            receipt.setMerkleProof(JSON.toJSONString(proof));
            voteReceiptRepository.save(receipt);
        }
    }

    private String generateBlockHash(Block block) {
        StringBuilder sb = new StringBuilder();
        sb.append(block.getBlockHeight()).append("|");
        sb.append(block.getPreviousHash()).append("|");
        sb.append(block.getMerkleRoot()).append("|");
        sb.append(block.getVoteCount()).append("|");
        sb.append(block.getCreatedAt() != null ? block.getCreatedAt().toString() : LocalDateTime.now().toString());

        return CryptoUtil.doubleSha256(sb.toString());
    }

    public Block getLatestBlock() {
        return blockRepository.findTopByOrderByBlockHeightDesc().orElse(null);
    }

    public Block getBlockByHeight(Long height) {
        return blockRepository.findByBlockHeight(height).orElse(null);
    }

    public VoteReceipt getReceiptByHash(String recordHash) {
        return voteReceiptRepository.findByRecordHash(recordHash).orElse(null);
    }

    public boolean verifyReceipt(String recordHash) {
        VoteReceipt receipt = voteReceiptRepository.findByRecordHash(recordHash).orElse(null);
        if (receipt == null || receipt.getBlockHeight() == null) {
            return false;
        }

        Block block = blockRepository.findByBlockHeight(receipt.getBlockHeight()).orElse(null);
        if (block == null) {
            return false;
        }

        try {
            String[] proof = JSON.parseObject(receipt.getMerkleProof(), String[].class);
            List<String> hashes = JSON.parseObject(block.getData(), List.class);
            int index = hashes.indexOf(recordHash);

            if (index < 0) {
                return false;
            }

            return CryptoUtil.verifyMerkleProof(block.getMerkleRoot(), recordHash, proof, index);
        } catch (Exception e) {
            return false;
        }
    }

    public boolean verifyBlockchainIntegrity() {
        List<Block> blocks = blockRepository.findAll();
        if (blocks.isEmpty()) {
            return true;
        }

        for (int i = 1; i < blocks.size(); i++) {
            Block current = blocks.get(i);
            Block previous = blocks.get(i - 1);

            if (!current.getPreviousHash().equals(previous.getHash())) {
                return false;
            }

            String recalculatedHash = generateBlockHash(current);
            if (!recalculatedHash.equals(current.getHash())) {
                return false;
            }
        }

        return true;
    }

    public List<VoteReceipt> getReceiptsByVoteId(Long voteId) {
        return voteReceiptRepository.findByVoteId(voteId);
    }
}
