package com.sla.monitor.controller;

import com.sla.monitor.model.ServiceInfo;
import com.sla.monitor.repository.ServiceInfoRepository;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Optional;

@RestController
@RequestMapping("/api/services")
public class ServiceController {

    private final ServiceInfoRepository serviceInfoRepository;

    public ServiceController(ServiceInfoRepository serviceInfoRepository) {
        this.serviceInfoRepository = serviceInfoRepository;
    }

    @GetMapping
    public List<ServiceInfo> getAllServices() {
        return serviceInfoRepository.findAll();
    }

    @GetMapping("/active")
    public List<ServiceInfo> getActiveServices() {
        return serviceInfoRepository.findByActiveTrue();
    }

    @GetMapping("/{serviceName}")
    public ResponseEntity<ServiceInfo> getServiceByName(@PathVariable String serviceName) {
        Optional<ServiceInfo> service = serviceInfoRepository.findByServiceName(serviceName);
        return service.map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public ResponseEntity<ServiceInfo> createService(@RequestBody ServiceInfo serviceInfo) {
        if (serviceInfoRepository.existsByServiceName(serviceInfo.getServiceName())) {
            return ResponseEntity.badRequest().build();
        }
        ServiceInfo saved = serviceInfoRepository.save(serviceInfo);
        return ResponseEntity.ok(saved);
    }

    @PutMapping("/{serviceName}")
    public ResponseEntity<ServiceInfo> updateService(
            @PathVariable String serviceName,
            @RequestBody ServiceInfo serviceInfo) {
        return serviceInfoRepository.findByServiceName(serviceName)
                .map(existing -> {
                    existing.setDescription(serviceInfo.getDescription());
                    existing.setEndpoint(serviceInfo.getEndpoint());
                    existing.setAvailabilityTarget(serviceInfo.getAvailabilityTarget());
                    existing.setLatencyTargetMs(serviceInfo.getLatencyTargetMs());
                    existing.setErrorRateTarget(serviceInfo.getErrorRateTarget());
                    existing.setActive(serviceInfo.isActive());
                    existing.setUseTierTargets(serviceInfo.isUseTierTargets());
                    if (serviceInfo.getSlaTier() != null && serviceInfo.getSlaTier().getId() != null) {
                        existing.setSlaTier(serviceInfo.getSlaTier());
                    }
                    return ResponseEntity.ok(serviceInfoRepository.save(existing));
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{serviceName}")
    public ResponseEntity<Void> deleteService(@PathVariable String serviceName) {
        return serviceInfoRepository.findByServiceName(serviceName)
                .map(service -> {
                    serviceInfoRepository.delete(service);
                    return ResponseEntity.ok().<Void>build();
                })
                .orElse(ResponseEntity.notFound().build());
    }
}
