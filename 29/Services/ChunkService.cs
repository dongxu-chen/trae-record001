using System.Collections.Concurrent;
using FileStorageService.Models;
using Microsoft.Extensions.Options;

namespace FileStorageService.Services;

public class ChunkService : IChunkService
{
    private readonly UploadSettings _settings;
    private readonly IFileRepository _fileRepository;
    private readonly IDeduplicationService _deduplicationService;
    private readonly string _chunkBasePath;
    private readonly string _uploadBasePath;
    private static readonly ConcurrentDictionary<string, ChunkSession> _sessions = new();

    public ChunkService(
        IOptions<UploadSettings> settings,
        IFileRepository fileRepository,
        IDeduplicationService deduplicationService)
    {
        _settings = settings.Value;
        _fileRepository = fileRepository;
        _deduplicationService = deduplicationService;
        _chunkBasePath = Path.Combine(Directory.GetCurrentDirectory(), _settings.ChunkPath);
        _uploadBasePath = Path.Combine(Directory.GetCurrentDirectory(), _settings.UploadPath);

        if (!Directory.Exists(_chunkBasePath))
        {
            Directory.CreateDirectory(_chunkBasePath);
        }

        RestoreSessionsFromDisk();
    }

    public async Task<ChunkUploadResult> UploadChunkAsync(ChunkUploadRequest request, Stream chunkStream)
    {
        if (request.TotalFileSize > _settings.MaxFileSize)
        {
            return new ChunkUploadResult
            {
                Success = false,
                Message = $"文件大小超过最大限制 {_settings.MaxFileSize} 字节"
            };
        }

        if (request.ChunkIndex < 0)
        {
            return new ChunkUploadResult
            {
                Success = false,
                Message = "分片索引不能为负数"
            };
        }

        if (request.ChunkIndex >= request.TotalChunks)
        {
            return new ChunkUploadResult
            {
                Success = false,
                Message = $"分片索引超出范围，应为 0 到 {request.TotalChunks - 1}"
            };
        }

        if (!string.IsNullOrWhiteSpace(request.FileHash))
        {
            var duplicateFile = await FindDuplicateFileAsync(request.FileHash, request.TotalFileSize);
            if (duplicateFile != null)
            {
                return new ChunkUploadResult
                {
                    Success = true,
                    Message = "秒传成功，文件已存在",
                    IsComplete = true,
                    IsDuplicate = true,
                    DuplicateFileId = duplicateFile.Id,
                    UploadedChunks = request.TotalChunks,
                    TotalChunks = request.TotalChunks
                };
            }
        }

        var session = await GetOrCreateSessionAsync(request);
        if (session == null)
        {
            return new ChunkUploadResult
            {
                Success = false,
                Message = "无法创建上传会话"
            };
        }

        var chunkDir = Path.Combine(_chunkBasePath, session.FileId);
        if (!Directory.Exists(chunkDir))
        {
            Directory.CreateDirectory(chunkDir);
        }

        var chunkFileName = $"{request.ChunkIndex:D8}.part";
        var chunkFilePath = Path.Combine(chunkDir, chunkFileName);

        using (var fileStream = new FileStream(chunkFilePath, FileMode.Create, FileAccess.Write))
        {
            await chunkStream.CopyToAsync(fileStream);
        }

        lock (session.UploadedChunks)
        {
            session.UploadedChunks.Add(request.ChunkIndex);
            session.LastUpdatedAt = DateTime.UtcNow;
        }

        var isComplete = false;
        var uploadedCount = 0;
        List<int> uploadedIndices;
        List<int> missingChunks;

        lock (session.UploadedChunks)
        {
            uploadedCount = session.UploadedChunks.Count;
            isComplete = uploadedCount == request.TotalChunks;
            uploadedIndices = session.UploadedChunks.OrderBy(i => i).ToList();
            missingChunks = new List<int>();
            for (int i = 0; i < request.TotalChunks; i++)
            {
                if (!session.UploadedChunks.Contains(i))
                {
                    missingChunks.Add(i);
                }
            }
        }

        Guid? fileId = null;

        if (isComplete)
        {
            fileId = await MergeChunksAsync(request, session, chunkDir);
            CleanupChunkDirectory(chunkDir);
            _sessions.TryRemove(session.FileId, out _);
        }

        return new ChunkUploadResult
        {
            Success = true,
            Message = isComplete ? "文件上传并合并完成" : "分片上传成功",
            UploadedChunks = uploadedCount,
            TotalChunks = request.TotalChunks,
            IsComplete = isComplete,
            FileId = fileId,
            UploadedChunkIndices = uploadedIndices,
            MissingChunks = missingChunks
        };
    }

    public Task<ChunkStatusResult> GetChunkStatusAsync(string fileId)
    {
        if (string.IsNullOrWhiteSpace(fileId))
        {
            return Task.FromResult(new ChunkStatusResult { FileId = fileId });
        }

        var session = _sessions.GetValueOrDefault(fileId);
        if (session == null)
        {
            var chunkDir = Path.Combine(_chunkBasePath, fileId);
            if (Directory.Exists(chunkDir))
            {
                var diskIndices = GetUploadedChunksFromDisk(chunkDir);
                return Task.FromResult(new ChunkStatusResult
                {
                    FileId = fileId,
                    UploadedChunks = diskIndices.Count,
                    TotalChunks = 0,
                    UploadedChunkIndices = diskIndices,
                    IsComplete = false
                });
            }
            return Task.FromResult(new ChunkStatusResult { FileId = fileId });
        }

        List<int> uploadedIndices;
        List<int> missingChunks;
        int uploadedCount;
        bool isComplete;

        lock (session.UploadedChunks)
        {
            uploadedCount = session.UploadedChunks.Count;
            isComplete = uploadedCount == session.TotalChunks;
            uploadedIndices = session.UploadedChunks.OrderBy(i => i).ToList();
            missingChunks = new List<int>();
            for (int i = 0; i < session.TotalChunks; i++)
            {
                if (!session.UploadedChunks.Contains(i))
                {
                    missingChunks.Add(i);
                }
            }
        }

        return Task.FromResult(new ChunkStatusResult
        {
            FileId = fileId,
            UploadedChunks = uploadedCount,
            TotalChunks = session.TotalChunks,
            UploadedChunkIndices = uploadedIndices,
            MissingChunks = missingChunks,
            IsComplete = isComplete
        });
    }

    public Task<ChunkSession?> GetOrCreateSessionAsync(ChunkUploadRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.FileId))
        {
            request.FileId = Guid.NewGuid().ToString();
        }

        var session = _sessions.GetOrAdd(request.FileId, _ => new ChunkSession
        {
            FileId = request.FileId,
            FileName = request.FileName,
            TotalFileSize = request.TotalFileSize,
            TotalChunks = request.TotalChunks,
            ContentType = request.ContentType,
            FileHash = request.FileHash,
            CreatedAt = DateTime.UtcNow,
            LastUpdatedAt = DateTime.UtcNow
        });

        var chunkDir = Path.Combine(_chunkBasePath, request.FileId);
        if (Directory.Exists(chunkDir))
        {
            var diskChunks = GetUploadedChunksFromDisk(chunkDir);
            lock (session.UploadedChunks)
            {
                foreach (var idx in diskChunks)
                {
                    session.UploadedChunks.Add(idx);
                }
            }
        }

        return Task.FromResult<ChunkSession?>(session);
    }

    public Task<bool> CleanupChunksAsync(string fileId)
    {
        var chunkDir = Path.Combine(_chunkBasePath, fileId);
        if (Directory.Exists(chunkDir))
        {
            CleanupChunkDirectory(chunkDir);
            _sessions.TryRemove(fileId, out _);
            return Task.FromResult(true);
        }
        _sessions.TryRemove(fileId, out _);
        return Task.FromResult(false);
    }

    public Task<List<ChunkSession>> GetAllSessionsAsync()
    {
        var sessions = _sessions.Values.ToList();
        return Task.FromResult(sessions);
    }

    private async Task<Guid> MergeChunksAsync(ChunkUploadRequest request, ChunkSession session, string chunkDir)
    {
        var fileId = Guid.NewGuid();
        var storedFileName = $"{fileId}{Path.GetExtension(request.FileName)}";
        var finalFilePath = Path.Combine(_uploadBasePath, storedFileName);

        using (var finalStream = new FileStream(finalFilePath, FileMode.Create, FileAccess.Write))
        {
            for (int i = 0; i < session.TotalChunks; i++)
            {
                var chunkFileName = $"{i:D8}.part";
                var chunkFilePath = Path.Combine(chunkDir, chunkFileName);

                if (!File.Exists(chunkFilePath))
                {
                    throw new FileNotFoundException($"缺少分片 {i}", chunkFilePath);
                }

                using (var chunkStream = new FileStream(chunkFilePath, FileMode.Open, FileAccess.Read))
                {
                    await chunkStream.CopyToAsync(finalStream);
                }
            }
        }

        var finalFileInfo = new FileInfo(finalFilePath);
        var fileHash = session.FileHash;
        if (string.IsNullOrWhiteSpace(fileHash))
        {
            fileHash = await _deduplicationService.ComputeFileHashAsync(finalFilePath);
        }

        var fileMetadata = new FileMetadata
        {
            Id = fileId,
            OriginalFileName = session.FileName,
            StoredFileName = storedFileName,
            ContentType = session.ContentType ?? "application/octet-stream",
            FileSize = finalFileInfo.Length,
            FilePath = finalFilePath,
            FileHash = fileHash,
            UploadStatus = UploadStatus.Completed,
            TotalChunks = session.TotalChunks,
            CreatedAt = DateTime.UtcNow
        };

        await _fileRepository.AddAsync(fileMetadata);

        return fileId;
    }

    private async Task<FileMetadata?> FindDuplicateFileAsync(string fileHash, long fileSize)
    {
        if (string.IsNullOrWhiteSpace(fileHash))
            return null;

        var allFiles = await _fileRepository.GetAllAsync(1, 1000);
        return allFiles.FirstOrDefault(f =>
            f.FileHash != null &&
            f.FileHash.Equals(fileHash, StringComparison.OrdinalIgnoreCase) &&
            f.FileSize == fileSize &&
            File.Exists(f.FilePath));
    }

    private static List<int> GetUploadedChunksFromDisk(string chunkDir)
    {
        var indices = new List<int>();
        if (!Directory.Exists(chunkDir))
            return indices;

        foreach (var file in Directory.GetFiles(chunkDir, "*.part"))
        {
            var fileName = Path.GetFileNameWithoutExtension(file);
            if (int.TryParse(fileName, out var index))
            {
                indices.Add(index);
            }
        }
        return indices.OrderBy(i => i).ToList();
    }

    private void RestoreSessionsFromDisk()
    {
        if (!Directory.Exists(_chunkBasePath))
            return;

        foreach (var dir in Directory.GetDirectories(_chunkBasePath))
        {
            var dirName = Path.GetFileName(dir);
            var uploadedIndices = GetUploadedChunksFromDisk(dir);

            if (uploadedIndices.Count > 0)
            {
                var dirInfo = new DirectoryInfo(dir);
                var session = new ChunkSession
                {
                    FileId = dirName,
                    FileName = dirName,
                    TotalFileSize = 0,
                    TotalChunks = uploadedIndices.Max() + 1,
                    CreatedAt = dirInfo.CreationTimeUtc,
                    LastUpdatedAt = dirInfo.LastWriteTimeUtc
                };

                foreach (var idx in uploadedIndices)
                {
                    session.UploadedChunks.Add(idx);
                }

                _sessions.TryAdd(dirName, session);
            }
        }
    }

    private static void CleanupChunkDirectory(string chunkDir)
    {
        if (Directory.Exists(chunkDir))
        {
            Directory.Delete(chunkDir, true);
        }
    }
}
