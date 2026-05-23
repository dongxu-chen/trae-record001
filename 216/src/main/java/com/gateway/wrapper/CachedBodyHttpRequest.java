package com.gateway.wrapper;

import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.core.io.buffer.DataBufferUtils;
import org.springframework.http.HttpHeaders;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpRequestDecorator;
import reactor.core.publisher.Flux;

import java.nio.charset.StandardCharsets;

public class CachedBodyHttpRequest extends ServerHttpRequestDecorator {

    private final byte[] cachedBody;

    public CachedBodyHttpRequest(ServerHttpRequest delegate, byte[] cachedBody) {
        super(delegate);
        this.cachedBody = cachedBody;
    }

    @Override
    public Flux<DataBuffer> getBody() {
        if (cachedBody == null || cachedBody.length == 0) {
            return super.getBody();
        }
        DataBuffer buffer = getDelegate().bufferFactory().wrap(cachedBody);
        return Flux.just(buffer);
    }

    public String getCachedBody() {
        if (cachedBody == null || cachedBody.length == 0) {
            return "";
        }
        return new String(cachedBody, StandardCharsets.UTF_8);
    }

    public static byte[] toByteArray(DataBuffer dataBuffer) {
        byte[] bytes = new byte[dataBuffer.readableByteCount()];
        dataBuffer.read(bytes);
        DataBufferUtils.release(dataBuffer);
        return bytes;
    }

    @Override
    public HttpHeaders getHeaders() {
        HttpHeaders headers = new HttpHeaders();
        headers.addAll(super.getHeaders());
        if (cachedBody != null && cachedBody.length > 0) {
            headers.setContentLength(cachedBody.length);
        }
        return headers;
    }
}
