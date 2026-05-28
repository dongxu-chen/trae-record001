package com.voting.service;

import com.voting.entity.AnonymousCredential;
import com.voting.repository.AnonymousCredentialRepository;
import com.voting.util.CryptoUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Service
public class AnonymousCredentialService {

    @Autowired
    private AnonymousCredentialRepository credentialRepository;

    @Value("${voting.vote-code.expire-days:7}")
    private int defaultExpireDays;

    @Transactional
    public List<String> generateCredentials(Long voteId, int count) {
        return generateCredentials(voteId, count, defaultExpireDays);
    }

    @Transactional
    public List<String> generateCredentials(Long voteId, int count, int expireDays) {
        List<String> credentials = new ArrayList<>();
        LocalDateTime expireAt = LocalDateTime.now().plusDays(expireDays);

        for (int i = 0; i < count; i++) {
            String secret = CryptoUtil.generateRandomString(32);
            String salt = "salt_" + voteId + "_" + System.nanoTime();
            String commitment = CryptoUtil.generateCommitment(secret, salt);
            String nullifier = CryptoUtil.generateNullifier(secret, voteId);
            String publicInput = "vote_" + voteId + "_" + expireAt;
            String zkProof = CryptoUtil.generateZkProof(secret, voteId, publicInput);

            AnonymousCredential credential = new AnonymousCredential();
            credential.setVoteId(voteId);
            credential.setCommitment(commitment);
            credential.setNullifier(nullifier);
            credential.setExpireAt(expireAt);
            credential.setZkProof(zkProof);

            credentialRepository.save(credential);

            credentials.add(secret);
        }

        return credentials;
    }

    public boolean verifyCredential(String zkProof, Long voteId) {
        if (zkProof == null || zkProof.isEmpty()) {
            return false;
        }

        String commitment = CryptoUtil.extractCommitmentFromProof(zkProof);
        if (commitment == null) {
            return false;
        }

        String publicInput = "vote_" + voteId;
        if (!CryptoUtil.verifyZkProof(zkProof, voteId, publicInput)) {
            String alternativePublicInput = "vote_" + voteId + "_" + LocalDateTime.now().plusDays(7).toLocalDate();
            if (!CryptoUtil.verifyZkProof(zkProof, voteId, alternativePublicInput)) {
                return false;
            }
        }

        return credentialRepository.isCommitmentValid(commitment, LocalDateTime.now());
    }

    @Transactional
    public boolean useCredential(String zkProof, Long voteId) {
        if (!verifyCredential(zkProof, voteId)) {
            return false;
        }

        String commitment = CryptoUtil.extractCommitmentFromProof(zkProof);
        int updated = credentialRepository.markAsUsed(commitment, LocalDateTime.now(), LocalDateTime.now());

        return updated > 0;
    }

    public boolean isNullifierUsed(String nullifier) {
        return credentialRepository.isNullifierUsed(nullifier);
    }

    public String extractCommitment(String zkProof) {
        return CryptoUtil.extractCommitmentFromProof(zkProof);
    }

    public String extractNullifier(String zkProof) {
        return CryptoUtil.extractNullifierFromProof(zkProof);
    }

    public String generateZkProof(String secret, Long voteId) {
        String publicInput = "vote_" + voteId;
        return CryptoUtil.generateZkProof(secret, voteId, publicInput);
    }
}
