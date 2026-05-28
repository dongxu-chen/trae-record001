package com.voting.service;

import com.voting.dto.CreateVoteRequest;
import com.voting.dto.SubmitVoteRequest;
import com.voting.dto.VoteResultDTO;
import com.voting.entity.Vote;
import com.voting.entity.VoteOption;
import com.voting.entity.VoteRecord;
import com.voting.repository.VoteOptionRepository;
import com.voting.repository.VoteRecordRepository;
import com.voting.repository.VoteRepository;
import com.voting.util.CryptoUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

@Service
public class VoteService {

    @Autowired
    private VoteRepository voteRepository;

    @Autowired
    private VoteOptionRepository voteOptionRepository;

    @Autowired
    private VoteRecordRepository voteRecordRepository;

    @Autowired
    private AntiFraudService antiFraudService;

    @Autowired
    private VoteCodeService voteCodeService;

    @Autowired
    private SimpMessagingTemplate messagingTemplate;

    @Autowired
    private BlockchainService blockchainService;

    @Autowired
    private AnonymousCredentialService credentialService;

    @Transactional
    public Vote createVote(CreateVoteRequest request) {
        Vote vote = new Vote();
        vote.setTitle(request.getTitle());
        vote.setDescription(request.getDescription());
        vote.setType(request.getType());
        vote.setMinSelect(request.getMinSelect());
        vote.setMaxSelect(request.getMaxSelect());
        vote.setMinScore(request.getMinScore());
        vote.setMaxScore(request.getMaxScore());
        vote.setRequireVoteCode(request.getRequireVoteCode());
        vote.setAllowAnonymous(request.getAllowAnonymous());
        vote.setStartTime(request.getStartTime());
        vote.setEndTime(request.getEndTime());
        vote.setCreatedBy(request.getCreatedBy());

        vote = voteRepository.save(vote);

        List<String> optionContents = request.getOptions();
        for (int i = 0; i < optionContents.size(); i++) {
            VoteOption option = new VoteOption();
            option.setVote(vote);
            option.setContent(optionContents.get(i));
            option.setSortOrder(i);
            voteOptionRepository.save(option);
        }

        return vote;
    }

    public Optional<Vote> getVoteById(Long id) {
        return voteRepository.findByIdAndActiveTrue(id);
    }

    public List<Vote> getAllVotes() {
        return voteRepository.findByActiveTrueOrderByCreatedAtDesc();
    }

    @Transactional
    public boolean submitVote(SubmitVoteRequest request, String ipAddress, String deviceFingerprint) {
        Optional<Vote> voteOpt = voteRepository.findByIdAndActiveTrue(request.getVoteId());
        if (voteOpt.isEmpty()) {
            throw new IllegalArgumentException("投票不存在或已关闭");
        }

        Vote vote = voteOpt.get();

        if (!isVoteActive(vote)) {
            throw new IllegalArgumentException("投票未开始或已结束");
        }

        if (request.getAnonymousProof() != null && !request.getAnonymousProof().isEmpty()) {
            if (!credentialService.verifyCredential(request.getAnonymousProof(), vote.getId())) {
                throw new IllegalArgumentException("无效的匿名凭证");
            }
            String nullifier = credentialService.extractNullifier(request.getAnonymousProof());
            if (credentialService.isNullifierUsed(nullifier)) {
                throw new IllegalArgumentException("该匿名凭证已被使用");
            }
        }

        if (vote.getRequireVoteCode()) {
            if (request.getVoteCode() == null || request.getVoteCode().isEmpty()) {
                throw new IllegalArgumentException("需要投票码才能参与投票");
            }
            if (!voteCodeService.validateVoteCode(vote.getId(), request.getVoteCode())) {
                throw new IllegalArgumentException("无效或已使用的投票码");
            }
        }

        if (!antiFraudService.canVote(vote.getId(), ipAddress,
                request.getDeviceFingerprint() != null ? request.getDeviceFingerprint() : deviceFingerprint)) {
            throw new IllegalArgumentException("您已参与过此投票或操作过于频繁");
        }

        String finalFingerprint = request.getDeviceFingerprint() != null ?
                request.getDeviceFingerprint() : deviceFingerprint;

        List<VoteRecord> records = processVote(vote, request, ipAddress, finalFingerprint);

        if (request.getAnonymousProof() != null && !request.getAnonymousProof().isEmpty()) {
            credentialService.useCredential(request.getAnonymousProof(), vote.getId());
        }

        if (vote.getRequireVoteCode()) {
            voteCodeService.useVoteCode(vote.getId(), request.getVoteCode());
        }

        antiFraudService.recordVote(vote.getId(), ipAddress, finalFingerprint);

        String commitment = null;
        String nullifier = null;
        if (request.getAnonymousProof() != null && !request.getAnonymousProof().isEmpty()) {
            commitment = credentialService.extractCommitment(request.getAnonymousProof());
            nullifier = credentialService.extractNullifier(request.getAnonymousProof());
        }

        for (VoteRecord record : records) {
            blockchainService.createVoteReceipt(record, commitment, nullifier);
        }

        sendVoteResultUpdate(vote.getId());

        return true;
    }

    private List<VoteRecord> processVote(Vote vote, SubmitVoteRequest request, String ipAddress, String deviceFingerprint) {
        String voteCodeHash = voteCodeService.getCodeHash(request.getVoteCode());

        switch (vote.getType().toUpperCase()) {
            case "SINGLE":
                return processSingleVote(vote, request, ipAddress, deviceFingerprint, voteCodeHash);
            case "MULTIPLE":
                return processMultipleVote(vote, request, ipAddress, deviceFingerprint, voteCodeHash);
            case "RATING":
                return processRatingVote(vote, request, ipAddress, deviceFingerprint, voteCodeHash);
            default:
                throw new IllegalArgumentException("不支持的投票类型");
        }
    }

    private List<VoteRecord> processSingleVote(Vote vote, SubmitVoteRequest request, String ipAddress,
                                                String deviceFingerprint, String voteCodeHash) {
        if (request.getOptionId() == null) {
            throw new IllegalArgumentException("请选择一个选项");
        }

        voteOptionRepository.incrementVoteCount(request.getOptionId());

        VoteRecord record = new VoteRecord();
        record.setVoteId(vote.getId());
        record.setOptionId(request.getOptionId());
        record.setDeviceFingerprint(deviceFingerprint);
        record.setIpAddress(ipAddress);
        record.setVoteCodeHash(voteCodeHash);
        record = voteRecordRepository.save(record);

        List<VoteRecord> records = new ArrayList<>();
        records.add(record);
        return records;
    }

    private List<VoteRecord> processMultipleVote(Vote vote, SubmitVoteRequest request, String ipAddress,
                                                  String deviceFingerprint, String voteCodeHash) {
        if (request.getOptionIds() == null || request.getOptionIds().isEmpty()) {
            throw new IllegalArgumentException("请至少选择一个选项");
        }

        if (request.getOptionIds().size() < vote.getMinSelect()) {
            throw new IllegalArgumentException("至少需要选择 " + vote.getMinSelect() + " 个选项");
        }

        if (request.getOptionIds().size() > vote.getMaxSelect()) {
            throw new IllegalArgumentException("最多只能选择 " + vote.getMaxSelect() + " 个选项");
        }

        List<VoteRecord> records = new ArrayList<>();
        for (Long optionId : request.getOptionIds()) {
            voteOptionRepository.incrementVoteCount(optionId);

            VoteRecord record = new VoteRecord();
            record.setVoteId(vote.getId());
            record.setOptionId(optionId);
            record.setDeviceFingerprint(deviceFingerprint);
            record.setIpAddress(ipAddress);
            record.setVoteCodeHash(voteCodeHash);
            record = voteRecordRepository.save(record);
            records.add(record);
        }
        return records;
    }

    private List<VoteRecord> processRatingVote(Vote vote, SubmitVoteRequest request, String ipAddress,
                                                String deviceFingerprint, String voteCodeHash) {
        if (request.getOptionId() == null) {
            throw new IllegalArgumentException("请选择评分项目");
        }

        if (request.getScore() == null) {
            throw new IllegalArgumentException("请提供评分");
        }

        if (request.getScore() < vote.getMinScore() || request.getScore() > vote.getMaxScore()) {
            throw new IllegalArgumentException("评分必须在 " + vote.getMinScore() + " 到 " + vote.getMaxScore() + " 之间");
        }

        voteOptionRepository.incrementVoteCountWithScore(request.getOptionId(), request.getScore());

        VoteRecord record = new VoteRecord();
        record.setVoteId(vote.getId());
        record.setOptionId(request.getOptionId());
        record.setVoteScore(request.getScore());
        record.setDeviceFingerprint(deviceFingerprint);
        record.setIpAddress(ipAddress);
        record.setVoteCodeHash(voteCodeHash);
        record = voteRecordRepository.save(record);

        List<VoteRecord> records = new ArrayList<>();
        records.add(record);
        return records;
    }

    private boolean isVoteActive(Vote vote) {
        LocalDateTime now = LocalDateTime.now();
        if (vote.getStartTime() != null && now.isBefore(vote.getStartTime())) {
            return false;
        }
        if (vote.getEndTime() != null && now.isAfter(vote.getEndTime())) {
            return false;
        }
        return vote.getActive();
    }

    public VoteResultDTO getVoteResult(Long voteId) {
        Optional<Vote> voteOpt = voteRepository.findByIdAndActiveTrue(voteId);
        if (voteOpt.isEmpty()) {
            throw new IllegalArgumentException("投票不存在");
        }

        Vote vote = voteOpt.get();
        List<VoteOption> options = voteOptionRepository.findByVoteIdOrderBySortOrderAsc(voteId);

        VoteResultDTO result = new VoteResultDTO();
        result.setVoteId(vote.getId());
        result.setTitle(vote.getTitle());
        result.setType(vote.getType());

        long totalVotes = options.stream()
                .mapToLong(VoteOption::getVoteCount)
                .sum();
        result.setTotalVotes(totalVotes);

        List<VoteResultDTO.OptionResult> optionResults = options.stream()
                .map(option -> {
                    VoteResultDTO.OptionResult or = new VoteResultDTO.OptionResult();
                    or.setOptionId(option.getId());
                    or.setContent(option.getContent());
                    or.setVoteCount(option.getVoteCount());
                    if (totalVotes > 0) {
                        or.setPercentage((double) option.getVoteCount() / totalVotes * 100);
                    } else {
                        or.setPercentage(0.0);
                    }
                    or.setAvgScore(option.getAvgScore());
                    return or;
                })
                .collect(Collectors.toList());

        result.setOptions(optionResults);

        return result;
    }

    private void sendVoteResultUpdate(Long voteId) {
        try {
            VoteResultDTO result = getVoteResult(voteId);
            messagingTemplate.convertAndSend("/topic/vote-result/" + voteId, result);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public List<VoteRecord> getVoteRecords(Long voteId) {
        return voteRecordRepository.findByVoteId(voteId);
    }
}
