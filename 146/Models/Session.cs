using CloudDesktop.Api.Models.Enums;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace CloudDesktop.Api.Models;

public class Session
{
    [Key]
    public Guid Id { get; set; }

    [Required]
    [ForeignKey(nameof(Desktop))]
    public Guid DesktopId { get; set; }

    [Required]
    [ForeignKey(nameof(User))]
    public Guid UserId { get; set; }

    [MaxLength(100)]
    public string? SessionName { get; set; }

    [Required]
    public SessionStatus Status { get; set; }

    [MaxLength(50)]
    public string? ClientIpAddress { get; set; }

    [MaxLength(100)]
    public string? ClientHostName { get; set; }

    public ConnectionProtocol Protocol { get; set; }

    public int? ProtocolPort { get; set; }

    [MaxLength(500)]
    public string? ConnectionString { get; set; }

    public DateTime? ConnectedAt { get; set; }

    public DateTime? DisconnectedAt { get; set; }

    public TimeSpan? Duration { get; set; }

    [MaxLength(500)]
    public string? ErrorMessage { get; set; }

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    public DateTime? UpdatedAt { get; set; }

    public Desktop Desktop { get; set; } = null!;

    public User User { get; set; } = null!;
}
