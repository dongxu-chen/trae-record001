package com.property.repair.service;

import com.property.repair.entity.RepairType;
import com.property.repair.repository.RepairTypeRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class RepairTypeService {

    @Autowired
    private RepairTypeRepository repairTypeRepository;

    public List<RepairType> getAllTypes() {
        return repairTypeRepository.findByStatus(1);
    }

    public RepairType getById(Long id) {
        return repairTypeRepository.findById(id).orElse(null);
    }
}
