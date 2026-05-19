using CloudDesktop.Api.Dtos;
using CloudDesktop.Api.Services;
using Microsoft.AspNetCore.Mvc;

namespace CloudDesktop.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class SessionsController : ControllerBase
{
    private readonly ISessionService _sessionService;

    public SessionsController(ISessionService sessionService)
    {
        _sessionService = sessionService;
    }

    [HttpGet]
    public async Task<ActionResult<List<SessionDetailDto>>> GetAll(
        [FromQuery] Guid? userId = null,
        [FromQuery] Guid? desktopPoolId = null)
    {
        var sessions = await _sessionService.GetAllAsync(userId, desktopPoolId);
        return Ok(sessions);
    }

    [HttpGet("{id}")]
    public async Task<ActionResult<SessionDetailDto>> GetById(Guid id)
    {
        var session = await _sessionService.GetByIdAsync(id);
        if (session == null) return NotFound();
        return Ok(session);
    }

    [HttpPost]
    public async Task<ActionResult<SessionDto>> Create(CreateSessionDto dto)
    {
        try
        {
            var session = await _sessionService.CreateAsync(dto);
            return CreatedAtAction(nameof(GetById), new { id = session.Id }, session);
        }
        catch (InvalidOperationException ex)
        {
            return BadRequest(ex.Message);
        }
    }

    [HttpPut("{id}")]
    public async Task<ActionResult<SessionDto>> Update(Guid id, UpdateSessionDto dto)
    {
        var session = await _sessionService.UpdateAsync(id, dto);
        if (session == null) return NotFound();
        return Ok(session);
    }

    [HttpPost("{id}/terminate")]
    public async Task<IActionResult> Terminate(Guid id)
    {
        var success = await _sessionService.TerminateAsync(id);
        if (!success) return NotFound();
        return NoContent();
    }
}
