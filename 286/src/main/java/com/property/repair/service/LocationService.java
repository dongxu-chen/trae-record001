package com.property.repair.service;

import com.property.repair.entity.WorkerLocation;
import com.property.repair.repository.WorkerLocationRepository;
import com.property.repair.websocket.NotificationWebSocket;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;

@Service
public class LocationService {

    @Autowired
    private WorkerLocationRepository locationRepository;

    @Autowired
    private NotificationWebSocket webSocket;

    private final Map<Long, WorkerLocation> currentLocations = new HashMap<>();

    public WorkerLocation updateLocation(Long workerId, String workerName, 
                                         Double longitude, Double latitude, 
                                         String address, Double accuracy) {
        WorkerLocation location = new WorkerLocation();
        location.setWorkerId(workerId);
        location.setWorkerName(workerName);
        location.setLongitude(longitude);
        location.setLatitude(latitude);
        location.setAddress(address);
        location.setAccuracy(accuracy);
        location = locationRepository.save(location);

        currentLocations.put(workerId, location);

        broadcastLocation(location);

        return location;
    }

    public WorkerLocation getCurrentLocation(Long workerId) {
        WorkerLocation cached = currentLocations.get(workerId);
        if (cached != null) {
            return cached;
        }
        return locationRepository.findTopByWorkerIdOrderByCreateTimeDesc(workerId).orElse(null);
    }

    public List<WorkerLocation> getLocationHistory(Long workerId, int hours) {
        LocalDateTime startTime = LocalDateTime.now().minusHours(hours);
        return locationRepository.findLocationHistory(workerId, startTime);
    }

    public Map<Long, WorkerLocation> getAllActiveWorkersLocation() {
        LocalDateTime threshold = LocalDateTime.now().minusMinutes(30);
        List<WorkerLocation> recent = locationRepository.findRecentLocations(threshold);
        
        Map<Long, WorkerLocation> result = new HashMap<>();
        for (WorkerLocation loc : recent) {
            WorkerLocation existing = result.get(loc.getWorkerId());
            if (existing == null || loc.getCreateTime().isAfter(existing.getCreateTime())) {
                result.put(loc.getWorkerId(), loc);
            }
        }
        return result;
    }

    private void broadcastLocation(WorkerLocation location) {
        Map<String, Object> locationData = new HashMap<>();
        locationData.put("workerId", location.getWorkerId());
        locationData.put("workerName", location.getWorkerName());
        locationData.put("longitude", location.getLongitude());
        locationData.put("latitude", location.getLatitude());
        locationData.put("address", location.getAddress());
        locationData.put("timestamp", location.getCreateTime().toString());

        webSocket.broadcast("WORKER_LOCATION_UPDATE", locationData);
    }

    public void sendLocationToOwner(Long ownerId, Long workerId) {
        WorkerLocation location = getCurrentLocation(workerId);
        if (location != null) {
            Map<String, Object> locationData = new HashMap<>();
            locationData.put("workerId", location.getWorkerId());
            locationData.put("workerName", location.getWorkerName());
            locationData.put("longitude", location.getLongitude());
            locationData.put("latitude", location.getLatitude());
            locationData.put("address", location.getAddress());
            locationData.put("timestamp", location.getCreateTime().toString());

            webSocket.sendToOwner(ownerId, "WORKER_LOCATION", locationData);
        }
    }
}
