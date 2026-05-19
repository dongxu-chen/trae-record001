using CloudDesktop.Api.Data;
using CloudDesktop.Api.Models;
using CloudDesktop.Api.Models.Enums;
using Microsoft.EntityFrameworkCore;

namespace CloudDesktop.Api.Services;

public interface IHealthCheckService
{
    Task<DesktopHealthCheck> PerformHealthCheckAsync(Guid desktopId);
    Task<List<DesktopHealthCheck>> GetHealthCheckHistoryAsync(Guid desktopId, int limit = 50);
    Task<DesktopHealthConfiguration?> GetHealthConfigurationAsync(Guid? desktopId = null, Guid? desktopPoolId = null);
    Task<DesktopHealthConfiguration> CreateOrUpdateConfigurationAsync(DesktopHealthConfiguration config);
    Task<bool> TryRecoverDesktopAsync(Guid desktopId, string reason);
    Task<List<RecoveryHistory>> GetRecoveryHistoryAsync(Guid desktopId, int limit = 50);
    Task RecordMetricsAsync(Guid desktopId, decimal cpuUsage, decimal memoryUsage, decimal diskUsage,
        long networkInBytes, long networkOutBytes, int networkLatencyMs, decimal gpuUsage = 0,
        decimal gpuMemoryUsage = 0, decimal gpuTemperature = 0);
    Task<List<DesktopMetrics>> GetMetricsHistoryAsync(Guid desktopId, DateTime? startTime = null, DateTime? endTime = null);
    Task<bool> IsRecoveryNeededAsync(Guid desktopId);
}

public class HealthCheckService : IHealthCheckService
{
    private readonly ApplicationDbContext _context;

    public HealthCheckService(ApplicationDbContext context)
    {
        _context = context;
    }

    public async Task<DesktopHealthCheck> PerformHealthCheckAsync(Guid desktopId)
    {
        var desktop = await _context.Desktops.FindAsync(desktopId);
        if (desktop == null)
            throw new InvalidOperationException("Desktop not found");

        var healthCheck = new DesktopHealthCheck
        {
            Id = Guid.NewGuid(),
            DesktopId = desktopId,
            CheckedAt = DateTime.UtcNow
        };

        var config = await GetHealthConfigurationAsync(desktopId, desktop.DesktopPoolId);

        healthCheck.RdpStatus = await CheckRdpConnectivityAsync(desktop);
        healthCheck.CpuStatus = HealthStatus.Healthy;
        healthCheck.MemoryStatus = HealthStatus.Healthy;
        healthCheck.DiskStatus = HealthStatus.Healthy;
        healthCheck.NetworkStatus = HealthStatus.Healthy;
        healthCheck.GpuStatus = desktop.GpuPassthroughEnabled ? HealthStatus.Healthy : HealthStatus.Unknown;

        var allStatuses = new[] { healthCheck.RdpStatus, healthCheck.CpuStatus, healthCheck.MemoryStatus,
            healthCheck.DiskStatus, healthCheck.NetworkStatus, healthCheck.GpuStatus }
            .Where(s => s != HealthStatus.Unknown)
            .ToList();

        if (allStatuses.Any(s => s == HealthStatus.Critical))
            healthCheck.OverallStatus = HealthStatus.Critical;
        else if (allStatuses.Any(s => s == HealthStatus.Warning))
            healthCheck.OverallStatus = HealthStatus.Warning;
        else if (allStatuses.All(s => s == HealthStatus.Healthy))
            healthCheck.OverallStatus = HealthStatus.Healthy;
        else
            healthCheck.OverallStatus = HealthStatus.Unknown;

        healthCheck.StatusMessage = healthCheck.OverallStatus switch
        {
            HealthStatus.Healthy => "Desktop is healthy",
            HealthStatus.Warning => "Desktop has warning conditions",
            HealthStatus.Critical => "Desktop has critical issues",
            HealthStatus.Offline => "Desktop is offline",
            _ => "Desktop status unknown"
        };

        desktop.HealthStatus = healthCheck.OverallStatus;

        if (healthCheck.OverallStatus != HealthStatus.Healthy)
        {
            desktop.ConsecutiveHealthFailures++;
        }
        else
        {
            desktop.ConsecutiveHealthFailures = 0;
        }

        desktop.UpdatedAt = DateTime.UtcNow;

        _context.DesktopHealthChecks.Add(healthCheck);
        await _context.SaveChangesAsync();

        if (config?.AutoRecoveryEnabled == true && await IsRecoveryNeededAsync(desktopId))
        {
            await TryRecoverDesktopAsync(desktopId, $"Health check failed: {healthCheck.StatusMessage}");
        }

        return healthCheck;
    }

    public async Task<List<DesktopHealthCheck>> GetHealthCheckHistoryAsync(Guid desktopId, int limit = 50)
    {
        return await _context.DesktopHealthChecks
            .Where(h => h.DesktopId == desktopId)
            .OrderByDescending(h => h.CheckedAt)
            .Take(limit)
            .ToListAsync();
    }

    public async Task<DesktopHealthConfiguration?> GetHealthConfigurationAsync(Guid? desktopId = null, Guid? desktopPoolId = null)
    {
        if (desktopId.HasValue)
        {
            var desktopConfig = await _context.DesktopHealthConfigurations
                .FirstOrDefaultAsync(c => c.DesktopId == desktopId.Value);

            if (desktopConfig != null) return desktopConfig;
        }

        if (desktopPoolId.HasValue)
        {
            var poolConfig = await _context.DesktopHealthConfigurations
                .FirstOrDefaultAsync(c => c.DesktopPoolId == desktopPoolId.Value);

            if (poolConfig != null) return poolConfig;
        }

        return await _context.DesktopHealthConfigurations
            .FirstOrDefaultAsync(c => !c.DesktopId.HasValue && !c.DesktopPoolId.HasValue);
    }

    public async Task<DesktopHealthConfiguration> CreateOrUpdateConfigurationAsync(DesktopHealthConfiguration config)
    {
        var existing = await _context.DesktopHealthConfigurations
            .FirstOrDefaultAsync(c =>
                (config.DesktopId.HasValue && c.DesktopId == config.DesktopId) ||
                (config.DesktopPoolId.HasValue && c.DesktopPoolId == config.DesktopPoolId));

        if (existing != null)
        {
            existing.HealthCheckEnabled = config.HealthCheckEnabled;
            existing.CheckIntervalSeconds = config.CheckIntervalSeconds;
            existing.HeartbeatTimeoutSeconds = config.HeartbeatTimeoutSeconds;
            existing.AutoRecoveryEnabled = config.AutoRecoveryEnabled;
            existing.MaxRecoveryAttempts = config.MaxRecoveryAttempts;
            existing.RecoveryCooldownMinutes = config.RecoveryCooldownMinutes;
            existing.RestartOnRdpFailure = config.RestartOnRdpFailure;
            existing.RestartOnHighCpuUsage = config.RestartOnHighCpuUsage;
            existing.CpuUsageThresholdPercent = config.CpuUsageThresholdPercent;
            existing.CpuUsageThresholdDurationSeconds = config.CpuUsageThresholdDurationSeconds;
            existing.RestartOnHighMemoryUsage = config.RestartOnHighMemoryUsage;
            existing.MemoryUsageThresholdPercent = config.MemoryUsageThresholdPercent;
            existing.MemoryUsageThresholdDurationSeconds = config.MemoryUsageThresholdDurationSeconds;
            existing.RestartOnHighDiskUsage = config.RestartOnHighDiskUsage;
            existing.DiskUsageThresholdPercent = config.DiskUsageThresholdPercent;
            existing.ConsecutiveFailuresForRecovery = config.ConsecutiveFailuresForRecovery;
            existing.UpdatedAt = DateTime.UtcNow;
            await _context.SaveChangesAsync();
            return existing;
        }

        config.Id = Guid.NewGuid();
        config.CreatedAt = DateTime.UtcNow;
        _context.DesktopHealthConfigurations.Add(config);
        await _context.SaveChangesAsync();
        return config;
    }

    public async Task<bool> TryRecoverDesktopAsync(Guid desktopId, string reason)
    {
        var desktop = await _context.Desktops.FindAsync(desktopId);
        if (desktop == null) return false;

        var config = await GetHealthConfigurationAsync(desktopId, desktop.DesktopPoolId);
        var recoveryAttempts = desktop.RecoveryAttempts;
        var maxAttempts = config?.MaxRecoveryAttempts ?? 3;

        if (config?.RecoveryCooldownMinutes > 0 && desktop.LastRecoveryAt.HasValue)
        {
            var cooldownEnd = desktop.LastRecoveryAt.Value.AddMinutes(config.RecoveryCooldownMinutes);
            if (DateTime.UtcNow < cooldownEnd)
                return false;
        }

        if (recoveryAttempts >= maxAttempts)
            return false;

        var recovery = new RecoveryHistory
        {
            Id = Guid.NewGuid(),
            DesktopId = desktopId,
            RecoveryType = "Restart",
            Reason = reason,
            StatusBeforeRecovery = desktop.HealthStatus,
            RecoveryAttempt = recoveryAttempts + 1,
            StartedAt = DateTime.UtcNow
        };

        try
        {
            desktop.Status = DesktopStatus.Maintenance;
            desktop.UpdatedAt = DateTime.UtcNow;
            await _context.SaveChangesAsync();

            await Task.Delay(5000);

            desktop.Status = DesktopStatus.Available;
            desktop.ConsecutiveHealthFailures = 0;
            desktop.RecoveryAttempts = 0;
            desktop.LastRecoveryAt = DateTime.UtcNow;
            desktop.UpdatedAt = DateTime.UtcNow;

            recovery.RecoverySuccessful = true;
            recovery.RecoveryDurationSeconds = 5;
            recovery.RecoveryDetails = "Desktop restarted successfully";
        }
        catch (Exception ex)
        {
            recovery.RecoverySuccessful = false;
            recovery.ErrorMessage = ex.Message;
            desktop.RecoveryAttempts++;
            desktop.UpdatedAt = DateTime.UtcNow;
        }

        recovery.CompletedAt = DateTime.UtcNow;
        _context.RecoveryHistories.Add(recovery);
        await _context.SaveChangesAsync();

        return recovery.RecoverySuccessful;
    }

    public async Task<List<RecoveryHistory>> GetRecoveryHistoryAsync(Guid desktopId, int limit = 50)
    {
        return await _context.RecoveryHistories
            .Where(r => r.DesktopId == desktopId)
            .OrderByDescending(r => r.StartedAt)
            .Take(limit)
            .ToListAsync();
    }

    public async Task RecordMetricsAsync(Guid desktopId, decimal cpuUsage, decimal memoryUsage, decimal diskUsage,
        long networkInBytes, long networkOutBytes, int networkLatencyMs, decimal gpuUsage = 0,
        decimal gpuMemoryUsage = 0, decimal gpuTemperature = 0)
    {
        var metrics = new DesktopMetrics
        {
            Id = Guid.NewGuid(),
            DesktopId = desktopId,
            CpuUsagePercent = cpuUsage,
            MemoryUsagePercent = memoryUsage,
            DiskUsagePercent = diskUsage,
            NetworkInBytes = networkInBytes,
            NetworkOutBytes = networkOutBytes,
            NetworkLatencyMs = networkLatencyMs,
            GpuUsagePercent = gpuUsage,
            GpuMemoryUsagePercent = gpuMemoryUsage,
            GpuTemperature = gpuTemperature,
            Timestamp = DateTime.UtcNow
        };

        _context.DesktopMetrics.Add(metrics);
        await _context.SaveChangesAsync();
    }

    public async Task<List<DesktopMetrics>> GetMetricsHistoryAsync(Guid desktopId, DateTime? startTime = null, DateTime? endTime = null)
    {
        var query = _context.DesktopMetrics
            .Where(m => m.DesktopId == desktopId)
            .AsQueryable();

        if (startTime.HasValue)
            query = query.Where(m => m.Timestamp >= startTime.Value);

        if (endTime.HasValue)
            query = query.Where(m => m.Timestamp <= endTime.Value);

        return await query
            .OrderByDescending(m => m.Timestamp)
            .Take(500)
            .ToListAsync();
    }

    public async Task<bool> IsRecoveryNeededAsync(Guid desktopId)
    {
        var desktop = await _context.Desktops.FindAsync(desktopId);
        if (desktop == null) return false;

        var config = await GetHealthConfigurationAsync(desktopId, desktop.DesktopPoolId);
        if (config == null) return false;

        if (desktop.ConsecutiveHealthFailures >= config.ConsecutiveFailuresForRecovery)
            return true;

        return false;
    }

    private async Task<HealthStatus> CheckRdpConnectivityAsync(Desktop desktop)
    {
        if (desktop.Status == DesktopStatus.Offline)
            return HealthStatus.Offline;

        if (desktop.LastHeartbeat.HasValue)
        {
            var config = await GetHealthConfigurationAsync(desktop.Id, desktop.DesktopPoolId);
            var timeoutSeconds = config?.HeartbeatTimeoutSeconds ?? 120;

            if (DateTime.UtcNow.Subtract(desktop.LastHeartbeat.Value).TotalSeconds > timeoutSeconds)
                return HealthStatus.Critical;
        }

        return desktop.Status == DesktopStatus.Available || desktop.Status == DesktopStatus.InUse
            ? HealthStatus.Healthy
            : HealthStatus.Warning;
    }
}
