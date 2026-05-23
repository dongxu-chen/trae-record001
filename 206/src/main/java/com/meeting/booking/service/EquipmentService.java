package com.meeting.booking.service;

import com.meeting.booking.entity.Equipment;
import com.meeting.booking.mapper.EquipmentMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class EquipmentService {

    @Autowired
    private EquipmentMapper equipmentMapper;

    public Equipment getById(Long id) {
        return equipmentMapper.selectById(id);
    }

    public List<Equipment> listAll() {
        return equipmentMapper.selectAll();
    }

    public List<Equipment> getByRoomId(Long roomId) {
        return equipmentMapper.selectByRoomId(roomId);
    }

    public List<Equipment> getByTypes(List<String> types) {
        return equipmentMapper.selectByTypes(types);
    }

    public boolean create(Equipment equipment) {
        return equipmentMapper.insert(equipment) > 0;
    }

    public boolean update(Equipment equipment) {
        return equipmentMapper.update(equipment) > 0;
    }

    public boolean delete(Long id) {
        return equipmentMapper.deleteById(id) > 0;
    }
}
