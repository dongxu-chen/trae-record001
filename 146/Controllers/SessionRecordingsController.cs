using CloudDesktop.Api.Models;
using CloudDesktop.Api.Models.Enums;
using CloudDesktop.Api.Services;
using Microsoft.AspNetCore.Mvc;

namespace CloudDesktop.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class SessionRecordingsController : ControllerBase
{
    private readonly ISessionRecordingService _recordingService;

    public SessionRecordingsController(ISessionRecordingService recordingService)
    {
        _recordingService = recordingService;
    }

    [HttpGet("session/{sessionId}")]
    public async Task<ActionResult<List<SessionRecording>>> GetBySession(Guid sessionId)
    {
        var recordings = await _recordingService.GetRecordingsBySessionAsync(sessionId);
        return Ok(recordings);
    }

    [HttpGet("user/{userId}")]
    public async Task<ActionResult<List<SessionRecording>>> GetByUser(Guid userId)
    {
        var recordings = await _recordingService.GetRecordingsByUserAsync(userId);
        return Ok(recordings);
    }

    [HttpGet("desktop/{desktopId}")]
    public async Task<ActionResult<List<SessionRecording>>> GetByDesktop(Guid desktopId)
    {
        var recordings = await _recordingService.GetRecordingsByDesktopAsync(desktopId);
        return Ok(recordings);
    }

    [HttpGet("{id}")]
    public async Task<ActionResult<SessionRecording>> GetById(Guid id)
    {
        var recording = await _recordingService.GetRecordingByIdAsync(id);
        if (recording == null) return NotFound();
        return Ok(recording);
    }

    [HttpPost("start/{sessionId}")]
    public async Task<ActionResult<SessionRecording>> StartRecording(Guid sessionId,
        [FromQuery] RecordingQuality quality = RecordingQuality.Medium)
    {
        var recording = await _recordingService.StartRecordingAsync(sessionId, quality);
        if (recording == null) return BadRequest("Failed to start recording");
        return CreatedAtAction(nameof(GetById), new { id = recording.Id }, recording);
    }

    [HttpPost("{id}/stop")]
    public async Task<IActionResult> StopRecording(Guid id)
    {
        var success = await _recordingService.StopRecordingAsync(id);
        if (!success) return BadRequest("Failed to stop recording");
        return Ok(new { Success = true, Message = "Recording stopped successfully" });
    }

    [HttpPost("{id}/pause")]
    public async Task<IActionResult> PauseRecording(Guid id)
    {
        var success = await _recordingService.PauseRecordingAsync(id);
        if (!success) return BadRequest("Failed to pause recording");
        return Ok(new { Success = true, Message = "Recording paused successfully" });
    }

    [HttpPost("{id}/resume")]
    public async Task<IActionResult> ResumeRecording(Guid id)
    {
        var success = await _recordingService.ResumeRecordingAsync(id);
        if (!success) return BadRequest("Failed to resume recording");
        return Ok(new { Success = true, Message = "Recording resumed successfully" });
    }

    [HttpDelete("{id}")]
    public async Task<IActionResult> DeleteRecording(Guid id)
    {
        var success = await _recordingService.DeleteRecordingAsync(id);
        if (!success) return NotFound();
        return NoContent();
    }

    [HttpPut("{id}/status")]
    public async Task<IActionResult> UpdateStatus(Guid id, [FromBody] UpdateRecordingStatusDto dto)
    {
        var success = await _recordingService.UpdateRecordingStatusAsync(id, dto.Status, dto.FileSizeBytes, dto.ErrorMessage);
        if (!success) return NotFound();
        return Ok(new { Success = true, Message = "Status updated successfully" });
    }
}

public class UpdateRecordingStatusDto
{
    public RecordingStatus Status { get; set; }
    public long? FileSizeBytes { get; set; }
    public string? ErrorMessage { get; set; }
}
