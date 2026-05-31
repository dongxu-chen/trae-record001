package com.dlq.platform.api.common;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PageResult<T> implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long total;

    private Integer pageNum;

    private Integer pageSize;

    private Integer pages;

    private List<T> list;

    public static <T> PageResult<T> of(Long total, Integer pageNum, Integer pageSize, List<T> list) {
        int pages = (int) Math.ceil((double) total / pageSize);
        return PageResult.<T>builder()
                .total(total)
                .pageNum(pageNum)
                .pageSize(pageSize)
                .pages(pages)
                .list(list)
                .build();
    }

    public static <T> PageResult<T> empty(Integer pageNum, Integer pageSize) {
        return PageResult.<T>builder()
                .total(0L)
                .pageNum(pageNum)
                .pageSize(pageSize)
                .pages(0)
                .list(List.of())
                .build();
    }
}
