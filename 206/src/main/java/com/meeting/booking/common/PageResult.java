package com.meeting.booking.common;

import lombok.Data;

import java.util.List;

@Data
public class PageResult<T> {
    private List<T> list;
    private Integer pageNum;
    private Integer pageSize;
    private Long total;
    private Integer pages;

    public static <T> PageResult<T> of(List<T> list, Integer pageNum, Integer pageSize, Long total) {
        PageResult<T> result = new PageResult<>();
        result.setList(list);
        result.setPageNum(pageNum);
        result.setPageSize(pageSize);
        result.setTotal(total);
        result.setPages((int) Math.ceil((double) total / pageSize));
        return result;
    }
}
