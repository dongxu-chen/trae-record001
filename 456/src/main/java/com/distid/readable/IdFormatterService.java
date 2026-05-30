package com.distid.readable;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Slf4j
@Service
public class IdFormatterService {

    private final boolean readableEnabled;
    private final boolean timePrefixEnabled;
    private final boolean base62Enabled;
    private final String dcCode;

    public IdFormatterService(
            @Value("${distid.readable.enabled:true}") boolean readableEnabled,
            @Value("${distid.readable.time-prefix:true}") boolean timePrefixEnabled,
            @Value("${distid.readable.base62:true}") boolean base62Enabled,
            @Value("${distid.readable.dc-code:}") String dcCode) {
        this.readableEnabled = readableEnabled;
        this.timePrefixEnabled = timePrefixEnabled;
        this.base62Enabled = base62Enabled;
        this.dcCode = dcCode;
        log.info("IdFormatterService initialized: readable={}, timePrefix={}, base62={}, dcCode={}",
                readableEnabled, timePrefixEnabled, base62Enabled, dcCode);
    }

    public FormattedId formatSnowflake(long rawId, String bizTag) {
        if (!readableEnabled) {
            return FormattedId.of(rawId, bizTag, dcCode);
        }

        long generatedAt = System.currentTimeMillis();
        String timePrefix = timePrefixEnabled ? TimePrefixFormatter.format(generatedAt) : "";
        String base62 = base62Enabled ? Base62Codec.encodeWithPadding(rawId, 8) : String.valueOf(rawId);

        StringBuilder readable = new StringBuilder();
        if (timePrefixEnabled && !timePrefix.isEmpty()) {
            readable.append(timePrefix);
        }
        if (bizTag != null && !bizTag.isEmpty()) {
            if (readable.length() > 0) readable.append("-");
            readable.append(bizTag.toUpperCase());
        }
        if (dcCode != null && !dcCode.isEmpty()) {
            if (readable.length() > 0) readable.append("-");
            readable.append(dcCode);
        }
        if (readable.length() > 0) readable.append("-");
        readable.append(base62);

        return FormattedId.builder()
                .rawId(rawId)
                .bizTag(bizTag)
                .timePrefix(timePrefix)
                .dcCode(dcCode)
                .readableId(readable.toString())
                .base62Id(base62)
                .generatedAt(generatedAt)
                .build();
    }

    public FormattedId formatSegment(long rawId, String bizTag) {
        return formatSnowflake(rawId, bizTag);
    }
}
