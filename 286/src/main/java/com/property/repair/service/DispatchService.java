package com.property.repair.service;

import com.property.repair.domain.DispatchRequest;
import com.property.repair.domain.WorkerCandidate;
import com.property.repair.entity.RepairOrder;
import com.property.repair.entity.RepairWorker;
import com.property.repair.entity.SysUser;
import com.property.repair.repository.RepairOrderRepository;
import org.kie.api.runtime.KieContainer;
import org.kie.api.runtime.KieSession;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Service
public class DispatchService {

    @Autowired
    private KieContainer kieContainer;

    @Autowired
    private RepairWorkerService workerService;

    @Autowired
    private RepairOrderRepository orderRepository;

    @Autowired
    private RepairLogService logService;

    @Value("${repair.dispatch.max-workload:5}")
    private Integer maxWorkload;

    public WorkerCandidate autoDispatch(RepairOrder order) {
        List<RepairWorker> workers = workerService.getAllAvailableWorkers();
        List<WorkerCandidate> candidates = new ArrayList<>();

        for (RepairWorker worker : workers) {
            SysUser user = workerService.getWorkerUser(worker.getWorkerId());
            if (user != null) {
                candidates.add(new WorkerCandidate(
                    worker.getWorkerId(),
                    user.getRealName(),
                    worker.getSkills(),
                    worker.getCurrentWorkload(),
                    worker.getAvgRating(),
                    worker.getLongitude(),
                    worker.getLatitude()
                ));
            }
        }

        DispatchRequest request = new DispatchRequest(
            order.getRepairTypeName(),
            order.getPriority(),
            maxWorkload,
            order.getLongitude(),
            order.getLatitude(),
            candidates
        );

        KieSession kieSession = kieContainer.newKieSession();
        kieSession.insert(request);
        for (WorkerCandidate candidate : candidates) {
            kieSession.insert(candidate);
        }
        kieSession.fireAllRules();
        kieSession.dispose();

        WorkerCandidate selected = request.getSelectedWorker();
        if (selected != null) {
            assignWorker(order, selected.getWorkerId(), selected.getWorkerName());
        }

        return selected;
    }

    public void assignWorker(RepairOrder order, Long workerId, String workerName) {
        SysUser worker = workerService.getWorkerUser(workerId);
        if (worker == null) {
            throw new RuntimeException("维修工不存在");
        }

        order.setWorkerId(workerId);
        order.setWorkerName(workerName);
        order.setWorkerPhone(worker.getPhone());
        order.setStatus("ASSIGNED");
        order.setAssignTime(LocalDateTime.now());
        orderRepository.save(order);

        workerService.increaseWorkload(workerId);

        logService.addLog(order, "派单", 1L, "系统", "自动派单给维修工：" + workerName);
    }
}
