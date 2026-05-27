package com.platform.points.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.platform.points.annotation.DistributedLock;
import com.platform.points.dto.PointsDeductDTO;
import com.platform.points.dto.PointsExchangeDTO;
import com.platform.points.entity.PointsMallOrder;
import com.platform.points.entity.PointsMallProduct;
import com.platform.points.entity.UserPoints;
import com.platform.points.enums.PointsSourceEnum;
import com.platform.points.exception.BusinessException;
import com.platform.points.mapper.PointsMallOrderMapper;
import com.platform.points.mapper.PointsMallProductMapper;
import com.platform.points.mapper.UserPointsMapper;
import com.platform.points.service.PointsMallService;
import com.platform.points.service.PointsService;
import com.platform.points.vo.PointsMallProductVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Slf4j
@Service
public class PointsMallServiceImpl implements PointsMallService {

    @Autowired
    private PointsMallProductMapper productMapper;

    @Autowired
    private PointsMallOrderMapper orderMapper;

    @Autowired
    private UserPointsMapper userPointsMapper;

    @Autowired
    private PointsService pointsService;

    @Override
    public List<PointsMallProductVO> listProducts() {
        LambdaQueryWrapper<PointsMallProduct> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(PointsMallProduct::getStatus, 1)
                .orderByAsc(PointsMallProduct::getPointsRequired);
        List<PointsMallProduct> products = productMapper.selectList(wrapper);
        return products.stream().map(this::convertToVO).collect(Collectors.toList());
    }

    @Override
    public PointsMallProductVO getProduct(Long productId) {
        PointsMallProduct product = productMapper.selectById(productId);
        if (product == null) {
            throw new BusinessException("商品不存在");
        }
        return convertToVO(product);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    @DistributedLock(key = "#dto.productId + '_' + #dto.userId", prefix = "points:mall:lock:", watchdog = true)
    public String exchange(PointsExchangeDTO dto) {
        PointsMallProduct product = productMapper.selectById(dto.getProductId());
        if (product == null || product.getStatus() != 1) {
            throw new BusinessException("商品不存在或已下架");
        }

        if (product.getStock() < dto.getQuantity()) {
            throw new BusinessException("库存不足");
        }

        LambdaQueryWrapper<UserPoints> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(UserPoints::getUserId, dto.getUserId());
        UserPoints userPoints = userPointsMapper.selectOne(wrapper);
        if (userPoints == null) {
            throw new BusinessException("用户积分账户不存在");
        }

        int totalPoints = product.getPointsRequired() * dto.getQuantity();
        if (userPoints.getAvailablePoints() < totalPoints) {
            throw new BusinessException("可用积分不足");
        }

        int stockRows = productMapper.deductStock(dto.getProductId(), dto.getQuantity());
        if (stockRows == 0) {
            throw new BusinessException("库存扣减失败，请稍后重试");
        }

        PointsDeductDTO deductDTO = new PointsDeductDTO();
        deductDTO.setUserId(dto.getUserId());
        deductDTO.setPoints(totalPoints);
        deductDTO.setSource(PointsSourceEnum.EXCHANGE.getCode());
        deductDTO.setOrderNo(generateOrderNo());
        deductDTO.setDescription("兑换商品: " + product.getProductName());
        pointsService.deductPoints(deductDTO);

        PointsMallOrder order = new PointsMallOrder();
        order.setOrderNo(deductDTO.getOrderNo());
        order.setUserId(dto.getUserId());
        order.setProductId(product.getId());
        order.setProductName(product.getProductName());
        order.setPointsRequired(product.getPointsRequired());
        order.setQuantity(dto.getQuantity());
        order.setTotalPoints(totalPoints);
        order.setStatus(1);
        order.setReceiverName(dto.getReceiverName());
        order.setReceiverPhone(dto.getReceiverPhone());
        order.setReceiverAddress(dto.getReceiverAddress());
        orderMapper.insert(order);

        log.info("积分兑换成功, userId: {}, productId: {}, quantity: {}, totalPoints: {}",
                dto.getUserId(), dto.getProductId(), dto.getQuantity(), totalPoints);

        return order.getOrderNo();
    }

    private PointsMallProductVO convertToVO(PointsMallProduct product) {
        PointsMallProductVO vo = new PointsMallProductVO();
        BeanUtils.copyProperties(product, vo);
        return vo;
    }

    private String generateOrderNo() {
        return "MALL" + UUID.randomUUID().toString().replace("-", "").toUpperCase();
    }
}
