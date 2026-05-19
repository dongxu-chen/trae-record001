package com.logplatform;

import com.logplatform.model.ExportTask;
import com.logplatform.model.LogQueryRequest;
import com.logplatform.service.AsyncExportService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
class AsyncExportServiceTest {

    @Autowired
    private AsyncExportService asyncExportService;

    @Test
    void testCreateExportTask() {
        LogQueryRequest request = new LogQueryRequest();
        request.setQuery("error");
        request.setSize(10);

        ExportTask task = asyncExportService.createExportTask(
                request, 1000, ExportTask.ExportFormat.CSV);

        assertNotNull(task);
        assertNotNull(task.getTaskId());
        assertEquals(ExportTask.ExportStatus.PENDING, task.getStatus());
        assertEquals(ExportTask.ExportFormat.CSV, task.getFormat());
    }

    @Test
    void testGetTaskStatus() {
        LogQueryRequest request = new LogQueryRequest();
        request.setQuery("test");

        ExportTask task = asyncExportService.createExportTask(
                request, 100, ExportTask.ExportFormat.JSON);

        ExportTask found = asyncExportService.getTaskStatus(task.getTaskId());
        assertNotNull(found);
        assertEquals(task.getTaskId(), found.getTaskId());
    }

    @Test
    void testListTasks() {
        LogQueryRequest request = new LogQueryRequest();
        request.setQuery("test");

        asyncExportService.createExportTask(request, 100, ExportTask.ExportFormat.CSV);
        asyncExportService.createExportTask(request, 100, ExportTask.ExportFormat.JSON);

        List<ExportTask> tasks = asyncExportService.listTasks();
        assertTrue(tasks.size() >= 2);
    }

    @Test
    void testGetNonExistentTask() {
        ExportTask task = asyncExportService.getTaskStatus("non-existent-id");
        assertNull(task);
    }
}
