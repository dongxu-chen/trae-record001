package com.platform.points.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.platform.points.dto.PointsExchangeDTO;
import com.platform.points.vo.PointsMallProductVO;

import java.util.List;

public interface PointsMallService {

    List<PointsMallProductVO> listProducts();

    PointsMallProductVO getProduct(Long productId);

    String exchange(PointsExchangeDTO dto);
}
