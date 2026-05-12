namespace FileStorageService.Services;

public interface IDeduplicationService
{
    Task<string?> ComputeFileHashAsync(Stream stream);
    Task<string?> ComputeFileHashAsync(string filePath);
    Task<string> ComputeChunkHashAsync(Stream chunkStream);
}
