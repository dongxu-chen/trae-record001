namespace FileStorageService.Models;

public class ChunkUploadRequest
{
    public string FileId { get; set; } = string.Empty;
    public string FileName { get; set; } = string.Empty;
    public int ChunkIndex { get; set; }
    public int TotalChunks { get; set; }
    public long TotalFileSize { get; set; }
    public string? ContentType { get; set; }
    public string? FileHash { get; set; }
}

public class ChunkUploadResult
{
    public bool Success { get; set; }
    public string Message { get; set; } = string.Empty;
    public int UploadedChunks { get; set; }
    public int TotalChunks { get; set; }
    public bool IsComplete { get; set; }
    public Guid? FileId { get; set; }
    public List<int>? MissingChunks { get; set; }
    public List<int>? UploadedChunkIndices { get; set; }
    public bool IsDuplicate { get; set; }
    public Guid? DuplicateFileId { get; set; }
}

public class UploadFileResult
{
    public Guid FileId { get; set; }
    public string FileName { get; set; } = string.Empty;
    public long FileSize { get; set; }
    public string ContentType { get; set; } = string.Empty;
    public DateTime UploadedAt { get; set; }
}

public class ChunkStatusResult
{
    public string FileId { get; set; } = string.Empty;
    public int UploadedChunks { get; set; }
    public int TotalChunks { get; set; }
    public List<int> UploadedChunkIndices { get; set; } = new();
    public List<int> MissingChunks { get; set; } = new();
    public bool IsComplete { get; set; }
}

public class UploadCheckRequest
{
    public string FileName { get; set; } = string.Empty;
    public long FileSize { get; set; }
    public string FileHash { get; set; } = string.Empty;
    public int TotalChunks { get; set; }
}

public class UploadCheckResult
{
    public bool ShouldUpload { get; set; }
    public bool IsDuplicate { get; set; }
    public Guid? DuplicateFileId { get; set; }
    public bool HasPartialUpload { get; set; }
    public string? UploadFileId { get; set; }
    public List<int>? UploadedChunks { get; set; }
    public int UploadedChunkCount { get; set; }
    public int TotalChunks { get; set; }
}

public class ChunkSession
{
    public string FileId { get; set; } = string.Empty;
    public string FileName { get; set; } = string.Empty;
    public long TotalFileSize { get; set; }
    public int TotalChunks { get; set; }
    public string? ContentType { get; set; }
    public string? FileHash { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime LastUpdatedAt { get; set; }
    public HashSet<int> UploadedChunks { get; set; } = new();
}
