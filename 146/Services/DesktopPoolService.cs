using CloudDesktop.Api.Data;
using CloudDesktop.Api.Dtos;
using CloudDesktop.Api.Models;
using CloudDesktop.Api.Models.Enums;
using Microsoft.EntityFrameworkCore;

namespace CloudDesktop.Api.Services;

public interface IDesktopPoolService
{
    Task<List<DesktopPoolDto>> GetAllAsync();
    Task<DesktopPoolDetailDto?> GetByIdAsync(Guid id);
    Task<DesktopPoolDto> CreateAsync(CreateDesktopPoolDto dto);
    Task<DesktopPoolDto?> UpdateAsync(Guid id, UpdateDesktopPoolDto dto);
    Task<bool> DeleteAsync(Guid id);
    Task<int> ScaleUpAsync(Guid desktopPoolId, int count);
    Task<int> ScaleDownAsync(Guid desktopPoolId, int count);
    Task<int> CleanupOrphanedSessionsAsync(Guid desktopPoolId);
    Task<int> GetAvailableCapacityAsync(Guid desktopPoolId);
}

public class DesktopPoolService : IDesktopPoolService
{
    private readonly ApplicationDbContext _context;
    private readonly IPortPoolService _portPoolService;

    public DesktopPoolService(ApplicationDbContext context, IPortPoolService portPoolService)
    {
        _context = context;
        _portPoolService = portPoolService;
    }

    public async Task<List<DesktopPoolDto>> GetAllAsync()
    {
        var pools = await _context.DesktopPools.ToListAsync();
        var result = new List<DesktopPoolDto>();

        foreach (var dp in pools)
        {
            var availablePorts = await _portPoolService.GetAvailablePortCountAsync(dp.Id);
            var availableCapacity = await GetAvailableCapacityAsync(dp.Id);

            result.Add(new DesktopPoolDto
            {
                Id = dp.Id,
                Name = dp.Name,
                Description = dp.Description,
                Status = dp.Status,
                MaxDesktops = dp.MaxDesktops,
                CurrentDesktops = dp.CurrentDesktops,
                AvailableCapacity = availableCapacity,
                DefaultProtocol = dp.DefaultProtocol,
                DefaultPort = dp.DefaultPort,
                PortRangeStart = dp.PortRangeStart,
                PortRangeEnd = dp.PortRangeEnd,
                AvailablePorts = availablePorts,
                CpuCores = dp.CpuCores,
                MemoryGB = dp.MemoryGB,
                StorageGB = dp.StorageGB,
                CreatedAt = dp.CreatedAt,
                UpdatedAt = dp.UpdatedAt
            });
        }

        return result;
    }

    public async Task<DesktopPoolDetailDto?> GetByIdAsync(Guid id)
    {
        var pool = await _context.DesktopPools
            .Include(dp => dp.Desktops)
            .FirstOrDefaultAsync(dp => dp.Id == id);

        if (pool == null)
            return null;

        var availablePorts = await _portPoolService.GetAvailablePortCountAsync(pool.Id);
        var availableCapacity = await GetAvailableCapacityAsync(pool.Id);

        return new DesktopPoolDetailDto
        {
            Id = pool.Id,
            Name = pool.Name,
            Description = pool.Description,
            Status = pool.Status,
            MaxDesktops = pool.MaxDesktops,
            CurrentDesktops = pool.CurrentDesktops,
            AvailableCapacity = availableCapacity,
            DefaultProtocol = pool.DefaultProtocol,
            DefaultPort = pool.DefaultPort,
            PortRangeStart = pool.PortRangeStart,
            PortRangeEnd = pool.PortRangeEnd,
            AvailablePorts = availablePorts,
            CpuCores = pool.CpuCores,
            MemoryGB = pool.MemoryGB,
            StorageGB = pool.StorageGB,
            CreatedAt = pool.CreatedAt,
            UpdatedAt = pool.UpdatedAt,
            Desktops = pool.Desktops.Select(d => new DesktopDto
            {
                Id = d.Id,
                DesktopPoolId = d.DesktopPoolId,
                Name = d.Name,
                ComputerName = d.ComputerName,
                IpAddress = d.IpAddress,
                Port = d.Port,
                Status = d.Status,
                StatusMessage = d.StatusMessage,
                Protocol = d.Protocol,
                CpuCores = d.CpuCores,
                MemoryGB = d.MemoryGB,
                StorageGB = d.StorageGB,
                LastHeartbeat = d.LastHeartbeat,
                CreatedAt = d.CreatedAt
            }).ToList()
        };
    }

    public async Task<DesktopPoolDto> CreateAsync(CreateDesktopPoolDto dto)
    {
        var desktopPool = new DesktopPool
        {
            Id = Guid.NewGuid(),
            Name = dto.Name,
            Description = dto.Description,
            Status = DesktopPoolStatus.Available,
            MaxDesktops = dto.MaxDesktops,
            CurrentDesktops = 0,
            DefaultProtocol = dto.DefaultProtocol,
            DefaultPort = dto.DefaultPort,
            PortRangeStart = dto.PortRangeStart,
            PortRangeEnd = dto.PortRangeEnd,
            ImageTemplate = dto.ImageTemplate,
            CpuCores = dto.CpuCores,
            MemoryGB = dto.MemoryGB,
            StorageGB = dto.StorageGB,
            CreatedAt = DateTime.UtcNow
        };

        _context.DesktopPools.Add(desktopPool);
        await _context.SaveChangesAsync();

        await _portPoolService.InitializePortPoolAsync(desktopPool.Id);

        return new DesktopPoolDto
        {
            Id = desktopPool.Id,
            Name = desktopPool.Name,
            Description = desktopPool.Description,
            Status = desktopPool.Status,
            MaxDesktops = desktopPool.MaxDesktops,
            CurrentDesktops = desktopPool.CurrentDesktops,
            DefaultProtocol = desktopPool.DefaultProtocol,
            DefaultPort = desktopPool.DefaultPort,
            CpuCores = desktopPool.CpuCores,
            MemoryGB = desktopPool.MemoryGB,
            StorageGB = desktopPool.StorageGB,
            CreatedAt = desktopPool.CreatedAt
        };
    }

    public async Task<DesktopPoolDto?> UpdateAsync(Guid id, UpdateDesktopPoolDto dto)
    {
        var desktopPool = await _context.DesktopPools.FindAsync(id);
        if (desktopPool == null) return null;

        var portRangeChanged = false;
        if (!string.IsNullOrEmpty(dto.Name)) desktopPool.Name = dto.Name;
        if (dto.Description != null) desktopPool.Description = dto.Description;
        if (dto.Status.HasValue) desktopPool.Status = dto.Status.Value;
        if (dto.MaxDesktops.HasValue) desktopPool.MaxDesktops = dto.MaxDesktops.Value;
        if (dto.DefaultProtocol.HasValue) desktopPool.DefaultProtocol = dto.DefaultProtocol.Value;
        if (dto.DefaultPort.HasValue) desktopPool.DefaultPort = dto.DefaultPort.Value;
        if (dto.PortRangeStart.HasValue && dto.PortRangeStart.Value != desktopPool.PortRangeStart)
        {
            desktopPool.PortRangeStart = dto.PortRangeStart.Value;
            portRangeChanged = true;
        }
        if (dto.PortRangeEnd.HasValue && dto.PortRangeEnd.Value != desktopPool.PortRangeEnd)
        {
            desktopPool.PortRangeEnd = dto.PortRangeEnd.Value;
            portRangeChanged = true;
        }

        desktopPool.UpdatedAt = DateTime.UtcNow;
        await _context.SaveChangesAsync();

        if (portRangeChanged)
        {
            await _portPoolService.InitializePortPoolAsync(desktopPool.Id);
        }

        var availablePorts = await _portPoolService.GetAvailablePortCountAsync(desktopPool.Id);
        var availableCapacity = await GetAvailableCapacityAsync(desktopPool.Id);

        return new DesktopPoolDto
        {
            Id = desktopPool.Id,
            Name = desktopPool.Name,
            Description = desktopPool.Description,
            Status = desktopPool.Status,
            MaxDesktops = desktopPool.MaxDesktops,
            CurrentDesktops = desktopPool.CurrentDesktops,
            AvailableCapacity = availableCapacity,
            DefaultProtocol = desktopPool.DefaultProtocol,
            DefaultPort = desktopPool.DefaultPort,
            PortRangeStart = desktopPool.PortRangeStart,
            PortRangeEnd = desktopPool.PortRangeEnd,
            AvailablePorts = availablePorts,
            CpuCores = desktopPool.CpuCores,
            MemoryGB = desktopPool.MemoryGB,
            StorageGB = desktopPool.StorageGB,
            CreatedAt = desktopPool.CreatedAt,
            UpdatedAt = desktopPool.UpdatedAt
        };
    }

    public async Task<bool> DeleteAsync(Guid id)
    {
        var desktopPool = await _context.DesktopPools.FindAsync(id);
        if (desktopPool == null) return false;

        _context.DesktopPools.Remove(desktopPool);
        await _context.SaveChangesAsync();
        return true;
    }

    public async Task<int> ScaleUpAsync(Guid desktopPoolId, int count)
    {
        var pool = await _context.DesktopPools.FindAsync(desktopPoolId);
        if (pool == null)
            throw new InvalidOperationException("Desktop pool not found");

        var actualCount = Math.Min(count, pool.MaxDesktops - pool.CurrentDesktops);
        if (actualCount <= 0)
            return 0;

        var createdCount = 0;
        for (int i = 0; i < actualCount; i++)
        {
            var port = await _portPoolService.AllocatePortAsync(desktopPoolId);
            if (port == null)
                break;

            var desktop = new Desktop
            {
                Id = Guid.NewGuid(),
                DesktopPoolId = desktopPoolId,
                Name = $"{pool.Name}-Desktop-{pool.CurrentDesktops + createdCount + 1}",
                Port = port.Value,
                Status = DesktopStatus.Available,
                Protocol = pool.DefaultProtocol,
                CpuCores = pool.CpuCores,
                MemoryGB = pool.MemoryGB,
                StorageGB = pool.StorageGB,
                CreatedAt = DateTime.UtcNow
            };

            _context.Desktops.Add(desktop);
            createdCount++;
        }

        if (createdCount > 0)
        {
            pool.CurrentDesktops += createdCount;
            pool.UpdatedAt = DateTime.UtcNow;
            await _context.SaveChangesAsync();
        }

        return createdCount;
    }

    public async Task<int> ScaleDownAsync(Guid desktopPoolId, int count)
    {
        var pool = await _context.DesktopPools.FindAsync(desktopPoolId);
        if (pool == null)
            throw new InvalidOperationException("Desktop pool not found");

        var desktopsToRemove = await _context.Desktops
            .Where(d => d.DesktopPoolId == desktopPoolId && d.Status == DesktopStatus.Available)
            .OrderBy(d => d.CreatedAt)
            .Take(count)
            .ToListAsync();

        var removedCount = 0;
        foreach (var desktop in desktopsToRemove)
        {
            desktop.Status = DesktopStatus.Maintenance;
            await _portPoolService.ReleasePortByDesktopAsync(desktop.Id);

            var sessions = await _context.Sessions
                .Where(s => s.DesktopId == desktop.Id && s.Status == SessionStatus.Active)
                .ToListAsync();

            foreach (var session in sessions)
            {
                session.Status = SessionStatus.Disconnected;
                session.DisconnectedAt = DateTime.UtcNow;
                session.UpdatedAt = DateTime.UtcNow;
            }

            _context.Desktops.Remove(desktop);
            removedCount++;
        }

        if (removedCount > 0)
        {
            pool.CurrentDesktops -= removedCount;
            pool.UpdatedAt = DateTime.UtcNow;
            await _context.SaveChangesAsync();
        }

        await CleanupOrphanedSessionsAsync(desktopPoolId);

        return removedCount;
    }

    public async Task<int> CleanupOrphanedSessionsAsync(Guid desktopPoolId)
    {
        var orphanedSessions = await _context.Sessions
            .Include(s => s.Desktop)
            .Where(s => s.Desktop.DesktopPoolId == desktopPoolId)
            .Where(s => !_context.Desktops.Any(d => d.Id == s.DesktopId) ||
                       s.Status == SessionStatus.Active &&
                       !_context.Desktops.Any(d => d.Id == s.DesktopId && d.Status == DesktopStatus.InUse))
            .ToListAsync();

        var cleanedCount = 0;
        foreach (var session in orphanedSessions)
        {
            await _portPoolService.ReleasePortBySessionAsync(session.Id);

            if (session.Status == SessionStatus.Active)
            {
                session.Status = SessionStatus.Disconnected;
                session.DisconnectedAt = DateTime.UtcNow;
                session.UpdatedAt = DateTime.UtcNow;
            }

            cleanedCount++;
        }

        var orphanedActiveSessions = await _context.Sessions
            .Where(s => s.Status == SessionStatus.Active &&
                       !_context.Users.Any(u => u.Id == s.UserId))
            .ToListAsync();

        foreach (var session in orphanedActiveSessions)
        {
            session.Status = SessionStatus.Disconnected;
            session.DisconnectedAt = DateTime.UtcNow;
            session.UpdatedAt = DateTime.UtcNow;
            await _portPoolService.ReleasePortBySessionAsync(session.Id);
            cleanedCount++;
        }

        if (cleanedCount > 0)
        {
            await _context.SaveChangesAsync();
        }

        return cleanedCount;
    }

    public async Task<int> GetAvailableCapacityAsync(Guid desktopPoolId)
    {
        var pool = await _context.DesktopPools.FindAsync(desktopPoolId);
        if (pool == null)
            throw new InvalidOperationException("Desktop pool not found");

        var availableDesktops = await _context.Desktops
            .CountAsync(d => d.DesktopPoolId == desktopPoolId && d.Status == DesktopStatus.Available);

        var availablePorts = await _portPoolService.GetAvailablePortCountAsync(desktopPoolId);

        return Math.Min(availableDesktops, availablePorts);
    }
}
