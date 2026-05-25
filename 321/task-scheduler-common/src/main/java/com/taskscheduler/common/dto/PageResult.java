package com.taskscheduler.common.dto;

import lombok.Data;

import java.util.List;

@Data
public class PageResult<T> {

    private Long total;
    private Integer pageNum;
    private Integer pageSize;
    private List<T> list;

    public PageResult(Long total, Integer pageNum, Integer pageSize, List<T> list) {
        this.total = total;
        this.pageNum = pageNum;
        this.pageSize = pageSize;
        this.list = list;
    }
}
