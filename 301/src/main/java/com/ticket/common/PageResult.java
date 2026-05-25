package com.ticket.common;

import lombok.Data;
import org.springframework.data.domain.Page;

import java.util.List;

@Data
public class PageResult<T> {

    private List<T> list;
    private Long total;
    private Integer pageNum;
    private Integer pageSize;
    private Integer pages;

    public static <T> PageResult<T> of(Page<T> page) {
        PageResult<T> result = new PageResult<>();
        result.setList(page.getContent());
        result.setTotal(page.getTotalElements());
        result.setPageNum(page.getNumber() + 1);
        result.setPageSize(page.getSize());
        result.setPages(page.getTotalPages());
        return result;
    }

    public static <T, E> PageResult<T> of(Page<E> page, List<T> content) {
        PageResult<T> result = new PageResult<>();
        result.setList(content);
        result.setTotal(page.getTotalElements());
        result.setPageNum(page.getNumber() + 1);
        result.setPageSize(page.getSize());
        result.setPages(page.getTotalPages());
        return result;
    }
}
