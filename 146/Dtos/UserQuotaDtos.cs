using System.ComponentModel.DataAnnotations;

namespace CloudDesktop.Api.Dtos;

public class CreateUserQuotaDto
{
    [Required]
    public Guid UserId { get; set; }

    [Required]
    public Guid DesktopPoolId { get; set; }

    public int MaxConcurrentSessions { get; set; } = 1;

    public int MaxDailySessionMinutes { get; set; } = 480;

    public int MaxMonthlySessionMinutes { get; set; } = 9600;
}

public class UpdateUserQuotaDto
{
    public int? MaxConcurrentSessions { get; set; }

    public int? MaxDailySessionMinutes { get; set; }

    public int? MaxMonthlySessionMinutes { get; set; }
}

public class UserQuotaDto
{
    public Guid Id { get; set; }
    public Guid UserId { get; set; }
    public Guid DesktopPoolId { get; set; }
    public string Username { get; set; } = string.Empty;
    public string DesktopPoolName { get; set; } = string.Empty;
    public int MaxConcurrentSessions { get; set; }
    public int CurrentActiveSessions { get; set; }
    public int MaxDailySessionMinutes { get; set; }
    public int TodayUsedMinutes { get; set; }
    public int MaxMonthlySessionMinutes { get; set; }
    public int MonthUsedMinutes { get; set; }
    public DateTime CreatedAt { get; set; }
}

public class ConnectionRequestDto
{
    [Required]
    public Guid UserId { get; set; }

    [Required]
    public Guid DesktopPoolId { get; set; }

    public Guid? PreferredDesktopId { get; set; }

    [MaxLength(50)]
    public string? ClientIpAddress { get; set; }
}

public class ConnectionResponseDto
{
    public bool Success { get; set; }
    public string? Message { get; set; }
    public Guid? SessionId { get; set; }
    public Guid? DesktopId { get; set; }
    public string? DesktopName { get; set; }
    public string? IpAddress { get; set; }
    public int? Port { get; set; }
    public string? Protocol { get; set; }
    public string? ConnectionString { get; set; }
}
