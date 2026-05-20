package com.payment.reconciliation.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.payment.reconciliation.entity.ChannelFeeConfig;
import org.apache.ibatis.annotations.Param;

import java.math.BigDecimal;
import java.util.List;

public interface ChannelFeeConfigMapper extends BaseMapper<ChannelFeeConfig> {

    List<ChannelFeeConfig> selectByChannelAndMerchant(@Param("channelCode") String channelCode,
                                                        @Param("merchantNo") String merchantNo);

    ChannelFeeConfig selectMatchedConfig(@Param("channelCode") String channelCode,
                                          @Param("merchantNo") String merchantNo,
                                          @Param("amount") BigDecimal amount);
}
