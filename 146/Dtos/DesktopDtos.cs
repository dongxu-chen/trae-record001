using CloudDesktop.Api.Models.Enums;
using System.ComponentModel.DataAnnotations;

namespace CloudDesktop.Api.Dtos;

public class CreateDesktopDto
{
    [Required]
    public Guid DesktopPoolId { get; set; }

    [Required]
    [MaxLength(100)]
    public string Name { get; set; } = string.Empty;

    [MaxLength(50)]
    public string? ComputerName { get; set; }

    [MaxLength(50)]
    public string? IpAddress { get; set; }

    public int Port { get; set; } = 3389;

    public ConnectionProtocol Protocol { get; set; } = ConnectionProtocol.RDP;

    public int CpuCores { get; set; } = 2;

    public int MemoryGB { get; set; } = 4;

    public int StorageGB { get; set; } = 50;
}

public class UpdateDesktopDto
{
    [MaxLength(100)]
    public string? Name { get; set; }

    [MaxLength(50)]
    public string? ComputerName { get; set; }

    [MaxLength(50)]
    public string? IpAddress { get; set; }

    public int? Port { get; set; }

    public DesktopStatus? Status { get; set; }
}

public class DesktopDto
{
    public Guid Id { get; set; }
    public Guid DesktopPoolId { get; set; }
    public string Name { get; set; } = string.Empty;
    public string? ComputerName { get; set; }
    public string? IpAddress { get; set; }
    public int Port { get; set; }
    public DesktopStatus Status { get; set; }
    public string? StatusMessage { get; set; }
    public ConnectionProtocol Protocol { get; set; }
    public int CpuCores { get; set; }
    public int MemoryGB { get; set; }
    public int StorageGB { get; set; }
    public DateTime? LastHeartbeat { get; set; }
    public DateTime CreatedAt { get; set; }
}
