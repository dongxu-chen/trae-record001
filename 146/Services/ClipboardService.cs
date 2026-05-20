using CloudDesktop.Api.Data;
using CloudDesktop.Api.Models;
using Microsoft.EntityFrameworkCore;

namespace CloudDesktop.Api.Services;

public interface IClipboardService
{
    Task<ClipboardConfiguration?> GetConfigurationByDesktopAsync(Guid desktopId);
    Task<ClipboardConfiguration?> GetConfigurationByPoolAsync(Guid desktopPoolId);
    Task<ClipboardConfiguration?> GetConfigurationByUserAsync(Guid userId);
    Task<ClipboardConfiguration> CreateOrUpdateConfigurationAsync(ClipboardConfiguration config);
    Task<bool> DeleteConfigurationAsync(Guid id);
    Task<bool> IsClipboardAllowedAsync(Guid desktopId, Guid userId, bool isCopyFromClient);
    Task<bool> IsFileTransferAllowedAsync(Guid desktopId, Guid userId, string? fileType = null);
    Task LogClipboardActivityAsync(Guid sessionId, Guid userId, Guid desktopId, bool isCopyFromClient,
        string? contentType, int contentSizeKB, string? fileName, bool wasBlocked, string? blockReason);
    Task<List<ClipboardAuditLog>> GetAuditLogsBySessionAsync(Guid sessionId, int limit = 100);
    Task<List<ClipboardAuditLog>> GetAuditLogsByUserAsync(Guid userId, int limit = 100);
}

public class ClipboardService : IClipboardService
{
    private readonly ApplicationDbContext _context;

    public ClipboardService(ApplicationDbContext context)
    {
        _context = context;
    }

    public async Task<ClipboardConfiguration?> GetConfigurationByDesktopAsync(Guid desktopId)
    {
        return await _context.ClipboardConfigurations
            .FirstOrDefaultAsync(c => c.DesktopId == desktopId);
    }

    public async Task<ClipboardConfiguration?> GetConfigurationByPoolAsync(Guid desktopPoolId)
    {
        return await _context.ClipboardConfigurations
            .FirstOrDefaultAsync(c => c.DesktopPoolId == desktopPoolId);
    }

    public async Task<ClipboardConfiguration?> GetConfigurationByUserAsync(Guid userId)
    {
        return await _context.ClipboardConfigurations
            .FirstOrDefaultAsync(c => c.UserId == userId);
    }

    public async Task<ClipboardConfiguration> CreateOrUpdateConfigurationAsync(ClipboardConfiguration config)
    {
        var existing = await _context.ClipboardConfigurations
            .FirstOrDefaultAsync(c =>
                (config.DesktopId.HasValue && c.DesktopId == config.DesktopId) ||
                (config.DesktopPoolId.HasValue && c.DesktopPoolId == config.DesktopPoolId) ||
                (config.UserId.HasValue && c.UserId == config.UserId));

        if (existing != null)
        {
            existing.ClipboardEnabled = config.ClipboardEnabled;
            existing.CopyFromClientEnabled = config.CopyFromClientEnabled;
            existing.CopyToClientEnabled = config.CopyToClientEnabled;
            existing.FileTransferEnabled = config.FileTransferEnabled;
            existing.MaxClipboardSizeKB = config.MaxClipboardSizeKB;
            existing.RestrictFileTypes = config.RestrictFileTypes;
            existing.AllowedFileTypes = config.AllowedFileTypes;
            existing.BlockedFileTypes = config.BlockedFileTypes;
            existing.AuditClipboardActivity = config.AuditClipboardActivity;
            existing.UpdatedAt = DateTime.UtcNow;
            await _context.SaveChangesAsync();
            return existing;
        }

        config.Id = Guid.NewGuid();
        config.CreatedAt = DateTime.UtcNow;
        _context.ClipboardConfigurations.Add(config);
        await _context.SaveChangesAsync();
        return config;
    }

    public async Task<bool> DeleteConfigurationAsync(Guid id)
    {
        var config = await _context.ClipboardConfigurations.FindAsync(id);
        if (config == null) return false;

        _context.ClipboardConfigurations.Remove(config);
        await _context.SaveChangesAsync();
        return true;
    }

    public async Task<bool> IsClipboardAllowedAsync(Guid desktopId, Guid userId, bool isCopyFromClient)
    {
        var desktopConfig = await GetConfigurationByDesktopAsync(desktopId);
        var desktop = await _context.Desktops.FindAsync(desktopId);
        var userConfig = await GetConfigurationByUserAsync(userId);
        ClipboardConfiguration? poolConfig = null;

        if (desktop != null)
        {
            poolConfig = await GetConfigurationByPoolAsync(desktop.DesktopPoolId);
        }

        var effectiveConfig = desktopConfig ?? userConfig ?? poolConfig;

        if (effectiveConfig == null) return true;
        if (!effectiveConfig.ClipboardEnabled) return false;

        if (isCopyFromClient)
        {
            return effectiveConfig.CopyFromClientEnabled;
        }

        return effectiveConfig.CopyToClientEnabled;
    }

    public async Task<bool> IsFileTransferAllowedAsync(Guid desktopId, Guid userId, string? fileType = null)
    {
        var desktopConfig = await GetConfigurationByDesktopAsync(desktopId);
        var desktop = await _context.Desktops.FindAsync(desktopId);
        var userConfig = await GetConfigurationByUserAsync(userId);
        ClipboardConfiguration? poolConfig = null;

        if (desktop != null)
        {
            poolConfig = await GetConfigurationByPoolAsync(desktop.DesktopPoolId);
        }

        var effectiveConfig = desktopConfig ?? userConfig ?? poolConfig;

        if (effectiveConfig == null) return true;
        if (!effectiveConfig.FileTransferEnabled) return false;

        if (effectiveConfig.RestrictFileTypes && !string.IsNullOrEmpty(fileType))
        {
            if (!string.IsNullOrEmpty(effectiveConfig.AllowedFileTypes))
            {
                var allowedTypes = effectiveConfig.AllowedFileTypes.Split(',', StringSplitOptions.RemoveEmptyEntries);
                if (!allowedTypes.Any(t => t.Trim().Equals(fileType, StringComparison.OrdinalIgnoreCase)))
                {
                    return false;
                }
            }

            if (!string.IsNullOrEmpty(effectiveConfig.BlockedFileTypes))
            {
                var blockedTypes = effectiveConfig.BlockedFileTypes.Split(',', StringSplitOptions.RemoveEmptyEntries);
                if (blockedTypes.Any(t => t.Trim().Equals(fileType, StringComparison.OrdinalIgnoreCase)))
                {
                    return false;
                }
            }
        }

        return true;
    }

    public async Task LogClipboardActivityAsync(Guid sessionId, Guid userId, Guid desktopId, bool isCopyFromClient,
        string? contentType, int contentSizeKB, string? fileName, bool wasBlocked, string? blockReason)
    {
        var log = new ClipboardAuditLog
        {
            Id = Guid.NewGuid(),
            SessionId = sessionId,
            UserId = userId,
            DesktopId = desktopId,
            IsCopyFromClient = isCopyFromClient,
            ContentType = contentType,
            ContentSizeKB = contentSizeKB,
            FileName = fileName,
            WasBlocked = wasBlocked,
            BlockReason = blockReason,
            Timestamp = DateTime.UtcNow
        };

        _context.ClipboardAuditLogs.Add(log);
        await _context.SaveChangesAsync();
    }

    public async Task<List<ClipboardAuditLog>> GetAuditLogsBySessionAsync(Guid sessionId, int limit = 100)
    {
        return await _context.ClipboardAuditLogs
            .Include(l => l.Session)
            .Include(l => l.User)
            .Include(l => l.Desktop)
            .Where(l => l.SessionId == sessionId)
            .OrderByDescending(l => l.Timestamp)
            .Take(limit)
            .ToListAsync();
    }

    public async Task<List<ClipboardAuditLog>> GetAuditLogsByUserAsync(Guid userId, int limit = 100)
    {
        return await _context.ClipboardAuditLogs
            .Include(l => l.Session)
            .Include(l => l.User)
            .Include(l => l.Desktop)
            .Where(l => l.UserId == userId)
            .OrderByDescending(l => l.Timestamp)
            .Take(limit)
            .ToListAsync();
    }
}
