using CloudDesktop.Api.Data;
using CloudDesktop.Api.Models;
using CloudDesktop.Api.Models.Enums;
using Microsoft.EntityFrameworkCore;

namespace CloudDesktop.Api.Services;

public interface IGpuService
{
    Task<List<GpuDevice>> GetAllGpusAsync();
    Task<GpuDevice?> GetGpuByIdAsync(Guid id);
    Task<GpuDevice> CreateGpuAsync(GpuDevice gpu);
    Task<GpuDevice?> UpdateGpuAsync(Guid id, GpuDevice gpu);
    Task<bool> DeleteGpuAsync(Guid id);
    Task<bool> AssignGpuToDesktopAsync(Guid gpuId, Guid desktopId, bool isPassthrough = true);
    Task<bool> ReleaseGpuFromDesktopAsync(Guid gpuId, Guid desktopId);
    Task<List<GpuAssignment>> GetGpuAssignmentsByDesktopAsync(Guid desktopId);
    Task<List<GpuDevice>> GetAvailableGpusAsync(Guid? desktopPoolId = null);
    Task<bool> UpdateGpuMetricsAsync(Guid gpuId, decimal utilization, decimal memoryUtilization, decimal temperature, decimal powerDraw);
}

public class GpuService : IGpuService
{
    private readonly ApplicationDbContext _context;

    public GpuService(ApplicationDbContext context)
    {
        _context = context;
    }

    public async Task<List<GpuDevice>> GetAllGpusAsync()
    {
        return await _context.GpuDevices
            .Include(g => g.GpuAssignments)
            .Include(g => g.DesktopPool)
            .ToListAsync();
    }

    public async Task<GpuDevice?> GetGpuByIdAsync(Guid id)
    {
        return await _context.GpuDevices
            .Include(g => g.GpuAssignments)
            .Include(g => g.DesktopPool)
            .FirstOrDefaultAsync(g => g.Id == id);
    }

    public async Task<GpuDevice> CreateGpuAsync(GpuDevice gpu)
    {
        gpu.Id = Guid.NewGuid();
        gpu.CreatedAt = DateTime.UtcNow;
        _context.GpuDevices.Add(gpu);
        await _context.SaveChangesAsync();
        return gpu;
    }

    public async Task<GpuDevice?> UpdateGpuAsync(Guid id, GpuDevice gpu)
    {
        var existingGpu = await _context.GpuDevices.FindAsync(id);
        if (existingGpu == null) return null;

        existingGpu.Name = gpu.Name;
        existingGpu.DeviceId = gpu.DeviceId;
        existingGpu.PciAddress = gpu.PciAddress;
        existingGpu.GpuType = gpu.GpuType;
        existingGpu.Status = gpu.Status;
        existingGpu.StatusMessage = gpu.StatusMessage;
        existingGpu.VramMB = gpu.VramMB;
        existingGpu.CudaCores = gpu.CudaCores;
        existingGpu.DriverVersion = gpu.DriverVersion;
        existingGpu.BiosVersion = gpu.BiosVersion;
        existingGpu.SupportPassthrough = gpu.SupportPassthrough;
        existingGpu.MaxVirtualGpus = gpu.MaxVirtualGpus;
        existingGpu.DesktopPoolId = gpu.DesktopPoolId;
        existingGpu.UpdatedAt = DateTime.UtcNow;

        await _context.SaveChangesAsync();
        return existingGpu;
    }

    public async Task<bool> DeleteGpuAsync(Guid id)
    {
        var gpu = await _context.GpuDevices.FindAsync(id);
        if (gpu == null) return false;

        _context.GpuDevices.Remove(gpu);
        await _context.SaveChangesAsync();
        return true;
    }

    public async Task<bool> AssignGpuToDesktopAsync(Guid gpuId, Guid desktopId, bool isPassthrough = true)
    {
        var gpu = await _context.GpuDevices.FindAsync(gpuId);
        var desktop = await _context.Desktops.FindAsync(desktopId);

        if (gpu == null || desktop == null) return false;
        if (!gpu.SupportPassthrough && isPassthrough) return false;
        if (gpu.AllocatedVirtualGpus >= gpu.MaxVirtualGpus) return false;

        var existingAssignment = await _context.GpuAssignments
            .FirstOrDefaultAsync(ga => ga.GpuDeviceId == gpuId && ga.DesktopId == desktopId && ga.ReleasedAt == null);

        if (existingAssignment != null) return true;

        var assignment = new GpuAssignment
        {
            Id = Guid.NewGuid(),
            GpuDeviceId = gpuId,
            DesktopId = desktopId,
            VramAllocationMB = gpu.VramMB,
            IsPassthrough = isPassthrough,
            AssignedAt = DateTime.UtcNow
        };

        _context.GpuAssignments.Add(assignment);
        gpu.AllocatedVirtualGpus++;
        gpu.UpdatedAt = DateTime.UtcNow;
        desktop.GpuPassthroughEnabled = true;
        desktop.UpdatedAt = DateTime.UtcNow;

        await _context.SaveChangesAsync();
        return true;
    }

    public async Task<bool> ReleaseGpuFromDesktopAsync(Guid gpuId, Guid desktopId)
    {
        var assignment = await _context.GpuAssignments
            .FirstOrDefaultAsync(ga => ga.GpuDeviceId == gpuId && ga.DesktopId == desktopId && ga.ReleasedAt == null);

        if (assignment == null) return false;

        assignment.ReleasedAt = DateTime.UtcNow;

        var gpu = await _context.GpuDevices.FindAsync(gpuId);
        if (gpu != null)
        {
            gpu.AllocatedVirtualGpus--;
            gpu.UpdatedAt = DateTime.UtcNow;
        }

        var desktop = await _context.Desktops.FindAsync(desktopId);
        if (desktop != null)
        {
            var remainingAssignments = await _context.GpuAssignments
                .CountAsync(ga => ga.DesktopId == desktopId && ga.ReleasedAt == null);

            if (remainingAssignments <= 1)
            {
                desktop.GpuPassthroughEnabled = false;
            }
            desktop.UpdatedAt = DateTime.UtcNow;
        }

        await _context.SaveChangesAsync();
        return true;
    }

    public async Task<List<GpuAssignment>> GetGpuAssignmentsByDesktopAsync(Guid desktopId)
    {
        return await _context.GpuAssignments
            .Include(ga => ga.GpuDevice)
            .Where(ga => ga.DesktopId == desktopId && ga.ReleasedAt == null)
            .ToListAsync();
    }

    public async Task<List<GpuDevice>> GetAvailableGpusAsync(Guid? desktopPoolId = null)
    {
        var query = _context.GpuDevices
            .Where(g => g.Status == GpuStatus.Available && g.SupportPassthrough)
            .Where(g => g.AllocatedVirtualGpus < g.MaxVirtualGpus);

        if (desktopPoolId.HasValue)
        {
            query = query.Where(g => g.DesktopPoolId == desktopPoolId.Value || g.DesktopPoolId == null);
        }

        return await query.ToListAsync();
    }

    public async Task<bool> UpdateGpuMetricsAsync(Guid gpuId, decimal utilization, decimal memoryUtilization, decimal temperature, decimal powerDraw)
    {
        var gpu = await _context.GpuDevices.FindAsync(gpuId);
        if (gpu == null) return false;

        gpu.CurrentGpuUtilization = utilization;
        gpu.CurrentMemoryUtilization = memoryUtilization;
        gpu.Temperature = temperature;
        gpu.PowerDrawW = powerDraw;
        gpu.LastHealthCheckAt = DateTime.UtcNow;
        gpu.UpdatedAt = DateTime.UtcNow;

        await _context.SaveChangesAsync();
        return true;
    }
}
