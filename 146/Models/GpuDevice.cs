using CloudDesktop.Api.Models.Enums;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace CloudDesktop.Api.Models;

public class GpuDevice
{
    [Key]
    public Guid Id { get; set; }

    [Required]
    [MaxLength(100)]
    public string Name { get; set; } = string.Empty;

    [MaxLength(200)]
    public string? DeviceId { get; set; }

    [MaxLength(100)]
    public string? PciAddress { get; set; }

    [Required]
    public GpuType GpuType { get; set; }

    [Required]
    public GpuStatus Status { get; set; }

    [MaxLength(500)]
    public string? StatusMessage { get; set; }

    public int VramMB { get; set; }

    public int CudaCores { get; set; }

    [MaxLength(50)]
    public string? DriverVersion { get; set; }

    [MaxLength(50)]
    public string? BiosVersion { get; set; }

    public decimal CurrentGpuUtilization { get; set; }

    public decimal CurrentMemoryUtilization { get; set; }

    public decimal Temperature { get; set; }

    public decimal PowerDrawW { get; set; }

    public bool SupportPassthrough { get; set; } = true;

    public int MaxVirtualGpus { get; set; } = 1;

    public int AllocatedVirtualGpus { get; set; } = 0;

    [ForeignKey(nameof(DesktopPool))]
    public Guid? DesktopPoolId { get; set; }

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    public DateTime? UpdatedAt { get; set; }

    public DateTime? LastHealthCheckAt { get; set; }

    public DesktopPool? DesktopPool { get; set; }

    public ICollection<GpuAssignment> GpuAssignments { get; set; } = new List<GpuAssignment>();
}

public class GpuAssignment
{
    [Key]
    public Guid Id { get; set; }

    [Required]
    [ForeignKey(nameof(GpuDevice))]
    public Guid GpuDeviceId { get; set; }

    [Required]
    [ForeignKey(nameof(Desktop))]
    public Guid DesktopId { get; set; }

    public int VramAllocationMB { get; set; }

    public int VirtualFunctionIndex { get; set; }

    [MaxLength(200)]
    public string? VirtualDeviceId { get; set; }

    public bool IsPassthrough { get; set; } = true;

    public DateTime AssignedAt { get; set; } = DateTime.UtcNow;

    public DateTime? ReleasedAt { get; set; }

    public GpuDevice GpuDevice { get; set; } = null!;

    public Desktop Desktop { get; set; } = null!;
}
