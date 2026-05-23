package com.shortlink.service;

import com.shortlink.common.ErrorCode;
import com.shortlink.dto.BatchCreateResult;
import com.shortlink.dto.CreateShortLinkRequest;
import com.shortlink.entity.ShortLink;
import com.shortlink.exception.BusinessException;
import com.shortlink.repository.ShortLinkRepository;
import com.shortlink.util.Base62Encoder;
import com.shortlink.util.CsvUtil;
import com.shortlink.util.SnowflakeIdGenerator;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;
import java.util.regex.Pattern;

@Slf4j
@Service
@RequiredArgsConstructor
public class ShortLinkService {

    private final ShortLinkRepository shortLinkRepository;
    private final SnowflakeIdGenerator idGenerator;
    private final Base62Encoder base62Encoder;
    private final RedisTemplate<String, Object> redisTemplate;

    @Value("${shortlink.domain:http://localhost:8080}")
    private String domain;

    @Value("${shortlink.redis-expire-seconds:3600}")
    private Long redisExpireSeconds;

    private static final String REDIS_SHORT_LINK_PREFIX = "shortlink:code:";
    private static final String REDIS_UV_PREFIX = "shortlink:uv:";
    private static final Pattern URL_PATTERN = Pattern.compile(
            "^(https?://)?[\\w-]+(\\.[\\w-]+)+[\\w.,@?^=%&:/~+#-]*$",
            Pattern.CASE_INSENSITIVE
    );

    @Transactional
    public String createShortLink(CreateShortLinkRequest request) {
        String shortCode;

        if (request.getCustomCode() != null && !request.getCustomCode().isBlank()) {
            shortCode = request.getCustomCode().trim();
            if (!base62Encoder.isValidShortCode(shortCode)) {
                throw new BusinessException(ErrorCode.INVALID_SHORT_CODE);
            }
            if (shortLinkRepository.existsByShortCode(shortCode)) {
                throw new BusinessException(ErrorCode.SHORT_CODE_ALREADY_EXISTS);
            }
        } else {
            long snowflakeId = idGenerator.nextId();
            shortCode = base62Encoder.generateShortCodeFromSnowflake(snowflakeId);
        }

        ShortLink shortLink = new ShortLink();
        shortLink.setOriginUrl(request.getOriginUrl());
        shortLink.setShortCode(shortCode);
        shortLink.setDescription(request.getDescription());
        shortLink.setEnabled(true);
        shortLink.setPvCount(0L);
        shortLink.setUvCount(0L);

        if (request.getExpireDays() != null && request.getExpireDays() > 0) {
            shortLink.setExpireTime(LocalDateTime.now().plusDays(request.getExpireDays()));
        }

        shortLinkRepository.save(shortLink);

        String cacheKey = REDIS_SHORT_LINK_PREFIX + shortCode;
        redisTemplate.opsForValue().set(cacheKey, request.getOriginUrl(), redisExpireSeconds, TimeUnit.SECONDS);

        return domain + "/" + shortCode;
    }

    @Transactional
    public BatchCreateResult batchCreateShortLink(MultipartFile file) throws IOException {
        List<CsvUtil.CsvRow> rows = CsvUtil.parseCsv(file);
        BatchCreateResult result = new BatchCreateResult();
        result.setTotalCount(rows.size());

        List<ShortLink> batchSaveList = new ArrayList<>();

        for (CsvUtil.CsvRow row : rows) {
            String originUrl = row.getOriginUrl();

            if (StringUtils.isBlank(originUrl)) {
                result.getFailList().add(new BatchCreateResult.FailRecord(
                        originUrl, row.getCustomCode(), "URL不能为空", row.getLineNumber()
                ));
                continue;
            }

            if (!isValidUrl(originUrl)) {
                result.getFailList().add(new BatchCreateResult.FailRecord(
                        originUrl, row.getCustomCode(), "URL格式不正确", row.getLineNumber()
                ));
                continue;
            }

            String shortCode;
            String customCode = row.getCustomCode();

            try {
                if (StringUtils.isNotBlank(customCode)) {
                    if (!base62Encoder.isValidShortCode(customCode)) {
                        result.getFailList().add(new BatchCreateResult.FailRecord(
                                originUrl, customCode, "自定义短码格式不正确", row.getLineNumber()
                        ));
                        continue;
                    }
                    if (shortLinkRepository.existsByShortCode(customCode)) {
                        result.getFailList().add(new BatchCreateResult.FailRecord(
                                originUrl, customCode, "自定义短码已存在", row.getLineNumber()
                        ));
                        continue;
                    }
                    shortCode = customCode;
                } else {
                    long snowflakeId = idGenerator.nextId();
                    shortCode = base62Encoder.generateShortCodeFromSnowflake(snowflakeId);
                }

                ShortLink shortLink = new ShortLink();
                shortLink.setOriginUrl(originUrl);
                shortLink.setShortCode(shortCode);
                shortLink.setDescription(row.getDescription());
                shortLink.setEnabled(true);
                shortLink.setPvCount(0L);
                shortLink.setUvCount(0L);

                if (row.getExpireDays() != null && row.getExpireDays() > 0) {
                    shortLink.setExpireTime(LocalDateTime.now().plusDays(row.getExpireDays()));
                }

                batchSaveList.add(shortLink);

                String shortUrl = domain + "/" + shortCode;
                result.getSuccessList().add(new BatchCreateResult.ShortLinkMapping(
                        originUrl, shortCode, shortUrl, row.getDescription()
                ));

                String cacheKey = REDIS_SHORT_LINK_PREFIX + shortCode;
                redisTemplate.opsForValue().set(cacheKey, originUrl, redisExpireSeconds, TimeUnit.SECONDS);

            } catch (Exception e) {
                log.error("批量创建短链接失败: {}, error: {}", originUrl, e.getMessage());
                result.getFailList().add(new BatchCreateResult.FailRecord(
                        originUrl, customCode, "创建失败: " + e.getMessage(), row.getLineNumber()
                ));
            }
        }

        if (!batchSaveList.isEmpty()) {
            shortLinkRepository.saveAll(batchSaveList);
        }

        result.setSuccessCount(result.getSuccessList().size());
        result.setFailCount(result.getFailList().size());

        return result;
    }

    private boolean isValidUrl(String url) {
        if (StringUtils.isBlank(url)) {
            return false;
        }
        return URL_PATTERN.matcher(url).matches();
    }

    public byte[] generateMappingCsv(List<BatchCreateResult.ShortLinkMapping> mappings) throws IOException {
        return CsvUtil.generateMappingCsv(mappings);
    }

    public String getOriginUrl(String shortCode) {
        String cacheKey = REDIS_SHORT_LINK_PREFIX + shortCode;
        String cachedUrl = (String) redisTemplate.opsForValue().get(cacheKey);

        if (cachedUrl != null) {
            return cachedUrl;
        }

        ShortLink shortLink = shortLinkRepository.findByShortCode(shortCode)
                .orElseThrow(() -> new BusinessException(ErrorCode.SHORT_CODE_NOT_FOUND));

        if (!shortLink.getEnabled()) {
            throw new BusinessException(ErrorCode.SHORT_CODE_NOT_FOUND);
        }

        if (shortLink.getExpireTime() != null && shortLink.getExpireTime().isBefore(LocalDateTime.now())) {
            throw new BusinessException(ErrorCode.SHORT_CODE_EXPIRED);
        }

        redisTemplate.opsForValue().set(cacheKey, shortLink.getOriginUrl(), redisExpireSeconds, TimeUnit.SECONDS);

        return shortLink.getOriginUrl();
    }

    public ShortLink getShortLinkInfo(String shortCode) {
        return shortLinkRepository.findByShortCode(shortCode)
                .orElseThrow(() -> new BusinessException(ErrorCode.SHORT_CODE_NOT_FOUND));
    }

    @Transactional
    public void incrementPv(String shortCode) {
        shortLinkRepository.incrementPvCount(shortCode);
    }

    @Transactional
    public void incrementUv(String shortCode) {
        shortLinkRepository.incrementUvCount(shortCode);
    }

    public boolean isFirstVisitByFingerprint(String shortCode, String fingerprint) {
        String key = REDIS_UV_PREFIX + shortCode + ":" + fingerprint;
        Boolean isNew = redisTemplate.opsForValue().setIfAbsent(key, "1", 24, TimeUnit.HOURS);
        return Boolean.TRUE.equals(isNew);
    }

    @Transactional
    public int deleteExpiredLinks() {
        return shortLinkRepository.deleteExpiredLinks(LocalDateTime.now());
    }
}
