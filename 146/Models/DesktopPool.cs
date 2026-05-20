using CloudDesktop.Api.Models.Enums;
using System.ComponentModel.DataAnnotations;

namespace CloudDesktop.Api.Models;

public class DesktopPool
{
    [Key]
    public Guid Id { get; set; }

    [Required]
    [MaxLength(100)]
    public string Name { get; set; } = string.Empty;

    [MaxLength(500)]
    public string? Description { get; set; }

    [Required]
    public DesktopPoolStatus Status { get; set; }

    [Required]
    public int MaxDesktops { get; set; }

    public int CurrentDesktops { get; set; }

    [Required]
    public ConnectionProtocol DefaultProtocol { get; set; }

    public int DefaultPort { get; set; } = 3389;

    public int PortRangeStart { get; set; } = 3389;

    public int PortRangeEnd { get; set; } = 3489;

    [MaxLength(200)]
    public string? ImageTemplate { get; set; }

    public int CpuCores { get; set; }

    public int MemoryGB { get; set; }

    public int StorageGB { get; set; }

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    public DateTime? UpdatedAt { get; set; }

    public ICollection<Desktop> Desktops { get; set; } = new List<Desktop>();

    public ICollection<UserQuota> UserQuotas { get; set; } = new List<UserQuota>();

    public ICollection<PortAllocation> PortAllocations { get; set; } = new List<PortAllocation>();
}
