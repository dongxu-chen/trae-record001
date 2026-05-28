package com.example.deduplication.util;

import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.core.io.buffer.DefaultDataBufferFactory;
import reactor.core.publisher.Mono;

import java.util.List;

public final class DataBufferUtils {

    private DataBufferUtils() {
    }

    public static Mono<DataBuffer> join(org.reactivestreams.Publisher<DataBuffer> dataBuffers) {
        return reactor.core.publisher.Flux.from(dataBuffers)
                .collectList()
                .map(DataBufferUtils::combineBuffers);
    }

    private static DataBuffer combineBuffers(List<DataBuffer> buffers) {
        if (buffers.isEmpty()) {
            return new DefaultDataBufferFactory().allocateBuffer(0);
        }

        int totalSize = buffers.stream()
                .mapToInt(DataBuffer::readableByteCount)
                .sum();

        DefaultDataBufferFactory factory = new DefaultDataBufferFactory();
        DataBuffer combined = factory.allocateBuffer(totalSize);

        for (DataBuffer buffer : buffers) {
            combined.write(buffer);
            org.springframework.core.io.buffer.DataBufferUtils.release(buffer);
        }

        return combined;
    }

    public static void release(DataBuffer buffer) {
        org.springframework.core.io.buffer.DataBufferUtils.release(buffer);
    }
}
