package com.example.deduplication.filter;

import com.example.deduplication.util.DataBufferUtils;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.core.io.buffer.DataBufferFactory;
import org.springframework.core.io.buffer.DefaultDataBufferFactory;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpRequestDecorator;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;

public class CachingBodyDecorator extends ServerHttpRequestDecorator {

    private final DataBufferFactory bufferFactory = new DefaultDataBufferFactory();
    private final Mono<String> cachedBody;

    public CachingBodyDecorator(ServerHttpRequest delegate) {
        super(delegate);
        this.cachedBody = cacheBody(delegate);
    }

    private Mono<String> cacheBody(ServerHttpRequest request) {
        return DataBufferUtils.join(request.getBody())
                .map(dataBuffer -> {
                    byte[] bytes = new byte[dataBuffer.readableByteCount()];
                    dataBuffer.read(bytes);
                    DataBufferUtils.release(dataBuffer);
                    return new String(bytes, StandardCharsets.UTF_8);
                })
                .defaultIfEmpty("");
    }

    public Mono<String> getCachedBody() {
        return cachedBody;
    }

    @Override
    public Flux<DataBuffer> getBody() {
        return cachedBody.flatMapMany(body -> {
            byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
            DataBuffer buffer = bufferFactory.allocateBuffer(bytes.length);
            buffer.write(bytes);
            return Flux.just(buffer);
        });
    }
}
