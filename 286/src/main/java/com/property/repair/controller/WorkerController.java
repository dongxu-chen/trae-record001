package com.property.repair.controller;

import com.property.repair.common.Result;
import com.property.repair.entity.RepairWorker;
import com.property.repair.service.RepairWorkerService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/worker")
@CrossOrigin
public class WorkerController {

    @Autowired
    private RepairWorkerService workerService;

    @GetMapping("/list")
    public Result<List<RepairWorker>> list() {
        return Result.success(workerService.getAllAvailableWorkers());
    }

    @GetMapping("/{workerId}")
    public Result<RepairWorker> getByWorkerId(@PathVariable Long workerId) {
        return Result.success(workerService.getByWorkerId(workerId));
    }
}
