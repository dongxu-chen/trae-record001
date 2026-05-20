using CloudDesktop.Api.Models;
using CloudDesktop.Api.Services;
using Microsoft.AspNetCore.Mvc;

namespace CloudDesktop.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class GpusController : ControllerBase
{
    private readonly IGpuService _gpuService;

    public GpusController(IGpuService gpuService)
    {
        _gpuService = gpuService;
    }

    [HttpGet]
    public async Task<ActionResult<List<GpuDevice>>> GetAll()
    {
        var gpus = await _gpuService.GetAllGpusAsync();
        return Ok(gpus);
    }

    [HttpGet("{id}")]
    public async Task<ActionResult<GpuDevice>> GetById(Guid id)
    {
        var gpu = await _gpuService.GetGpuByIdAsync(id);
        if (gpu == null) return NotFound();
        return Ok(gpu);
    }

    [HttpPost]
    public async Task<ActionResult<GpuDevice>> Create([FromBody] GpuDevice gpu)
    {
        var created = await _gpuService.CreateGpuAsync(gpu);
        return CreatedAtAction(nameof(GetById), new { id = created.Id }, created);
    }

    [HttpPut("{id}")]
    public async Task<ActionResult<GpuDevice>> Update(Guid id, [FromBody] GpuDevice gpu)
    {
        var updated = await _gpuService.UpdateGpuAsync(id, gpu);
        if (updated == null) return NotFound();
        return Ok(updated);
    }

    [HttpDelete("{id}")]
    public async Task<IActionResult> Delete(Guid id)
    {
        var success = await _gpuService.DeleteGpuAsync(id);
        if (!success) return NotFound();
        return NoContent();
    }

    [HttpPost("{gpuId}/assign/{desktopId}")]
    public async Task<IActionResult> AssignToDesktop(Guid gpuId, Guid desktopId, [FromQuery] bool isPassthrough = true)
    {
        var success = await _gpuService.AssignGpuToDesktopAsync(gpuId, desktopId, isPassthrough);
        if (!success) return BadRequest("Failed to assign GPU");
        return Ok(new { Success = true, Message = "GPU assigned successfully" });
    }

    [HttpPost("{gpuId}/release/{desktopId}")]
    public async Task<IActionResult> ReleaseFromDesktop(Guid gpuId, Guid desktopId)
    {
        var success = await _gpuService.ReleaseGpuFromDesktopAsync(gpuId, desktopId);
        if (!success) return BadRequest("Failed to release GPU");
        return Ok(new { Success = true, Message = "GPU released successfully" });
    }

    [HttpGet("desktop/{desktopId}")]
    public async Task<ActionResult<List<GpuAssignment>>> GetAssignmentsByDesktop(Guid desktopId)
    {
        var assignments = await _gpuService.GetGpuAssignmentsByDesktopAsync(desktopId);
        return Ok(assignments);
    }

    [HttpGet("available")]
    public async Task<ActionResult<List<GpuDevice>>> GetAvailableGpus([FromQuery] Guid? desktopPoolId = null)
    {
        var gpus = await _gpuService.GetAvailableGpusAsync(desktopPoolId);
        return Ok(gpus);
    }

    [HttpPost("{id}/metrics")]
    public async Task<IActionResult> UpdateMetrics(Guid id, [FromBody] GpuMetricsUpdateDto metrics)
    {
        var success = await _gpuService.UpdateGpuMetricsAsync(id, metrics.Utilization, metrics.MemoryUtilization,
            metrics.Temperature, metrics.PowerDraw);
        if (!success) return NotFound();
        return Ok(new { Success = true, Message = "Metrics updated successfully" });
    }
}

public class GpuMetricsUpdateDto
{
    public decimal Utilization { get; set; }
    public decimal MemoryUtilization { get; set; }
    public decimal Temperature { get; set; }
    public decimal PowerDraw { get; set; }
}
