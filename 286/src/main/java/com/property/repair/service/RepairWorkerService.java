package com.property.repair.service;

import com.property.repair.entity.RepairWorker;
import com.property.repair.entity.SysUser;
import com.property.repair.repository.RepairWorkerRepository;
import com.property.repair.repository.SysUserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class RepairWorkerService {

    @Autowired
    private RepairWorkerRepository repairWorkerRepository;

    @Autowired
    private SysUserRepository sysUserRepository;

    public List<RepairWorker> getAllAvailableWorkers() {
        return repairWorkerRepository.findByStatus(1);
    }

    public RepairWorker getByWorkerId(Long workerId) {
        return repairWorkerRepository.findByWorkerId(workerId);
    }

    public SysUser getWorkerUser(Long workerId) {
        return sysUserRepository.findById(workerId).orElse(null);
    }

    public void increaseWorkload(Long workerId) {
        RepairWorker worker = repairWorkerRepository.findByWorkerId(workerId);
        if (worker != null) {
            worker.setCurrentWorkload(worker.getCurrentWorkload() + 1);
            repairWorkerRepository.save(worker);
        }
    }

    public void decreaseWorkload(Long workerId) {
        RepairWorker worker = repairWorkerRepository.findByWorkerId(workerId);
        if (worker != null && worker.getCurrentWorkload() > 0) {
            worker.setCurrentWorkload(worker.getCurrentWorkload() - 1);
            repairWorkerRepository.save(worker);
        }
    }
}
