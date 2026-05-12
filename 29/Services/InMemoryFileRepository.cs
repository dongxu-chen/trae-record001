using System.Collections.Concurrent;
using FileStorageService.Models;

namespace FileStorageService.Services;

public class InMemoryFileRepository : IFileRepository
{
    private readonly ConcurrentDictionary<Guid, FileMetadata> _files = new();

    public Task<FileMetadata> AddAsync(FileMetadata fileMetadata)
    {
        _files.TryAdd(fileMetadata.Id, fileMetadata);
        return Task.FromResult(fileMetadata);
    }

    public Task<FileMetadata?> GetByIdAsync(Guid id)
    {
        _files.TryGetValue(id, out var file);
        return Task.FromResult(file?.IsDeleted == true ? null : file);
    }

    public Task<List<FileMetadata>> GetAllAsync(int page, int pageSize)
    {
        var files = _files.Values
            .Where(f => !f.IsDeleted)
            .OrderByDescending(f => f.CreatedAt)
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .ToList();

        return Task.FromResult(files);
    }

    public Task<int> GetTotalCountAsync()
    {
        var count = _files.Values.Count(f => !f.IsDeleted);
        return Task.FromResult(count);
    }

    public Task UpdateAsync(FileMetadata fileMetadata)
    {
        _files.TryUpdate(fileMetadata.Id, fileMetadata, _files[fileMetadata.Id]);
        return Task.CompletedTask;
    }

    public Task DeleteAsync(Guid id)
    {
        if (_files.TryGetValue(id, out var file))
        {
            file.IsDeleted = true;
        }
        return Task.CompletedTask;
    }
}
