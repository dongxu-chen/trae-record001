package com.econtract.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.econtract.entity.Contract;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface ContractMapper extends BaseMapper<Contract> {
}
