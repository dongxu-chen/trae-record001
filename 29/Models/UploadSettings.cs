namespace FileStorageService.Models;

public class UploadSettings
{
    public string UploadPath { get; set; } = "uploads";
    public string ChunkPath { get; set; } = "chunks";
    public long MaxFileSize { get; set; } = 1073741824;
    public long MaxChunkSize { get; set; } = 5242880;
}

public class TokenSettings
{
    public string SecretKey { get; set; } = string.Empty;
    public int ExpirationMinutes { get; set; } = 30;
}
