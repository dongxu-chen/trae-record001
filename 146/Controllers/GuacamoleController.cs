using CloudDesktop.Api.Data;
using CloudDesktop.Api.Models.Guacamole;
using CloudDesktop.Api.Services.Guacamole;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using System.Net.WebSockets;

namespace CloudDesktop.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class GuacamoleController : ControllerBase
{
    private readonly ApplicationDbContext _context;
    private readonly IGuacamoleTunnel _tunnel;
    private readonly ILogger<GuacamoleController> _logger;

    public GuacamoleController(
        ApplicationDbContext context,
        IGuacamoleTunnel tunnel,
        ILogger<GuacamoleController> logger)
    {
        _context = context;
        _tunnel = tunnel;
        _logger = logger;
    }

    #region Connection Management

    [HttpGet("connections")]
    public async Task<ActionResult<IEnumerable<GuacamoleConnection>>> GetConnections(
        [FromQuery] Guid? poolId = null,
        [FromQuery] bool? isActive = null)
    {
        var query = _context.GuacamoleConnections.AsQueryable();

        if (poolId.HasValue)
            query = query.Where(c => c.DesktopPoolId == poolId.Value);

        if (isActive.HasValue)
            query = query.Where(c => c.IsActive == isActive.Value);

        var connections = await query
            .OrderBy(c => c.Name)
            .ToListAsync();

        return Ok(connections);
    }

    [HttpGet("connections/{id}")]
    public async Task<ActionResult<GuacamoleConnection>> GetConnection(Guid id)
    {
        var connection = await _context.GuacamoleConnections.FindAsync(id);
        if (connection == null) return NotFound();
        return Ok(connection);
    }

    [HttpPost("connections")]
    public async Task<ActionResult<GuacamoleConnection>> CreateConnection([FromBody] GuacamoleConnection connection)
    {
        connection.Id = Guid.NewGuid();
        connection.CreatedAt = DateTime.UtcNow;

        _context.GuacamoleConnections.Add(connection);
        await _context.SaveChangesAsync();

        return CreatedAtAction(nameof(GetConnection), new { id = connection.Id }, connection);
    }

    [HttpPut("connections/{id}")]
    public async Task<IActionResult> UpdateConnection(Guid id, [FromBody] GuacamoleConnection connection)
    {
        if (id != connection.Id) return BadRequest();

        var existing = await _context.GuacamoleConnections.FindAsync(id);
        if (existing == null) return NotFound();

        existing.Name = connection.Name;
        existing.Description = connection.Description;
        existing.Protocol = connection.Protocol;
        existing.Hostname = connection.Hostname;
        existing.Port = connection.Port;
        existing.Username = connection.Username;
        existing.Password = connection.Password;
        existing.Domain = connection.Domain;
        existing.Width = connection.Width;
        existing.Height = connection.Height;
        existing.Dpi = connection.Dpi;
        existing.ColorDepth = connection.ColorDepth;
        existing.EnableAudio = connection.EnableAudio;
        existing.EnableClipboard = connection.EnableClipboard;
        existing.EnableRecording = connection.EnableRecording;
        existing.RecordingPath = connection.RecordingPath;
        existing.IsActive = connection.IsActive;
        existing.UpdatedAt = DateTime.UtcNow;

        await _context.SaveChangesAsync();
        return NoContent();
    }

    [HttpDelete("connections/{id}")]
    public async Task<IActionResult> DeleteConnection(Guid id)
    {
        var connection = await _context.GuacamoleConnections.FindAsync(id);
        if (connection == null) return NotFound();

        connection.IsActive = false;
        connection.UpdatedAt = DateTime.UtcNow;
        await _context.SaveChangesAsync();

        return NoContent();
    }

    #endregion

    #region WebSocket Tunnel

    [HttpGet("ws")]
    public async Task WebSocketTunnel([FromQuery] Guid connectionId, [FromQuery] Guid userId)
    {
        if (!HttpContext.WebSockets.IsWebSocketRequest)
        {
            HttpContext.Response.StatusCode = 400;
            return;
        }

        var connection = await _context.GuacamoleConnections.FindAsync(connectionId);
        if (connection == null || !connection.IsActive)
        {
            HttpContext.Response.StatusCode = 404;
            return;
        }

        var user = await _context.Users.FindAsync(userId);
        if (user == null)
        {
            HttpContext.Response.StatusCode = 401;
            return;
        }

        var clientIp = HttpContext.Connection.RemoteIpAddress?.ToString() ?? "unknown";

        using var webSocket = await HttpContext.WebSockets.AcceptWebSocketAsync();
        await _tunnel.HandleWebSocketAsync(webSocket, connectionId, userId, clientIp);
    }

    #endregion

    #region Session Management

    [HttpGet("sessions")]
    public async Task<ActionResult<IEnumerable<GuacamoleSession>>> GetSessions(
        [FromQuery] Guid? connectionId = null,
        [FromQuery] Guid? userId = null,
        [FromQuery] bool? activeOnly = null,
        [FromQuery] int limit = 50)
    {
        var query = _context.GuacamoleSessions.AsQueryable();

        if (connectionId.HasValue)
            query = query.Where(s => s.ConnectionId == connectionId.Value);

        if (userId.HasValue)
            query = query.Where(s => s.UserId == userId.Value);

        if (activeOnly == true)
            query = query.Where(s => s.State == GuacamoleConnectionState.Connected);

        var sessions = await query
            .Include(s => s.User)
            .Include(s => s.Connection)
            .OrderByDescending(s => s.CreatedAt)
            .Take(limit)
            .ToListAsync();

        return Ok(sessions);
    }

    [HttpGet("sessions/{id}")]
    public async Task<ActionResult<GuacamoleSession>> GetSession(Guid id)
    {
        var session = await _context.GuacamoleSessions
            .Include(s => s.User)
            .Include(s => s.Connection)
            .FirstOrDefaultAsync(s => s.Id == id);

        if (session == null) return NotFound();
        return Ok(session);
    }

    [HttpPost("sessions/{id}/disconnect")]
    public async Task<IActionResult> DisconnectSession(Guid id)
    {
        await _tunnel.DisconnectSessionAsync(id);
        return Ok(new { Message = "Disconnect requested" });
    }

    [HttpGet("sessions/active/count")]
    public ActionResult<int> GetActiveSessionCount()
    {
        return Ok(_tunnel.GetActiveConnectionCount());
    }

    #endregion

    #region Session Recording

    [HttpGet("recordings")]
    public async Task<ActionResult<IEnumerable<object>>> GetRecordings(
        [FromQuery] Guid? sessionId = null,
        [FromQuery] Guid? userId = null,
        [FromQuery] int limit = 50)
    {
        var query = _context.GuacamoleSessions
            .Where(s => s.HasRecording && !string.IsNullOrEmpty(s.RecordingPath))
            .AsQueryable();

        if (sessionId.HasValue)
            query = query.Where(s => s.Id == sessionId.Value);

        if (userId.HasValue)
            query = query.Where(s => s.UserId == userId.Value);

        var recordings = await query
            .Include(s => s.User)
            .Include(s => s.Connection)
            .OrderByDescending(s => s.CreatedAt)
            .Take(limit)
            .Select(s => new
            {
                s.Id,
                s.ConnectionId,
                s.ConnectionName,
                s.UserId,
                UserName = s.User.Username,
                s.Protocol,
                s.ConnectedAt,
                s.Duration,
                s.RecordingPath,
                s.RecordingSizeBytes,
                s.FrameCount,
                s.KeyEventCount,
                s.MouseEventCount
            })
            .ToListAsync();

        return Ok(recordings);
    }

    [HttpGet("recordings/{sessionId}/download")]
    public async Task<IActionResult> DownloadRecording(Guid sessionId)
    {
        var session = await _context.GuacamoleSessions.FindAsync(sessionId);
        if (session == null || string.IsNullOrEmpty(session.RecordingPath) || !System.IO.File.Exists(session.RecordingPath))
            return NotFound();

        var fileBytes = await System.IO.File.ReadAllBytesAsync(session.RecordingPath);
        var fileName = $"recording-{sessionId}.guac";

        return File(fileBytes, "application/octet-stream", fileName);
    }

    [HttpGet("recordings/{sessionId}/playback")]
    public async Task<IActionResult> GetRecordingPlayback(Guid sessionId)
    {
        var session = await _context.GuacamoleSessions.FindAsync(sessionId);
        if (session == null || string.IsNullOrEmpty(session.RecordingPath) || !System.IO.File.Exists(session.RecordingPath))
            return NotFound();

        var content = await System.IO.File.ReadAllTextAsync(session.RecordingPath);

        return Ok(new
        {
            sessionId,
            session.ConnectionName,
            session.ConnectedAt,
            session.Duration,
            Content = content
        });
    }

    #endregion

    #region Statistics

    [HttpGet("stats")]
    public async Task<ActionResult<object>> GetStatistics()
    {
        var totalConnections = await _context.GuacamoleConnections.CountAsync(c => c.IsActive);
        var totalSessions = await _context.GuacamoleSessions.CountAsync();
        var activeSessions = _tunnel.GetActiveConnectionCount();
        var recordedSessions = await _context.GuacamoleSessions.CountAsync(s => s.HasRecording);

        var today = DateTime.UtcNow.Date;
        var todaySessions = await _context.GuacamoleSessions
            .CountAsync(s => s.CreatedAt >= today);

        var protocolStats = await _context.GuacamoleSessions
            .Where(s => s.CreatedAt >= today.AddDays(-30))
            .GroupBy(s => s.Protocol)
            .Select(g => new { Protocol = g.Key, Count = g.Count() })
            .ToListAsync();

        return Ok(new
        {
            TotalConnections = totalConnections,
            TotalSessions = totalSessions,
            ActiveSessions = activeSessions,
            RecordedSessions = recordedSessions,
            TodaySessions = todaySessions,
            ProtocolStats = protocolStats,
            ActiveSessionIds = _tunnel.GetActiveSessionIds()
        });
    }

    #endregion
}
