package com.meeting.booking.controller;

import com.meeting.booking.common.Result;
import com.meeting.booking.entity.Equipment;
import com.meeting.booking.service.EquipmentService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/equipments")
public class EquipmentController {

    @Autowired
    private EquipmentService equipmentService;

    @GetMapping("/{id}")
    public Result<Equipment> getById(@PathVariable Long id) {
        return Result.success(equipmentService.getById(id));
    }

    @GetMapping
    public Result<List<Equipment>> listAll() {
        return Result.success(equipmentService.listAll());
    }

    @GetMapping("/room/{roomId}")
    public Result<List<Equipment>> getByRoomId(@PathVariable Long roomId) {
        return Result.success(equipmentService.getByRoomId(roomId));
    }

    @PostMapping
    public Result<Boolean> create(@RequestBody Equipment equipment) {
        return Result.success(equipmentService.create(equipment));
    }

    @PutMapping
    public Result<Boolean> update(@RequestBody Equipment equipment) {
        return Result.success(equipmentService.update(equipment));
    }

    @DeleteMapping("/{id}")
    public Result<Boolean> delete(@PathVariable Long id) {
        return Result.success(equipmentService.delete(id));
    }
}
