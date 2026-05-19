using CloudDesktop.Api.Models.Enums;
using System.ComponentModel.DataAnnotations;

namespace CloudDesktop.Api.Dtos;

public class CreateDesktopPoolDto
{
    [Required]
    [MaxLength(100)]
    public string Name { get; set; } = string.Empty;

    [MaxLength(500)]
    public string? Description { get; set; }

    [Required]
    public int MaxDesktops { get; set; }

    [Required]
    public ConnectionProtocol DefaultProtocol { get; set; }

    public int DefaultPort { get; set; } = 3389;

    public int PortRangeStart { get; set; } = 3389;

    public int PortRangeEnd { get; set; } = 3489;

    public string? ImageTemplate { get; set; }

    public int CpuCores { get; set; } = 2;

    public int MemoryGB { get; set; } = 4;

    public int StorageGB { get; set; } = 50;
}

public class UpdateDesktopPoolDto
{
    [MaxLength(100)]
    public string? Name { get; set; }

    [MaxLength(500)]
    public string? Description { get; set; }

    public DesktopPoolStatus? Status { get; set; }

    public int? MaxDesktops { get; set; }

    public ConnectionProtocol? DefaultProtocol { get; set; }

    public int? DefaultPort { get; set; }

    public int? PortRangeStart { get; set; }

    public int? PortRangeEnd { get; set; }
}

public class DesktopPoolDto
{
    public Guid Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string? Description { get; set; }
    public DesktopPoolStatus Status { get; set; }
    public int MaxDesktops { get; set; }
    public int CurrentDesktops { get; set; }
    public int AvailableCapacity { get; set; }
    public ConnectionProtocol DefaultProtocol { get; set; }
    public int DefaultPort { get; set; }
    public int PortRangeStart { get; set; }
    public int PortRangeEnd { get; set; }
    public int AvailablePorts { get; set; }
    public int CpuCores { get; set; }
    public int MemoryGB { get; set; }
    public int StorageGB { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime? UpdatedAt { get; set; }
}

public class DesktopPoolDetailDto : DesktopPoolDto
{
    public List<DesktopDto> Desktops { get; set; } = new();
}
