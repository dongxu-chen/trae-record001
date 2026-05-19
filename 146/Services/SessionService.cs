using CloudDesktop.Api.Data;
using CloudDesktop.Api.Dtos;
using CloudDesktop.Api.Models;
using CloudDesktop.Api.Models.Enums;
using Microsoft.EntityFrameworkCore;

namespace CloudDesktop.Api.Services;

public interface ISessionService
{
    Task<List<SessionDetailDto>> GetAllAsync(Guid? userId = null, Guid? desktopPoolId = null);
    Task<SessionDetailDto?> GetByIdAsync(Guid id);
    Task<SessionDto> CreateAsync(CreateSessionDto dto);
    Task<SessionDto?> UpdateAsync(Guid id, UpdateSessionDto dto);
    Task<bool> TerminateAsync(Guid id);
}

public class SessionService : ISessionService
{
    private readonly ApplicationDbContext _context;

    public SessionService(ApplicationDbContext context)
    {
        _context = context;
    }

    public async Task<List<SessionDetailDto>> GetAllAsync(Guid? userId = null, Guid? desktopPoolId = null)
    {
        var query = _context.Sessions
            .Include(s => s.Desktop)
            .Include(s => s.User)
            .AsQueryable();

        if (userId.HasValue)
            query = query.Where(s => s.UserId == userId.Value);

        if (desktopPoolId.HasValue)
            query = query.Where(s => s.Desktop.DesktopPoolId == desktopPoolId.Value);

        return await query
            .OrderByDescending(s => s.CreatedAt)
            .Select(s => new SessionDetailDto
            {
                Id = s.Id,
                DesktopId = s.DesktopId,
                UserId = s.UserId,
                SessionName = s.SessionName,
                Status = s.Status,
                ClientIpAddress = s.ClientIpAddress,
                ClientHostName = s.ClientHostName,
                Protocol = s.Protocol,
                ProtocolPort = s.ProtocolPort,
                ConnectedAt = s.ConnectedAt,
                DisconnectedAt = s.DisconnectedAt,
                Duration = s.Duration,
                ErrorMessage = s.ErrorMessage,
                CreatedAt = s.CreatedAt,
                DesktopName = s.Desktop.Name,
                DesktopIpAddress = s.Desktop.IpAddress,
                Username = s.User.Username,
                UserFullName = s.User.FullName
            })
            .ToListAsync();
    }

    public async Task<SessionDetailDto?> GetByIdAsync(Guid id)
    {
        return await _context.Sessions
            .Include(s => s.Desktop)
            .Include(s => s.User)
            .Where(s => s.Id == id)
            .Select(s => new SessionDetailDto
            {
                Id = s.Id,
                DesktopId = s.DesktopId,
                UserId = s.UserId,
                SessionName = s.SessionName,
                Status = s.Status,
                ClientIpAddress = s.ClientIpAddress,
                ClientHostName = s.ClientHostName,
                Protocol = s.Protocol,
                ProtocolPort = s.ProtocolPort,
                ConnectedAt = s.ConnectedAt,
                DisconnectedAt = s.DisconnectedAt,
                Duration = s.Duration,
                ErrorMessage = s.ErrorMessage,
                CreatedAt = s.CreatedAt,
                DesktopName = s.Desktop.Name,
                DesktopIpAddress = s.Desktop.IpAddress,
                Username = s.User.Username,
                UserFullName = s.User.FullName
            })
            .FirstOrDefaultAsync();
    }

    public async Task<SessionDto> CreateAsync(CreateSessionDto dto)
    {
        var desktop = await GetAvailableDesktopAsync(dto.DesktopPoolId, dto.PreferredDesktopId);
        if (desktop == null)
            throw new InvalidOperationException("No available desktop found in the specified pool.");

        var user = await _context.Users.FindAsync(dto.UserId);
        if (user == null)
            throw new InvalidOperationException("User not found.");

        var session = new Session
        {
            Id = Guid.NewGuid(),
            DesktopId = desktop.Id,
            UserId = dto.UserId,
            SessionName = $"{user.Username}-{DateTime.UtcNow:yyyyMMddHHmmss}",
            Status = SessionStatus.Connecting,
            ClientIpAddress = dto.ClientIpAddress,
            ClientHostName = dto.ClientHostName,
            Protocol = desktop.Protocol,
            ProtocolPort = desktop.Port,
            ConnectionString = GenerateConnectionString(desktop),
            CreatedAt = DateTime.UtcNow
        };

        desktop.Status = DesktopStatus.InUse;
        desktop.UpdatedAt = DateTime.UtcNow;

        _context.Sessions.Add(session);
        await _context.SaveChangesAsync();

        return new SessionDto
        {
            Id = session.Id,
            DesktopId = session.DesktopId,
            UserId = session.UserId,
            SessionName = session.SessionName,
            Status = session.Status,
            ClientIpAddress = session.ClientIpAddress,
            ClientHostName = session.ClientHostName,
            Protocol = session.Protocol,
            ProtocolPort = session.ProtocolPort,
            CreatedAt = session.CreatedAt
        };
    }

    public async Task<SessionDto?> UpdateAsync(Guid id, UpdateSessionDto dto)
    {
        var session = await _context.Sessions.FindAsync(id);
        if (session == null) return null;

        if (dto.Status.HasValue)
        {
            session.Status = dto.Status.Value;

            if (dto.Status.Value == SessionStatus.Active && !session.ConnectedAt.HasValue)
            {
                session.ConnectedAt = DateTime.UtcNow;
            }

            if (dto.Status.Value is SessionStatus.Disconnected or SessionStatus.LoggedOff)
            {
                session.DisconnectedAt = DateTime.UtcNow;
                if (session.ConnectedAt.HasValue)
                {
                    session.Duration = session.DisconnectedAt - session.ConnectedAt;
                }

                var desktop = await _context.Desktops.FindAsync(session.DesktopId);
                if (desktop != null)
                {
                    desktop.Status = DesktopStatus.Available;
                    desktop.UpdatedAt = DateTime.UtcNow;
                }
            }
        }

        if (!string.IsNullOrEmpty(dto.ErrorMessage))
            session.ErrorMessage = dto.ErrorMessage;

        session.UpdatedAt = DateTime.UtcNow;
        await _context.SaveChangesAsync();

        return new SessionDto
        {
            Id = session.Id,
            DesktopId = session.DesktopId,
            UserId = session.UserId,
            SessionName = session.SessionName,
            Status = session.Status,
            ClientIpAddress = session.ClientIpAddress,
            ClientHostName = session.ClientHostName,
            Protocol = session.Protocol,
            ProtocolPort = session.ProtocolPort,
            ConnectedAt = session.ConnectedAt,
            DisconnectedAt = session.DisconnectedAt,
            Duration = session.Duration,
            ErrorMessage = session.ErrorMessage,
            CreatedAt = session.CreatedAt
        };
    }

    public async Task<bool> TerminateAsync(Guid id)
    {
        var session = await _context.Sessions.FindAsync(id);
        if (session == null) return false;

        session.Status = SessionStatus.LoggedOff;
        session.DisconnectedAt = DateTime.UtcNow;
        if (session.ConnectedAt.HasValue)
        {
            session.Duration = session.DisconnectedAt - session.ConnectedAt;
        }
        session.UpdatedAt = DateTime.UtcNow;

        var desktop = await _context.Desktops.FindAsync(session.DesktopId);
        if (desktop != null)
        {
            desktop.Status = DesktopStatus.Available;
            desktop.UpdatedAt = DateTime.UtcNow;
        }

        await _context.SaveChangesAsync();
        return true;
    }

    private async Task<Desktop?> GetAvailableDesktopAsync(Guid desktopPoolId, Guid? preferredDesktopId)
    {
        if (preferredDesktopId.HasValue)
        {
            var preferred = await _context.Desktops
                .FirstOrDefaultAsync(d => d.Id == preferredDesktopId.Value
                    && d.DesktopPoolId == desktopPoolId
                    && d.Status == DesktopStatus.Available);

            if (preferred != null) return preferred;
        }

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

    private string GenerateConnectionString(Desktop desktop)
    {
        return desktop.Protocol switch
        {
            ConnectionProtocol.RDP => $"rdp://{desktop.IpAddress}:{desktop.Port}",
            ConnectionProtocol.VNC => $"vnc://{desktop.IpAddress}:{desktop.Port}",
            ConnectionProtocol.SPICE => $"spice://{desktop.IpAddress}:{desktop.Port}",
            _ => $"{desktop.IpAddress}:{desktop.Port}"
        };
    }
}
