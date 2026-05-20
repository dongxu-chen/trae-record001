using CloudDesktop.Api.Dtos;
using CloudDesktop.Api.Services;
using Microsoft.AspNetCore.Mvc;

namespace CloudDesktop.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class DesktopPoolsController : ControllerBase
{
    private readonly IDesktopPoolService _desktopPoolService;

    public DesktopPoolsController(IDesktopPoolService desktopPoolService)
    {
        _desktopPoolService = desktopPoolService;
    }

    [HttpGet]
    public async Task<ActionResult<List<DesktopPoolDto>>> GetAll()
    {
        var pools = await _desktopPoolService.GetAllAsync();
        return Ok(pools);
    }

    [HttpGet("{id}")]
    public async Task<ActionResult<DesktopPoolDetailDto>> GetById(Guid id)
    {
        var pool = await _desktopPoolService.GetByIdAsync(id);
        if (pool == null) return NotFound();
        return Ok(pool);
    }

    [HttpPost]
    public async Task<ActionResult<DesktopPoolDto>> Create(CreateDesktopPoolDto dto)
    {
        var pool = await _desktopPoolService.CreateAsync(dto);
        return CreatedAtAction(nameof(GetById), new { id = pool.Id }, pool);
    }

    [HttpPut("{id}")]
    public async Task<ActionResult<DesktopPoolDto>> Update(Guid id, UpdateDesktopPoolDto dto)
    {
        var pool = await _desktopPoolService.UpdateAsync(id, dto);
        if (pool == null) return NotFound();
        return Ok(pool);
    }

    [HttpDelete("{id}")]
    public async Task<IActionResult> Delete(Guid id)
    {
        var success = await _desktopPoolService.DeleteAsync(id);
        if (!success) return NotFound();
        return NoContent();
    }

    [HttpPost("{id}/scale-up")]
    public async Task<ActionResult<int>> ScaleUp(Guid id, [FromQuery] int count = 1)
    {
        try
        {
            var createdCount = await _desktopPoolService.ScaleUpAsync(id, count);
            return Ok(new { CreatedDesktops = createdCount });
        }
        catch (InvalidOperationException ex)
        {
            return BadRequest(ex.Message);
        }
    }

    [HttpPost("{id}/scale-down")]
    public async Task<ActionResult<int>> ScaleDown(Guid id, [FromQuery] int count = 1)
    {
        try
        {
            var removedCount = await _desktopPoolService.ScaleDownAsync(id, count);
            return Ok(new { RemovedDesktops = removedCount });
        }
        catch (InvalidOperationException ex)
        {
            return BadRequest(ex.Message);
        }
    }

    [HttpPost("{id}/cleanup-orphaned-sessions")]
    public async Task<ActionResult<int>> CleanupOrphanedSessions(Guid id)
    {
        try
        {
            var cleanedCount = await _desktopPoolService.CleanupOrphanedSessionsAsync(id);
            return Ok(new { CleanedSessions = cleanedCount });
        }
        catch (InvalidOperationException ex)
        {
            return BadRequest(ex.Message);
        }
    }

    [HttpGet("{id}/available-capacity")]
    public async Task<ActionResult<int>> GetAvailableCapacity(Guid id)
    {
        try
        {
            var capacity = await _desktopPoolService.GetAvailableCapacityAsync(id);
            return Ok(new { AvailableCapacity = capacity });
        }
        catch (InvalidOperationException ex)
        {
            return BadRequest(ex.Message);
        }
    }
}
