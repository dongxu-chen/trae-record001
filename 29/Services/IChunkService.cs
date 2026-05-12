using FileStorageService.Models;

namespace FileStorageService.Services;

public interface IChunkService
{
    Task<ChunkUploadResult> UploadChunkAsync(ChunkUploadRequest request, Stream chunkStream);
    Task<ChunkStatusResult> GetChunkStatusAsync(string fileId);
    Task<ChunkSession?> GetOrCreateSessionAsync(ChunkUploadRequest request);
    Task<bool> CleanupChunksAsync(string fileId);
    Task<List<ChunkSession>> GetAllSessionsAsync();
}
