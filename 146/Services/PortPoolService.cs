using CloudDesktop.Api.Data;
using CloudDesktop.Api.Models;
using Microsoft.EntityFrameworkCore;

namespace CloudDesktop.Api.Services;

public interface IPortPoolService
{
    Task<int?> AllocatePortAsync(Guid desktopPoolId, Guid? desktopId = null, Guid? sessionId = null, string? allocatedTo = null);
    Task<bool> ReleasePortAsync(Guid desktopPoolId, int portNumber);
    Task<bool> ReleasePortByDesktopAsync(Guid desktopId);
    Task<bool> ReleasePortBySessionAsync(Guid sessionId);
    Task InitializePortPoolAsync(Guid desktopPoolId);
    Task<int> GetAvailablePortCountAsync(Guid desktopPoolId);
    Task<int> GetAllocatedPortCountAsync(Guid desktopPoolId);
    Task CleanupOrphanedPortsAsync(Guid desktopPoolId);
}

public class PortPoolService : IPortPoolService
{
    private readonly ApplicationDbContext _context;

    public PortPoolService(ApplicationDbContext context)
    {
        _context = context;
    }

    public async Task InitializePortPoolAsync(Guid desktopPoolId)
    {
        var pool = await _context.DesktopPools.FindAsync(desktopPoolId);
        if (pool == null)
            throw new InvalidOperationException("Desktop pool not found");

        var existingAllocations = await _context.PortAllocations
            .Where(p => p.DesktopPoolId == desktopPoolId)
            .Select(p => p.PortNumber)
            .ToListAsync();

        var allocations = new List<PortAllocation>();
        for (int port = pool.PortRangeStart; port <= pool.PortRangeEnd; port++)
        {
            if (!existingAllocations.Contains(port))
            {
                allocations.Add(new PortAllocation
                {
                    Id = Guid.NewGuid(),
                    DesktopPoolId = desktopPoolId,
                    PortNumber = port,
                    IsAllocated = false,
                    CreatedAt = DateTime.UtcNow
                });
            }
        }

        if (allocations.Any())
        {
            _context.PortAllocations.AddRange(allocations);
            await _context.SaveChangesAsync();
        }
    }

    public async Task<int?> AllocatePortAsync(Guid desktopPoolId, Guid? desktopId = null, Guid? sessionId = null, string? allocatedTo = null)
    {
        var pool = await _context.DesktopPools.FindAsync(desktopPoolId);
        if (pool == null)
            throw new InvalidOperationException("Desktop pool not found");

        var availablePort = await _context.PortAllocations
            .Where(p => p.DesktopPoolId == desktopPoolId && !p.IsAllocated)
            .OrderBy(p => p.PortNumber)
            .FirstOrDefaultAsync();

        if (availablePort == null)
            return null;

        availablePort.IsAllocated = true;
        availablePort.AllocatedAt = DateTime.UtcNow;
        availablePort.DesktopId = desktopId;
        availablePort.SessionId = sessionId;
        availablePort.AllocatedTo = allocatedTo;

        await _context.SaveChangesAsync();
        return availablePort.PortNumber;
    }

    public async Task<bool> ReleasePortAsync(Guid desktopPoolId, int portNumber)
    {
        var allocation = await _context.PortAllocations
            .FirstOrDefaultAsync(p => p.DesktopPoolId == desktopPoolId && p.PortNumber == portNumber && p.IsAllocated);

        if (allocation == null)
            return false;

        allocation.IsAllocated = false;
        allocation.ReleasedAt = DateTime.UtcNow;
        allocation.DesktopId = null;
        allocation.SessionId = null;
        allocation.AllocatedTo = null;

        await _context.SaveChangesAsync();
        return true;
    }

    public async Task<bool> ReleasePortByDesktopAsync(Guid desktopId)
    {
        var allocation = await _context.PortAllocations
            .FirstOrDefaultAsync(p => p.DesktopId == desktopId && p.IsAllocated);

        if (allocation == null)
            return false;

        allocation.IsAllocated = false;
        allocation.ReleasedAt = DateTime.UtcNow;
        allocation.DesktopId = null;
        allocation.SessionId = null;
        allocation.AllocatedTo = null;

        await _context.SaveChangesAsync();
        return true;
    }

    public async Task<bool> ReleasePortBySessionAsync(Guid sessionId)
    {
        var allocation = await _context.PortAllocations
            .FirstOrDefaultAsync(p => p.SessionId == sessionId && p.IsAllocated);

        if (allocation == null)
            return false;

        allocation.IsAllocated = false;
        allocation.ReleasedAt = DateTime.UtcNow;
        allocation.DesktopId = null;
        allocation.SessionId = null;
        allocation.AllocatedTo = null;

        await _context.SaveChangesAsync();
        return true;
    }

    public async Task<int> GetAvailablePortCountAsync(Guid desktopPoolId)
    {
        return await _context.PortAllocations
            .CountAsync(p => p.DesktopPoolId == desktopPoolId && !p.IsAllocated);
    }

    public async Task<int> GetAllocatedPortCountAsync(Guid desktopPoolId)
    {
        return await _context.PortAllocations
            .CountAsync(p => p.DesktopPoolId == desktopPoolId && p.IsAllocated);
    }

    public async Task CleanupOrphanedPortsAsync(Guid desktopPoolId)
    {
        var orphanedAllocations = await _context.PortAllocations
            .Where(p => p.DesktopPoolId == desktopPoolId && p.IsAllocated)
            .Where(p => (p.DesktopId != null && !_context.Desktops.Any(d => d.Id == p.DesktopId)) ||
                       (p.SessionId != null && !_context.Sessions.Any(s => s.Id == p.SessionId)))
            .ToListAsync();

        foreach (var allocation in orphanedAllocations)
        {
            allocation.IsAllocated = false;
            allocation.ReleasedAt = DateTime.UtcNow;
            allocation.DesktopId = null;
            allocation.SessionId = null;
            allocation.AllocatedTo = null;
        }

        await _context.SaveChangesAsync();
    }
}
