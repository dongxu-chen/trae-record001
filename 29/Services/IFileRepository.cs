using FileStorageService.Models;

namespace FileStorageService.Services;

public interface IFileRepository
{
    Task<FileMetadata> AddAsync(FileMetadata fileMetadata);
    Task<FileMetadata?> GetByIdAsync(Guid id);
    Task<List<FileMetadata>> GetAllAsync(int page, int pageSize);
    Task<int> GetTotalCountAsync();
    Task UpdateAsync(FileMetadata fileMetadata);
    Task DeleteAsync(Guid id);
}
