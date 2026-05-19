using CloudDesktop.Api.Data;
using CloudDesktop.Api.Dtos;
using CloudDesktop.Api.Models;
using CloudDesktop.Api.Models.Enums;
using Microsoft.EntityFrameworkCore;

namespace CloudDesktop.Api.Services;

public interface IConnectionBrokerService
{
    Task<ConnectionResponseDto> RequestConnectionAsync(ConnectionRequestDto request);
    Task<Desktop?> FindAvailableDesktopAsync(Guid desktopPoolId);
    Task<bool> ValidateUserQuotaAsync(Guid userId, Guid desktopPoolId);
}

public class ConnectionBrokerService : IConnectionBrokerService
{
    private readonly ApplicationDbContext _context;
    private readonly IUserQuotaService _quotaService;

    public ConnectionBrokerService(ApplicationDbContext context, IUserQuotaService quotaService)
    {
        _context = context;
        _quotaService = quotaService;
    }

    public async Task<ConnectionResponseDto> RequestConnectionAsync(ConnectionRequestDto request)
    {
        var user = await _context.Users.FindAsync(request.UserId);
        if (user == null)
        {
            return new ConnectionResponseDto
            {
                Success = false,
                Message = "User not found"
            };
        }

        if (!user.IsActive)
        {
            return new ConnectionResponseDto
            {
                Success = false,
                Message = "User account is disabled"
            };
        }

        var desktopPool = await _context.DesktopPools.FindAsync(request.DesktopPoolId);
        if (desktopPool == null)
        {
            return new ConnectionResponseDto
            {
                Success = false,
                Message = "Desktop pool not found"
            };
        }

        if (desktopPool.Status != DesktopPoolStatus.Available)
        {
            return new ConnectionResponseDto
            {
                Success = false,
                Message = $"Desktop pool is {desktopPool.Status}"
            };
        }

        var hasQuota = await ValidateUserQuotaAsync(request.UserId, request.DesktopPoolId);
        if (!hasQuota)
        {
            return new ConnectionResponseDto
            {
                Success = false,
                Message = "User has exceeded their session quota"
            };
        }

        var desktop = await FindAvailableDesktopAsync(request.DesktopPoolId);
        if (desktop == null)
        {
            return new ConnectionResponseDto
            {
                Success = false,
                Message = "No available desktops in the pool"
            };
        }

        var session = new Session
        {
            Id = Guid.NewGuid(),
            DesktopId = desktop.Id,
            UserId = request.UserId,
            SessionName = $"{user.Username}-{DateTime.UtcNow:yyyyMMddHHmmss}",
            Status = SessionStatus.Connecting,
            ClientIpAddress = request.ClientIpAddress,
            Protocol = desktop.Protocol,
            ProtocolPort = desktop.Port,
            ConnectionString = GenerateConnectionString(desktop),
            CreatedAt = DateTime.UtcNow
        };

        desktop.Status = DesktopStatus.InUse;
        desktop.UpdatedAt = DateTime.UtcNow;

        _context.Sessions.Add(session);
        await _context.SaveChangesAsync();

        await _quotaService.IncrementSessionUsageAsync(request.UserId, request.DesktopPoolId);

        return new ConnectionResponseDto
        {
            Success = true,
            Message = "Connection successful",
            SessionId = session.Id,
            DesktopId = desktop.Id,
            DesktopName = desktop.Name,
            IpAddress = desktop.IpAddress,
            Port = desktop.Port,
            Protocol = desktop.Protocol.ToString(),
            ConnectionString = session.ConnectionString
        };
    }

    public async Task<Desktop?> FindAvailableDesktopAsync(Guid desktopPoolId)
    {
        return await _context.Desktops
            .Where(d => d.DesktopPoolId == desktopPoolId && d.Status == DesktopStatus.Available)
            .GroupJoin(
                _context.Sessions.Where(s => s.Status == SessionStatus.Active),
                d => d.Id,
                s => s.DesktopId,
                (d, sessions) => new { Desktop = d, SessionCount = sessions.Count() }
            )
            .OrderBy(x => x.SessionCount)
            .ThenBy(x => x.Desktop.LastHeartbeat ?? x.Desktop.CreatedAt)
            .Select(x => x.Desktop)
            .FirstOrDefaultAsync();
    }

    public async Task<bool> ValidateUserQuotaAsync(Guid userId, Guid desktopPoolId)
    {
        var pool = await _context.DesktopPools.FindAsync(desktopPoolId);
        if (pool == null)
            return false;

        if (pool.Status != DesktopPoolStatus.Available)
            return false;

        var availableDesktops = await _context.Desktops
            .CountAsync(d => d.DesktopPoolId == desktopPoolId && d.Status == DesktopStatus.Available);

        if (availableDesktops == 0)
            return false;

        var availablePorts = await _context.PortAllocations
            .CountAsync(p => p.DesktopPoolId == desktopPoolId && !p.IsAllocated);

        if (availablePorts == 0)
            return false;

        var quota = await _context.UserQuotas
            .FirstOrDefaultAsync(q => q.UserId == userId && q.DesktopPoolId == desktopPoolId);

        if (quota == null)
        {
            var defaultQuota = await _context.UserQuotas
                .OrderBy(q => q.CreatedAt)
                .FirstOrDefaultAsync(q => q.UserId == userId);

            if (defaultQuota == null)
                return true;

            quota = defaultQuota;
        }

        var activeSessions = await _context.Sessions
            .Where(s => s.UserId == userId
                && s.Desktop.DesktopPoolId == desktopPoolId
                && s.Status == SessionStatus.Active)
            .CountAsync();

        if (activeSessions >= quota.MaxConcurrentSessions)
            return false;

        if (quota.TodayUsedMinutes >= quota.MaxDailySessionMinutes)
            return false;

        return true;
    }

    private string GenerateConnectionString(Desktop desktop)
    {
        var protocol = desktop.Protocol.ToString().ToLower();
        return $"{protocol}://{desktop.IpAddress}:{desktop.Port}";
    }
}
