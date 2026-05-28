package com.voting.service;

import com.voting.dto.VoteResultDTO;
import com.voting.entity.Vote;
import com.voting.entity.VoteRecord;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.io.ByteArrayOutputStream;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.time.format.DateTimeFormatter;
import java.util.List;

@Service
public class ExportService {

    @Autowired
    private VoteService voteService;

    public byte[] exportVoteResultToCSV(Long voteId) {
        VoteResultDTO result = voteService.getVoteResult(voteId);
        Vote vote = voteService.getVoteById(voteId)
                .orElseThrow(() -> new IllegalArgumentException("投票不存在"));

        try (ByteArrayOutputStream baos = new ByteArrayOutputStream();
             PrintWriter writer = new PrintWriter(new OutputStreamWriter(baos, StandardCharsets.UTF_8))) {

            writer.println('\ufeff' + "投票ID," + result.getVoteId());
            writer.println("投票标题," + result.getTitle());
            writer.println("投票类型," + result.getType());
            writer.println("总投票数," + result.getTotalVotes());
            writer.println("创建时间," + vote.getCreatedAt().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
            writer.println();

            if ("RATING".equalsIgnoreCase(result.getType())) {
                writer.println("选项ID,选项内容,投票数,平均得分,占比(%)");
                for (VoteResultDTO.OptionResult option : result.getOptions()) {
                    writer.printf("%d,%s,%d,%.2f,%.2f%n",
                            option.getOptionId(),
                            escapeCSV(option.getContent()),
                            option.getVoteCount(),
                            option.getAvgScore() != null ? option.getAvgScore() : 0,
                            option.getPercentage() != null ? option.getPercentage() : 0);
                }
            } else {
                writer.println("选项ID,选项内容,投票数,占比(%)");
                for (VoteResultDTO.OptionResult option : result.getOptions()) {
                    writer.printf("%d,%s,%d,%.2f%n",
                            option.getOptionId(),
                            escapeCSV(option.getContent()),
                            option.getVoteCount(),
                            option.getPercentage() != null ? option.getPercentage() : 0);
                }
            }

            writer.flush();
            return baos.toByteArray();
        } catch (Exception e) {
            throw new RuntimeException("导出CSV失败", e);
        }
    }

    public byte[] exportVoteRecordsToCSV(Long voteId) {
        List<VoteRecord> records = voteService.getVoteRecords(voteId);
        Vote vote = voteService.getVoteById(voteId)
                .orElseThrow(() -> new IllegalArgumentException("投票不存在"));

        try (ByteArrayOutputStream baos = new ByteArrayOutputStream();
             PrintWriter writer = new PrintWriter(new OutputStreamWriter(baos, StandardCharsets.UTF_8))) {

            writer.println('\ufeff' + "投票ID," + voteId);
            writer.println("投票标题," + vote.getTitle());
            writer.println("记录总数," + records.size());
            writer.println();

            writer.println("记录ID,选项ID,评分,IP地址(脱敏),设备指纹(哈希),投票时间");
            DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

            for (VoteRecord record : records) {
                writer.printf("%d,%s,%s,%s,%s,%s%n",
                        record.getId(),
                        record.getOptionId() != null ? record.getOptionId().toString() : "",
                        record.getVoteScore() != null ? record.getVoteScore().toString() : "",
                        maskIp(record.getIpAddress()),
                        record.getDeviceFingerprint() != null ? hashTruncate(record.getDeviceFingerprint()) : "",
                        record.getCreatedAt().format(formatter));
            }

            writer.flush();
            return baos.toByteArray();
        } catch (Exception e) {
            throw new RuntimeException("导出CSV失败", e);
        }
    }

    private String escapeCSV(String value) {
        if (value == null) {
            return "";
        }
        if (value.contains(",") || value.contains("\"") || value.contains("\n")) {
            return "\"" + value.replace("\"", "\"\"") + "\"";
        }
        return value;
    }

    private String maskIp(String ip) {
        if (ip == null || ip.isEmpty()) {
            return "";
        }
        if (ip.contains(":")) {
            return ip.substring(0, Math.min(5, ip.length())) + ":***";
        }
        String[] parts = ip.split("\\.");
        if (parts.length >= 2) {
            return parts[0] + "." + parts[1] + ".***.***";
        }
        return "***.***.***.***";
    }

    private String hashTruncate(String hash) {
        if (hash == null || hash.length() < 8) {
            return hash;
        }
        return hash.substring(0, 8) + "***";
    }
}
