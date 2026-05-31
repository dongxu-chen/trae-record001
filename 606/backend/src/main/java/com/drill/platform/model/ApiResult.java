package com.drill.platform.model;

import lombok.Data;
import java.util.List;

@Data
public class ApiResult<T> {

    private int code;
    private String message;
    private T data;

    public static <T> ApiResult<T> success(T data) {
        ApiResult<T> result = new ApiResult<>();
        result.setCode(200);
        result.setMessage("success");
        result.setData(data);
        return result;
    }

    public static <T> ApiResult<T> error(int code, String message) {
        ApiResult<T> result = new ApiResult<>();
        result.setCode(code);
        result.setMessage(message);
        return result;
    }

    @Data
    public static class PageData<T> {
        private List<T> items;
        private long total;
        private int page;
        private int size;
    }
}
