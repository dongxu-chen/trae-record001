package com.smartschedule.service;

import com.smartschedule.entity.ShiftType;
import com.smartschedule.repository.ShiftTypeRepository;
import jakarta.persistence.EntityNotFoundException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class ShiftTypeService {

    @Autowired
    private ShiftTypeRepository shiftTypeRepository;

    @Transactional
    public ShiftType createShiftType(ShiftType shiftType) {
        return shiftTypeRepository.save(shiftType);
    }

    public ShiftType getShiftType(Long id) {
        return shiftTypeRepository.findById(id)
                .orElseThrow(() -> new EntityNotFoundException("ShiftType not found with id: " + id));
    }

    public List<ShiftType> getAllShiftTypes() {
        return shiftTypeRepository.findAll();
    }

    public List<ShiftType> getActiveShiftTypes() {
        return shiftTypeRepository.findByIsActiveTrue();
    }

    @Transactional
    public ShiftType updateShiftType(Long id, ShiftType shiftTypeDetails) {
        ShiftType shiftType = getShiftType(id);
        shiftType.setCode(shiftTypeDetails.getCode());
        shiftType.setName(shiftTypeDetails.getName());
        shiftType.setStartTime(shiftTypeDetails.getStartTime());
        shiftType.setEndTime(shiftTypeDetails.getEndTime());
        shiftType.setDurationHours(shiftTypeDetails.getDurationHours());
        shiftType.setColor(shiftTypeDetails.getColor());
        shiftType.setIsActive(shiftTypeDetails.getIsActive());
        return shiftTypeRepository.save(shiftType);
    }

    @Transactional
    public void deleteShiftType(Long id) {
        shiftTypeRepository.deleteById(id);
    }
}
