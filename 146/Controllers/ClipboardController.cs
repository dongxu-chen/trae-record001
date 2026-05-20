using CloudDesktop.Api.Models;
using CloudDesktop.Api.Services;
using Microsoft.AspNetCore.Mvc;

namespace CloudDesktop.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class ClipboardController : ControllerBase
{
    private readonly IClipboardService _clipboardService;

    public ClipboardController(IClipboardService clipboardService)
    {
        _clipboardService = clipboardService;
    }

    [HttpGet("configuration/desktop/{desktopId}")]
    public async Task<ActionResult<ClipboardConfiguration>> GetDesktopConfiguration(Guid desktopId)
    {
        var config = await _clipboardService.GetConfigurationByDesktopAsync(desktopId);
        if (config == null) return NotFound();
        return Ok(config);
    }

    [HttpGet("configuration/pool/{desktopPoolId}")]
    public async Task<ActionResult<ClipboardConfiguration>> GetPoolConfiguration(Guid desktopPoolId)
    {
        var config = await _clipboardService.GetConfigurationByPoolAsync(desktopPoolId);
        if (config == null) return NotFound();
        return Ok(config);
    }

    [HttpGet("configuration/user/{userId}")]
    public async Task<ActionResult<ClipboardConfiguration>> GetUserConfiguration(Guid userId)
    {
        var config = await _clipboardService.GetConfigurationByUserAsync(userId);
        if (config == null) return NotFound();
        return Ok(config);
    }

    [HttpPost("configuration")]
    public async Task<ActionResult<ClipboardConfiguration>> CreateOrUpdateConfiguration([FromBody] ClipboardConfiguration config)
    {
        var result = await _clipboardService.CreateOrUpdateConfigurationAsync(config);
        return Ok(result);
    }

    [HttpDelete("configuration/{id}")]
    public async Task<IActionResult> DeleteConfiguration(Guid id)
    {
        var success = await _clipboardService.DeleteConfigurationAsync(id);
        if (!success) return NotFound();
        return NoContent();
    }

    [HttpGet("check/{desktopId}/{userId}")]
    public async Task<ActionResult<bool>> IsClipboardAllowed(Guid desktopId, Guid userId, [FromQuery] bool isCopyFromClient = true)
    {
        var allowed = await _clipboardService.IsClipboardAllowedAsync(desktopId, userId, isCopyFromClient);
        return Ok(new { Allowed = allowed });
    }

    [HttpGet("check-file/{desktopId}/{userId}")]
    public async Task<ActionResult<bool>> IsFileTransferAllowed(Guid desktopId, Guid userId, [FromQuery] string? fileType = null)
    {
        var allowed = await _clipboardService.IsFileTransferAllowedAsync(desktopId, userId, fileType);
        return Ok(new { Allowed = allowed });
    }

    [HttpPost("log")]
    public async Task<IActionResult> LogActivity([FromBody] ClipboardActivityLogDto log)
    {
        await _clipboardService.LogClipboardActivityAsync(log.SessionId, log.UserId, log.DesktopId,
            log.IsCopyFromClient, log.ContentType, log.ContentSizeKB, log.FileName, log.WasBlocked, log.BlockReason);
        return Ok(new { Success = true, Message = "Activity logged successfully" });
    }

    [HttpGet("logs/session/{sessionId}")]
    public async Task<ActionResult<List<ClipboardAuditLog>>> GetSessionLogs(Guid sessionId, [FromQuery] int limit = 100)
    {
        var logs = await _clipboardService.GetAuditLogsBySessionAsync(sessionId, limit);
        return Ok(logs);
    }

    [HttpGet("logs/user/{userId}")]
    public async Task<ActionResult<List<ClipboardAuditLog>>> GetUserLogs(Guid userId, [FromQuery] int limit = 100)
    {
        var logs = await _clipboardService.GetAuditLogsByUserAsync(userId, limit);
        return Ok(logs);
    }
}

public class ClipboardActivityLogDto
{
    public Guid SessionId { get; set; }
    public Guid UserId { get; set; }
    public Guid DesktopId { get; set; }
    public bool IsCopyFromClient { get; set; }
    public string? ContentType { get; set; }
    public int ContentSizeKB { get; set; }
    public string? FileName { get; set; }
    public bool WasBlocked { get; set; }
    public string? BlockReason { get; set; }
}
