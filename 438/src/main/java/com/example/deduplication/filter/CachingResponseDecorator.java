package com.example.deduplication.filter;

import org.reactivestreams.Publisher;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.core.io.buffer.DataBufferFactory;
import org.springframework.core.io.buffer.DefaultDataBufferFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.http.server.reactive.ServerHttpResponseDecorator;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class CachingResponseDecorator extends ServerHttpResponseDecorator {

    private final DataBufferFactory bufferFactory = new DefaultDataBufferFactory();
    private final StringBuilder bodyBuilder = new StringBuilder();
    private int statusCode;

    public CachingResponseDecorator(ServerHttpResponse delegate) {
        super(delegate);
    }

    @Override
    public Mono<Void> writeWith(Publisher<? extends DataBuffer> body) {
        Flux<DataBuffer> flux = Flux.from(body);
        return flux.doOnNext(buffer -> {
                    byte[] bytes = new byte[buffer.readableByteCount()];
                    buffer.read(bytes);
                    bodyBuilder.append(new String(bytes, StandardCharsets.UTF_8));
                })
                .map(buffer -> {
                    byte[] bytes = new byte[buffer.readableByteCount()];
                    buffer.read(bytes);
                    DataBuffer newBuffer = bufferFactory.allocateBuffer(bytes.length);
                    newBuffer.write(bytes);
                    return newBuffer;
                })
                .collectList()
                .flatMap(buffers -> super.writeWith(Flux.fromIterable(buffers)));
    }

    @Override
    public Mono<Void> writeAndFlushWith(Publisher<? extends Publisher<? extends DataBuffer>> body) {
        return writeWith(Flux.from(body).flatMapSequential(p -> p));
    }

    public String getCachedBody() {
        return bodyBuilder.toString();
    }

    public Map<String, String> getCachedHeaders() {
        HttpHeaders headers = getHeaders();
        Map<String, String> headerMap = new HashMap<>();
        for (Map.Entry<String, List<String>> entry : headers.entrySet()) {
            headerMap.put(entry.getKey(), String.join(",", entry.getValue()));
        }
        return headerMap;
    }

    public int getCachedStatus() {
        return getStatusCode() != null ? getStatusCode().value() : 200;
    }
}
