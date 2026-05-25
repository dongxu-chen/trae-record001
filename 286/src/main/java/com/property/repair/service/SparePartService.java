package com.property.repair.service;

import com.property.repair.entity.SparePart;
import com.property.repair.entity.StockLog;
import com.property.repair.repository.SparePartRepository;
import com.property.repair.repository.StockLogRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class SparePartService {

    @Autowired
    private SparePartRepository sparePartRepository;

    @Autowired
    private StockLogRepository stockLogRepository;

    public List<SparePart> getAllParts() {
        return sparePartRepository.findAll();
    }

    public SparePart getById(Long id) {
        return sparePartRepository.findById(id).orElse(null);
    }

    public SparePart getByCode(String partCode) {
        return sparePartRepository.findByPartCode(partCode);
    }

    public List<SparePart> getLowStockParts() {
        return sparePartRepository.findLowStockParts();
    }

    @Transactional
    public SparePart createPart(SparePart part, Long operatorId, String operatorName) {
        part = sparePartRepository.save(part);

        StockLog log = new StockLog();
        log.setPartId(part.getId());
        log.setPartCode(part.getPartCode());
        log.setPartName(part.getPartName());
        log.setAction("CREATE");
        log.setChangeQuantity(part.getStockQuantity());
        log.setBeforeQuantity(0);
        log.setAfterQuantity(part.getStockQuantity());
        log.setOperatorId(operatorId);
        log.setOperatorName(operatorName);
        log.setRemark("创建备件，初始库存：" + part.getStockQuantity());
        stockLogRepository.save(log);

        return part;
    }

    @Transactional
    public SparePart updateStock(Long partId, Integer quantity, String action, 
                                  Long orderId, Long operatorId, String operatorName, String remark) {
        SparePart part = sparePartRepository.findById(partId).orElse(null);
        if (part == null) {
            throw new RuntimeException("备件不存在");
        }

        int beforeQuantity = part.getStockQuantity();
        
        if ("IN".equals(action)) {
            part.setStockQuantity(beforeQuantity + quantity);
        } else if ("OUT".equals(action)) {
            if (beforeQuantity < quantity) {
                throw new RuntimeException("库存不足");
            }
            part.setStockQuantity(beforeQuantity - quantity);
        }
        
        part = sparePartRepository.save(part);

        StockLog log = new StockLog();
        log.setPartId(part.getId());
        log.setPartCode(part.getPartCode());
        log.setPartName(part.getPartName());
        log.setAction(action);
        log.setChangeQuantity(quantity);
        log.setBeforeQuantity(beforeQuantity);
        log.setAfterQuantity(part.getStockQuantity());
        log.setOrderId(orderId);
        log.setOperatorId(operatorId);
        log.setOperatorName(operatorName);
        log.setRemark(remark);
        stockLogRepository.save(log);

        return part;
    }

    @Transactional
    public boolean lockStock(Long partId, Integer quantity) {
        SparePart part = sparePartRepository.findById(partId).orElse(null);
        if (part == null) {
            return false;
        }

        int available = part.getStockQuantity() - part.getLockedQuantity();
        if (available < quantity) {
            return false;
        }

        part.setLockedQuantity(part.getLockedQuantity() + quantity);
        sparePartRepository.save(part);
        return true;
    }

    @Transactional
    public boolean unlockStock(Long partId, Integer quantity) {
        SparePart part = sparePartRepository.findById(partId).orElse(null);
        if (part == null) {
            return false;
        }

        if (part.getLockedQuantity() < quantity) {
            return false;
        }

        part.setLockedQuantity(part.getLockedQuantity() - quantity);
        sparePartRepository.save(part);
        return true;
    }

    @Transactional
    public boolean confirmUsage(Long partId, Integer quantity, Long orderId, 
                                Long operatorId, String operatorName) {
        SparePart part = sparePartRepository.findById(partId).orElse(null);
        if (part == null) {
            return false;
        }

        if (part.getLockedQuantity() < quantity) {
            return false;
        }

        int beforeQuantity = part.getStockQuantity();
        part.setStockQuantity(beforeQuantity - quantity);
        part.setLockedQuantity(part.getLockedQuantity() - quantity);
        sparePartRepository.save(part);

        StockLog log = new StockLog();
        log.setPartId(part.getId());
        log.setPartCode(part.getPartCode());
        log.setPartName(part.getPartName());
        log.setAction("USE");
        log.setChangeQuantity(quantity);
        log.setBeforeQuantity(beforeQuantity);
        log.setAfterQuantity(part.getStockQuantity());
        log.setOrderId(orderId);
        log.setOperatorId(operatorId);
        log.setOperatorName(operatorName);
        log.setRemark("工单领用，扣除锁定库存");
        stockLogRepository.save(log);

        return true;
    }

    public List<StockLog> getPartLogs(Long partId) {
        return stockLogRepository.findByPartIdOrderByCreateTimeDesc(partId);
    }
}
