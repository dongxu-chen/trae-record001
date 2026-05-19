using CloudDesktop.Api.Models.Enums;
using System.ComponentModel.DataAnnotations;

namespace CloudDesktop.Api.Dtos;

public class CreateSessionDto
{
    [Required]
    public Guid UserId { get; set; }

    [Required]
    public Guid DesktopPoolId { get; set; }

    public Guid? PreferredDesktopId { get; set; }

    [MaxLength(50)]
    public string? ClientIpAddress { get; set; }

    [MaxLength(100)]
    public string? ClientHostName { get; set; }
}

public class UpdateSessionDto
{
    public SessionStatus? Status { get; set; }

    public string? ErrorMessage { get; set; }
}

public class SessionDto
{
    public Guid Id { get; set; }
    public Guid DesktopId { get; set; }
    public Guid UserId { get; set; }
    public string? SessionName { get; set; }
    public SessionStatus Status { get; set; }
    public string? ClientIpAddress { get; set; }
    public string? ClientHostName { get; set; }
    public ConnectionProtocol Protocol { get; set; }
    public int? ProtocolPort { get; set; }
    public DateTime? ConnectedAt { get; set; }
    public DateTime? DisconnectedAt { get; set; }
    public TimeSpan? Duration { get; set; }
    public string? ErrorMessage { get; set; }
    public DateTime CreatedAt { get; set; }
}

public class SessionDetailDto : SessionDto
{
    public string DesktopName { get; set; } = string.Empty;
    public string? DesktopIpAddress { get; set; }
    public string Username { get; set; } = string.Empty;
    public string? UserFullName { get; set; }
}
