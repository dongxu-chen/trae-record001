using CloudDesktop.Api.Dtos;
using CloudDesktop.Api.Services;
using Microsoft.AspNetCore.Mvc;

namespace CloudDesktop.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class UserQuotasController : ControllerBase
{
    private readonly IUserQuotaService _quotaService;

    public UserQuotasController(IUserQuotaService quotaService)
    {
        _quotaService = quotaService;
    }

    [HttpGet]
    public async Task<ActionResult<List<UserQuotaDto>>> GetAll(
        [FromQuery] Guid? userId = null)
    {
        var quotas = await _quotaService.GetAllAsync(userId);
        return Ok(quotas);
    }

    [HttpGet("{id}")]
    public async Task<ActionResult<UserQuotaDto>> GetById(Guid id)
    {
        var quota = await _quotaService.GetByIdAsync(id);
        if (quota == null) return NotFound();
        return Ok(quota);
    }

    [HttpPost]
    public async Task<ActionResult<UserQuotaDto>> Create(CreateUserQuotaDto dto)
    {
        try
        {
            var quota = await _quotaService.CreateAsync(dto);
            return CreatedAtAction(nameof(GetById), new { id = quota.Id }, quota);
        }
        catch (InvalidOperationException ex)
        {
            return BadRequest(ex.Message);
        }
    }

    [HttpPut("{id}")]
    public async Task<ActionResult<UserQuotaDto>> Update(Guid id, UpdateUserQuotaDto dto)
    {
        var quota = await _quotaService.UpdateAsync(id, dto);
        if (quota == null) return NotFound();
        return Ok(quota);
    }

    [HttpDelete("{id}")]
    public async Task<IActionResult> Delete(Guid id)
    {
        var success = await _quotaService.DeleteAsync(id);
        if (!success) return NotFound();
        return NoContent();
    }

    [HttpPost("reset-daily")]
    public async Task<IActionResult> ResetDailyUsage()
    {
        await _quotaService.ResetDailyUsageAsync();
        return Ok();
    }

    [HttpPost("reset-monthly")]
    public async Task<IActionResult> ResetMonthlyUsage()
    {
        await _quotaService.ResetMonthlyUsageAsync();
        return Ok();
    }
}
