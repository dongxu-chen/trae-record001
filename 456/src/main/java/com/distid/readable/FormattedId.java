package com.distid.readable;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class FormattedId {

    private final long rawId;
    private final String bizTag;
    private final String timePrefix;
    private final String dcCode;
    private final String readableId;
    private final String base62Id;
    private final long generatedAt;

    public static FormattedId of(long rawId, String bizTag, String dcCode) {
        long generatedAt = System.currentTimeMillis();
        String timePrefix = TimePrefixFormatter.format(generatedAt);
        String base62Id = Base62Codec.encodeWithPadding(rawId, 8);

        StringBuilder readable = new StringBuilder();
        readable.append(timePrefix);
        if (bizTag != null && !bizTag.isEmpty()) {
            readable.append("-").append(bizTag.toUpperCase());
        }
        if (dcCode != null && !dcCode.isEmpty()) {
            readable.append("-").append(dcCode);
        }
        readable.append("-").append(base62Id);

        return FormattedId.builder()
                .rawId(rawId)
                .bizTag(bizTag)
                .timePrefix(timePrefix)
                .dcCode(dcCode)
                .readableId(readable.toString())
                .base62Id(base62Id)
                .generatedAt(generatedAt)
                .build();
    }
}
