package com.property.repair.controller;

import com.property.repair.common.Result;
import com.property.repair.entity.WorkerLocation;
import com.property.repair.service.LocationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/location")
@CrossOrigin
public class LocationController {

    @Autowired
    private LocationService locationService;

    @PostMapping("/update")
    public Result<WorkerLocation> updateLocation(
            @RequestParam Long workerId,
            @RequestParam String workerName,
            @RequestParam Double longitude,
            @RequestParam Double latitude,
            @RequestParam(required = false) String address,
            @RequestParam(required = false) Double accuracy) {
        try {
            WorkerLocation location = locationService.updateLocation(
                workerId, workerName, longitude, latitude, address, accuracy);
            return Result.success(location);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/worker/{workerId}")
    public Result<WorkerLocation> getCurrentLocation(@PathVariable Long workerId) {
        return Result.success(locationService.getCurrentLocation(workerId));
    }

    @GetMapping("/worker/{workerId}/history")
    public Result<List<WorkerLocation>> getLocationHistory(
            @PathVariable Long workerId,
            @RequestParam(defaultValue = "24") int hours) {
        return Result.success(locationService.getLocationHistory(workerId, hours));
    }

    @GetMapping("/all")
    public Result<Map<Long, WorkerLocation>> getAllActiveWorkersLocation() {
        return Result.success(locationService.getAllActiveWorkersLocation());
    }

    @PostMapping("/track/{ownerId}/{workerId}")
    public Result<Void> startTracking(@PathVariable Long ownerId, @PathVariable Long workerId) {
        locationService.sendLocationToOwner(ownerId, workerId);
        return Result.success();
    }
}
