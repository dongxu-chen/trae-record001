using CloudDesktop.Api.Dtos;
using CloudDesktop.Api.Services;
using Microsoft.AspNetCore.Mvc;

namespace CloudDesktop.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class ConnectionBrokerController : ControllerBase
{
    private readonly IConnectionBrokerService _brokerService;

    public ConnectionBrokerController(IConnectionBrokerService brokerService)
    {
        _brokerService = brokerService;
    }

    [HttpPost("connect")]
    public async Task<ActionResult<ConnectionResponseDto>> RequestConnection(
        [FromBody] ConnectionRequestDto request)
    {
        var response = await _brokerService.RequestConnectionAsync(request);
        if (!response.Success)
            return BadRequest(response);
        return Ok(response);
    }

    [HttpGet("available-desktops/{desktopPoolId}")]
    public async Task<IActionResult> CheckAvailableDesktops(Guid desktopPoolId)
    {
        var desktop = await _brokerService.FindAvailableDesktopAsync(desktopPoolId);
        if (desktop == null)
            return NotFound("No available desktops in the pool");
        return Ok(new { desktop.Id, desktop.Name, desktop.IpAddress, desktop.Port });
    }

    [HttpGet("validate-quota")]
    public async Task<IActionResult> ValidateQuota(
        [FromQuery] Guid userId,
        [FromQuery] Guid desktopPoolId)
    {
        var isValid = await _brokerService.ValidateUserQuotaAsync(userId, desktopPoolId);
        return Ok(new { Valid = isValid });
    }
}
