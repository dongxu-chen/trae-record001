package com.voting.service;

import com.voting.entity.VoteCode;
import com.voting.repository.VoteCodeRepository;
import org.apache.commons.codec.digest.DigestUtils;
import org.apache.commons.lang3.RandomStringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Service
public class VoteCodeService {

    @Autowired
    private VoteCodeRepository voteCodeRepository;

    @Value("${voting.vote-code.length:8}")
    private int codeLength;

    @Value("${voting.vote-code.expire-days:7}")
    private int expireDays;

    @Transactional
    public List<String> generateVoteCodes(Long voteId, int count) {
        return generateVoteCodes(voteId, count, expireDays);
    }

    @Transactional
    public List<String> generateVoteCodes(Long voteId, int count, int customExpireDays) {
        List<String> codes = new ArrayList<>();
        LocalDateTime expireAt = LocalDateTime.now().plusDays(customExpireDays);

        for (int i = 0; i < count; i++) {
            String code = generateUniqueCode();
            String codeHash = DigestUtils.sha256Hex(code);

            VoteCode voteCode = new VoteCode();
            voteCode.setVoteId(voteId);
            voteCode.setCode(code);
            voteCode.setCodeHash(codeHash);
            voteCode.setExpireAt(expireAt);
            voteCodeRepository.save(voteCode);

            codes.add(code);
        }

        return codes;
    }

    private String generateUniqueCode() {
        String code;
        int attempts = 0;
        do {
            code = RandomStringUtils.randomAlphanumeric(codeLength).toUpperCase();
            attempts++;
        } while (voteCodeRepository.findByCode(code).isPresent() && attempts < 100);

        return code;
    }

    public boolean validateVoteCode(Long voteId, String code) {
        if (code == null || code.isEmpty()) {
            return false;
        }

        String codeHash = DigestUtils.sha256Hex(code);
        return voteCodeRepository.findByCodeHash(codeHash)
                .filter(vc -> vc.getVoteId().equals(voteId))
                .filter(vc -> !vc.getUsed())
                .filter(vc -> vc.getExpireAt().isAfter(LocalDateTime.now()))
                .isPresent();
    }

    @Transactional
    public boolean useVoteCode(Long voteId, String code) {
        if (code == null || code.isEmpty()) {
            return false;
        }

        String codeHash = DigestUtils.sha256Hex(code);
        return voteCodeRepository.findByCodeHash(codeHash)
                .filter(vc -> vc.getVoteId().equals(voteId))
                .filter(vc -> !vc.getUsed())
                .filter(vc -> vc.getExpireAt().isAfter(LocalDateTime.now()))
                .map(vc -> {
                    int updated = voteCodeRepository.markAsUsed(vc.getId(), LocalDateTime.now());
                    return updated > 0;
                })
                .orElse(false);
    }

    public String getCodeHash(String code) {
        if (code == null || code.isEmpty()) {
            return null;
        }
        return DigestUtils.sha256Hex(code);
    }

    public List<VoteCode> getVoteCodesByVoteId(Long voteId) {
        return voteCodeRepository.findByVoteId(voteId);
    }

    public long getUsedCodeCount(Long voteId) {
        return voteCodeRepository.countUsedCodesByVoteId(voteId);
    }
}
