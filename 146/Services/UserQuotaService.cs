using CloudDesktop.Api.Data;
using CloudDesktop.Api.Dtos;
using CloudDesktop.Api.Models;
using CloudDesktop.Api.Models.Enums;
using Microsoft.EntityFrameworkCore;

namespace CloudDesktop.Api.Services;

public interface IUserQuotaService
{
    Task<List<UserQuotaDto>> GetAllAsync(Guid? userId = null);
    Task<UserQuotaDto?> GetByIdAsync(Guid id);
    Task<UserQuotaDto> CreateAsync(CreateUserQuotaDto dto);
    Task<UserQuotaDto?> UpdateAsync(Guid id, UpdateUserQuotaDto dto);
    Task<bool> DeleteAsync(Guid id);
    Task IncrementSessionUsageAsync(Guid userId, Guid desktopPoolId);
    Task DecrementSessionUsageAsync(Guid userId, Guid desktopPoolId);
    Task UpdateUsageMinutesAsync(Guid sessionId, int minutes);
    Task ResetDailyUsageAsync();
    Task ResetMonthlyUsageAsync();
}

public class UserQuotaService : IUserQuotaService
{
    private readonly ApplicationDbContext _context;

    public UserQuotaService(ApplicationDbContext context)
    {
        _context = context;
    }

    public async Task<List<UserQuotaDto>> GetAllAsync(Guid? userId = null)
    {
        var query = _context.UserQuotas
            .Include(q => q.User)
            .Include(q => q.DesktopPool)
            .AsQueryable();

        if (userId.HasValue)
            query = query.Where(q => q.UserId == userId.Value);

        return await query
            .Select(q => new UserQuotaDto
            {
                Id = q.Id,
                UserId = q.UserId,
                DesktopPoolId = q.DesktopPoolId,
                Username = q.User.Username,
                DesktopPoolName = q.DesktopPool.Name,
                MaxConcurrentSessions = q.MaxConcurrentSessions,
                CurrentActiveSessions = q.CurrentActiveSessions,
                MaxDailySessionMinutes = q.MaxDailySessionMinutes,
                TodayUsedMinutes = q.TodayUsedMinutes,
                MaxMonthlySessionMinutes = q.MaxMonthlySessionMinutes,
                MonthUsedMinutes = q.MonthUsedMinutes,
                CreatedAt = q.CreatedAt
            })
            .ToListAsync();
    }

    public async Task<UserQuotaDto?> GetByIdAsync(Guid id)
    {
        return await _context.UserQuotas
            .Include(q => q.User)
            .Include(q => q.DesktopPool)
            .Where(q => q.Id == id)
            .Select(q => new UserQuotaDto
            {
                Id = q.Id,
                UserId = q.UserId,
                DesktopPoolId = q.DesktopPoolId,
                Username = q.User.Username,
                DesktopPoolName = q.DesktopPool.Name,
                MaxConcurrentSessions = q.MaxConcurrentSessions,
                CurrentActiveSessions = q.CurrentActiveSessions,
                MaxDailySessionMinutes = q.MaxDailySessionMinutes,
                TodayUsedMinutes = q.TodayUsedMinutes,
                MaxMonthlySessionMinutes = q.MaxMonthlySessionMinutes,
                MonthUsedMinutes = q.MonthUsedMinutes,
                CreatedAt = q.CreatedAt
            })
            .FirstOrDefaultAsync();
    }

    public async Task<UserQuotaDto> CreateAsync(CreateUserQuotaDto dto)
    {
        var existing = await _context.UserQuotas
            .FirstOrDefaultAsync(q => q.UserId == dto.UserId && q.DesktopPoolId == dto.DesktopPoolId);

        if (existing != null)
            throw new InvalidOperationException("Quota already exists for this user and desktop pool.");

        var quota = new UserQuota
        {
            Id = Guid.NewGuid(),
            UserId = dto.UserId,
            DesktopPoolId = dto.DesktopPoolId,
            MaxConcurrentSessions = dto.MaxConcurrentSessions,
            CurrentActiveSessions = 0,
            MaxDailySessionMinutes = dto.MaxDailySessionMinutes,
            TodayUsedMinutes = 0,
            MaxMonthlySessionMinutes = dto.MaxMonthlySessionMinutes,
            MonthUsedMinutes = 0,
            CreatedAt = DateTime.UtcNow
        };

        _context.UserQuotas.Add(quota);
        await _context.SaveChangesAsync();

        var user = await _context.Users.FindAsync(dto.UserId);
        var pool = await _context.DesktopPools.FindAsync(dto.DesktopPoolId);

        return new UserQuotaDto
        {
            Id = quota.Id,
            UserId = quota.UserId,
            DesktopPoolId = quota.DesktopPoolId,
            Username = user?.Username ?? string.Empty,
            DesktopPoolName = pool?.Name ?? string.Empty,
            MaxConcurrentSessions = quota.MaxConcurrentSessions,
            CurrentActiveSessions = quota.CurrentActiveSessions,
            MaxDailySessionMinutes = quota.MaxDailySessionMinutes,
            TodayUsedMinutes = quota.TodayUsedMinutes,
            MaxMonthlySessionMinutes = quota.MaxMonthlySessionMinutes,
            MonthUsedMinutes = quota.MonthUsedMinutes,
            CreatedAt = quota.CreatedAt
        };
    }

    public async Task<UserQuotaDto?> UpdateAsync(Guid id, UpdateUserQuotaDto dto)
    {
        var quota = await _context.UserQuotas.FindAsync(id);
        if (quota == null) return null;

        if (dto.MaxConcurrentSessions.HasValue)
            quota.MaxConcurrentSessions = dto.MaxConcurrentSessions.Value;

        if (dto.MaxDailySessionMinutes.HasValue)
            quota.MaxDailySessionMinutes = dto.MaxDailySessionMinutes.Value;

        if (dto.MaxMonthlySessionMinutes.HasValue)
            quota.MaxMonthlySessionMinutes = dto.MaxMonthlySessionMinutes.Value;

        quota.UpdatedAt = DateTime.UtcNow;
        await _context.SaveChangesAsync();

        var user = await _context.Users.FindAsync(quota.UserId);
        var pool = await _context.DesktopPools.FindAsync(quota.DesktopPoolId);

        return new UserQuotaDto
        {
            Id = quota.Id,
            UserId = quota.UserId,
            DesktopPoolId = quota.DesktopPoolId,
            Username = user?.Username ?? string.Empty,
            DesktopPoolName = pool?.Name ?? string.Empty,
            MaxConcurrentSessions = quota.MaxConcurrentSessions,
            CurrentActiveSessions = quota.CurrentActiveSessions,
            MaxDailySessionMinutes = quota.MaxDailySessionMinutes,
            TodayUsedMinutes = quota.TodayUsedMinutes,
            MaxMonthlySessionMinutes = quota.MaxMonthlySessionMinutes,
            MonthUsedMinutes = quota.MonthUsedMinutes,
            CreatedAt = quota.CreatedAt
        };
    }

    public async Task<bool> DeleteAsync(Guid id)
    {
        var quota = await _context.UserQuotas.FindAsync(id);
        if (quota == null) return false;

        _context.UserQuotas.Remove(quota);
        await _context.SaveChangesAsync();
        return true;
    }

    public async Task IncrementSessionUsageAsync(Guid userId, Guid desktopPoolId)
    {
        var quota = await _context.UserQuotas
            .FirstOrDefaultAsync(q => q.UserId == userId && q.DesktopPoolId == desktopPoolId);

        if (quota != null)
        {
            quota.CurrentActiveSessions++;
            quota.UpdatedAt = DateTime.UtcNow;
            await _context.SaveChangesAsync();
        }
    }

    public async Task DecrementSessionUsageAsync(Guid userId, Guid desktopPoolId)
    {
        var quota = await _context.UserQuotas
            .FirstOrDefaultAsync(q => q.UserId == userId && q.DesktopPoolId == desktopPoolId);

        if (quota != null && quota.CurrentActiveSessions > 0)
        {
            quota.CurrentActiveSessions--;
            quota.UpdatedAt = DateTime.UtcNow;
            await _context.SaveChangesAsync();
        }
    }

    public async Task UpdateUsageMinutesAsync(Guid sessionId, int minutes)
    {
        var session = await _context.Sessions
            .Include(s => s.Desktop)
            .FirstOrDefaultAsync(s => s.Id == sessionId);

        if (session == null) return;

        var quota = await _context.UserQuotas
            .FirstOrDefaultAsync(q => q.UserId == session.UserId
                && q.DesktopPoolId == session.Desktop.DesktopPoolId);

        if (quota != null)
        {
            quota.TodayUsedMinutes += minutes;
            quota.MonthUsedMinutes += minutes;
            quota.UpdatedAt = DateTime.UtcNow;
            await _context.SaveChangesAsync();
        }
    }

    public async Task ResetDailyUsageAsync()
    {
        var quotas = await _context.UserQuotas.ToListAsync();
        foreach (var quota in quotas)
        {
            quota.TodayUsedMinutes = 0;
            quota.UpdatedAt = DateTime.UtcNow;
        }
        await _context.SaveChangesAsync();
    }

    public async Task ResetMonthlyUsageAsync()
    {
        var quotas = await _context.UserQuotas.ToListAsync();
        foreach (var quota in quotas)
        {
            quota.MonthUsedMinutes = 0;
            quota.TodayUsedMinutes = 0;
            quota.UpdatedAt = DateTime.UtcNow;
        }
        await _context.SaveChangesAsync();
    }
}
