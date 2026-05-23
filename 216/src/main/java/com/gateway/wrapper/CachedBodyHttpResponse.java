package com.gateway.wrapper;

import org.reactivestreams.Publisher;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.core.io.buffer.DataBufferFactory;
import org.springframework.core.io.buffer.DataBufferUtils;
import org.springframework.http.HttpHeaders;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.http.server.reactive.ServerHttpResponseDecorator;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

public class CachedBodyHttpResponse extends ServerHttpResponseDecorator {

    private final List<DataBuffer> cachedBuffers = new ArrayList<>();
    private byte[] cachedBody;

    public CachedBodyHttpResponse(ServerHttpResponse delegate) {
        super(delegate);
    }

    @Override
    public Mono<Void> writeWith(Publisher<? extends DataBuffer> body) {
        if (body instanceof Flux<? extends DataBuffer> fluxBody) {
            return super.writeWith(fluxBody.buffer().map(dataBuffers -> {
                DataBufferFactory bufferFactory = bufferFactory();
                DataBuffer joinedBuffer = bufferFactory.join(dataBuffers);
                byte[] content = new byte[joinedBuffer.readableByteCount()];
                joinedBuffer.read(content);
                DataBufferUtils.release(joinedBuffer);
                cachedBody = content;
                return bufferFactory.wrap(content);
            }));
        } else if (body instanceof Mono<? extends DataBuffer> monoBody) {
            return super.writeWith(monoBody.map(dataBuffer -> {
                byte[] content = new byte[dataBuffer.readableByteCount()];
                dataBuffer.read(content);
                DataBufferUtils.release(dataBuffer);
                cachedBody = content;
                return bufferFactory().wrap(content);
            }));
        }
        return super.writeWith(body);
    }

    @Override
    public Mono<Void> writeAndFlushWith(Publisher<? extends Publisher<? extends DataBuffer>> body) {
        return writeWith(Flux.from(body).flatMapSequential(p -> p));
    }

    public String getCachedBody() {
        if (cachedBody == null || cachedBody.length == 0) {
            return "";
        }
        return new String(cachedBody, StandardCharsets.UTF_8);
    }

    public byte[] getCachedBodyBytes() {
        return cachedBody;
    }

    @Override
    public HttpHeaders getHeaders() {
        HttpHeaders headers = new HttpHeaders();
        headers.addAll(super.getHeaders());
        if (cachedBody != null && !headers.containsKey(HttpHeaders.CONTENT_LENGTH)) {
            headers.setContentLength(cachedBody.length);
        }
        return headers;
    }
}
