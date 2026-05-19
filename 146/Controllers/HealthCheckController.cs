using CloudDesktop.Api.Models;
using CloudDesktop.Api.Services;
using Microsoft.AspNetCore.Mvc;

namespace CloudDesktop.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class HealthCheckController : ControllerBase
{
    private readonly IHealthCheckService _healthCheckService;

    public HealthCheckController(IHealthCheckService healthCheckService)
    {
        _healthCheckService = healthCheckService;
    }

    [HttpPost("check/{desktopId}")]
    public async Task<ActionResult<DesktopHealthCheck>> PerformHealthCheck(Guid desktopId)
    {
        try
        {
            var result = await _healthCheckService.PerformHealthCheckAsync(desktopId);
            return Ok(result);
        }
        catch (InvalidOperationException ex)
        {
            return BadRequest(ex.Message);
        }
    }

    [HttpGet("history/{desktopId}")]
    public async Task<ActionResult<List<DesktopHealthCheck>>> GetHealthCheckHistory(Guid desktopId, [FromQuery] int limit = 50)
    {
        var history = await _healthCheckService.GetHealthCheckHistoryAsync(desktopId, limit);
        return Ok(history);
    }

    [HttpGet("configuration/desktop/{desktopId}")]
    public async Task<ActionResult<DesktopHealthConfiguration>> GetDesktopConfiguration(Guid desktopId)
    {
        var config = await _healthCheckService.GetHealthConfigurationAsync(desktopId);
        if (config == null) return NotFound();
        return Ok(config);
    }

    [HttpGet("configuration/pool/{desktopPoolId}")]
    public async Task<ActionResult<DesktopHealthConfiguration>> GetPoolConfiguration(Guid desktopPoolId)
    {
        var config = await _healthCheckService.GetHealthConfigurationAsync(null, desktopPoolId);
        if (config == null) return NotFound();
        return Ok(config);
    }

    [HttpPost("configuration")]
    public async Task<ActionResult<DesktopHealthConfiguration>> CreateOrUpdateConfiguration([FromBody] DesktopHealthConfiguration config)
    {
        var result = await _healthCheckService.CreateOrUpdateConfigurationAsync(config);
        return Ok(result);
    }

    [HttpPost("recover/{desktopId}")]
    public async Task<IActionResult> TryRecoverDesktop(Guid desktopId, [FromBody] RecoveryReasonDto reason)
    {
        var success = await _healthCheckService.TryRecoverDesktopAsync(desktopId, reason.Reason);
        if (!success) return BadRequest("Recovery failed or not needed");
        return Ok(new { Success = true, Message = "Recovery initiated successfully" });
    }

    [HttpGet("recovery/{desktopId}")]
    public async Task<ActionResult<List<RecoveryHistory>>> GetRecoveryHistory(Guid desktopId, [FromQuery] int limit = 50)
    {
        var history = await _healthCheckService.GetRecoveryHistoryAsync(desktopId, limit);
        return Ok(history);
    }

    [HttpPost("metrics/{desktopId}")]
    public async Task<IActionResult> RecordMetrics(Guid desktopId, [FromBody] DesktopMetricsDto metrics)
    {
        await _healthCheckService.RecordMetricsAsync(desktopId, metrics.CpuUsagePercent, metrics.MemoryUsagePercent,
            metrics.DiskUsagePercent, metrics.NetworkInBytes, metrics.NetworkOutBytes, metrics.NetworkLatencyMs,
            metrics.GpuUsagePercent, metrics.GpuMemoryUsagePercent, metrics.GpuTemperature);
        return Ok(new { Success = true, Message = "Metrics recorded successfully" });
    }

    [HttpGet("metrics/{desktopId}")]
    public async Task<ActionResult<List<DesktopMetrics>>> GetMetricsHistory(Guid desktopId,
        [FromQuery] DateTime? startTime = null, [FromQuery] DateTime? endTime = null)
    {
        var metrics = await _healthCheckService.GetMetricsHistoryAsync(desktopId, startTime, endTime);
        return Ok(metrics);
    }

    [HttpGet("recovery-needed/{desktopId}")]
    public async Task<ActionResult<bool>> IsRecoveryNeeded(Guid desktopId)
    {
        var needed = await _healthCheckService.IsRecoveryNeededAsync(desktopId);
        return Ok(new { RecoveryNeeded = needed });
    }
}

public class RecoveryReasonDto
{
    public string Reason { get; set; } = string.Empty;
}

public class DesktopMetricsDto
{
    public decimal CpuUsagePercent { get; set; }
    public decimal MemoryUsagePercent { get; set; }
    public decimal DiskUsagePercent { get; set; }
    public long NetworkInBytes { get; set; }
    public long NetworkOutBytes { get; set; }
    public int NetworkLatencyMs { get; set; }
    public decimal GpuUsagePercent { get; set; }
    public decimal GpuMemoryUsagePercent { get; set; }
    public decimal GpuTemperature { get; set; }
}
