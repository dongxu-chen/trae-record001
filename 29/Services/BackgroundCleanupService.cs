using FileStorageService.Models;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

namespace FileStorageService.Services;

public class BackgroundCleanupService : BackgroundService
{
    private readonly ILogger<BackgroundCleanupService> _logger;
    private readonly IChunkService _chunkService;
    private readonly UploadSettings _settings;
    private readonly TimeSpan _cleanupInterval;
    private readonly TimeSpan _chunkExpiration;

    public BackgroundCleanupService(
        ILogger<BackgroundCleanupService> logger,
        IChunkService chunkService,
        IOptions<UploadSettings> settings)
    {
        _logger = logger;
        _chunkService = chunkService;
        _settings = settings.Value;
        _cleanupInterval = TimeSpan.FromMinutes(30);
        _chunkExpiration = TimeSpan.FromHours(24);
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("后台分片清理服务已启动");

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                await CleanupExpiredChunksAsync(stoppingToken);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "清理过期分片时发生错误");
            }

            await Task.Delay(_cleanupInterval, stoppingToken);
        }

        _logger.LogInformation("后台分片清理服务已停止");
    }

    private async Task CleanupExpiredChunksAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("开始清理过期分片...");

        var sessions = await _chunkService.GetAllSessionsAsync();
        var now = DateTime.UtcNow;
        var cleanedCount = 0;

        foreach (var session in sessions)
        {
            if (stoppingToken.IsCancellationRequested)
                break;

            var elapsed = now - session.LastUpdatedAt;
            if (elapsed > _chunkExpiration)
            {
                _logger.LogInformation($"清理过期分片会话: {session.FileId}, 最后更新: {session.LastUpdatedAt}, 已上传分片: {session.UploadedChunks.Count}");

                await _chunkService.CleanupChunksAsync(session.FileId);
                cleanedCount++;
            }
        }

        var chunkBasePath = Path.Combine(Directory.GetCurrentDirectory(), _settings.ChunkPath);
        if (Directory.Exists(chunkBasePath))
        {
            foreach (var dir in Directory.GetDirectories(chunkBasePath))
            {
                if (stoppingToken.IsCancellationRequested)
                    break;

                var dirInfo = new DirectoryInfo(dir);
                var elapsed = now - dirInfo.LastWriteTimeUtc;

                if (elapsed > _chunkExpiration)
                {
                    try
                    {
                        Directory.Delete(dir, true);
                        _logger.LogInformation($"清理磁盘过期分片目录: {dirInfo.Name}");
                        cleanedCount++;
                    }
                    catch (Exception ex)
                    {
                        _logger.LogWarning(ex, $"删除分片目录失败: {dirInfo.Name}");
                    }
                }
            }
        }

        _logger.LogInformation($"分片清理完成，共清理 {cleanedCount} 个过期会话");
    }
}
