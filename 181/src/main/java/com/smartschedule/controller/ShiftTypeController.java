package com.smartschedule.controller;

import com.smartschedule.entity.ShiftType;
import com.smartschedule.service.ShiftTypeService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/shift-types")
@CrossOrigin(origins = "*")
public class ShiftTypeController {

    @Autowired
    private ShiftTypeService shiftTypeService;

    @PostMapping
    public ResponseEntity<ShiftType> createShiftType(@RequestBody ShiftType shiftType) {
        return ResponseEntity.ok(shiftTypeService.createShiftType(shiftType));
    }

    @GetMapping("/{id}")
    public ResponseEntity<ShiftType> getShiftType(@PathVariable Long id) {
        return ResponseEntity.ok(shiftTypeService.getShiftType(id));
    }

    @GetMapping
    public ResponseEntity<List<ShiftType>> getAllShiftTypes() {
        return ResponseEntity.ok(shiftTypeService.getAllShiftTypes());
    }

    @GetMapping("/active")
    public ResponseEntity<List<ShiftType>> getActiveShiftTypes() {
        return ResponseEntity.ok(shiftTypeService.getActiveShiftTypes());
    }

    @PutMapping("/{id}")
    public ResponseEntity<ShiftType> updateShiftType(@PathVariable Long id, @RequestBody ShiftType shiftType) {
        return ResponseEntity.ok(shiftTypeService.updateShiftType(id, shiftType));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteShiftType(@PathVariable Long id) {
        shiftTypeService.deleteShiftType(id);
        return ResponseEntity.ok().build();
    }
}
