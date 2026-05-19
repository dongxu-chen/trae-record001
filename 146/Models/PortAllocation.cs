using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace CloudDesktop.Api.Models;

public class PortAllocation
{
    [Key]
    public Guid Id { get; set; }

    [Required]
    public int PortNumber { get; set; }

    [Required]
    [ForeignKey(nameof(DesktopPool))]
    public Guid DesktopPoolId { get; set; }

    [ForeignKey(nameof(Desktop))]
    public Guid? DesktopId { get; set; }

    [ForeignKey(nameof(Session))]
    public Guid? SessionId { get; set; }

    public bool IsAllocated { get; set; }

    public DateTime? AllocatedAt { get; set; }

    public DateTime? ReleasedAt { get; set; }

    [MaxLength(200)]
    public string? AllocatedTo { get; set; }

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    public DesktopPool DesktopPool { get; set; } = null!;

    public Desktop? Desktop { get; set; }

    public Session? Session { get; set; }
}
