namespace FileStorageService.Models;

public class FileMetadata
{
    public Guid Id { get; set; }
    public string OriginalFileName { get; set; } = string.Empty;
    public string StoredFileName { get; set; } = string.Empty;
    public string ContentType { get; set; } = string.Empty;
    public long FileSize { get; set; }
    public string FilePath { get; set; } = string.Empty;
    public string? FileHash { get; set; }
    public string? UploaderId { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime? LastAccessedAt { get; set; }
    public bool IsDeleted { get; set; } = false;
    public UploadStatus UploadStatus { get; set; } = UploadStatus.Completed;
    public int TotalChunks { get; set; } = 1;
}

public enum UploadStatus
{
    Pending,
    Uploading,
    Completed,
    Failed
}
