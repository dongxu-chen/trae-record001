using System.Text;
using FileStorageService.Models;
using FileStorageService.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;

namespace FileStorageService.Controllers;

[ApiController]
[Route("api/[controller]")]
public class FileController : ControllerBase
{
    private readonly IFileRepository _fileRepository;
    private readonly ITokenService _tokenService;
    private readonly IChunkService _chunkService;
    private readonly IDeduplicationService _deduplicationService;
    private readonly UploadSettings _uploadSettings;

    public FileController(
        IFileRepository fileRepository,
        ITokenService tokenService,
        IChunkService chunkService,
        IDeduplicationService deduplicationService,
        IOptions<UploadSettings> uploadSettings)
    {
        _fileRepository = fileRepository;
        _tokenService = tokenService;
        _chunkService = chunkService;
        _deduplicationService = deduplicationService;
        _uploadSettings = uploadSettings.Value;
    }

    [HttpPost("upload")]
    public async Task<IActionResult> Upload(IFormFile file)
    {
        if (file == null || file.Length == 0)
        {
            return BadRequest("请选择要上传的文件");
        }

        if (file.Length > _uploadSettings.MaxFileSize)
        {
            return BadRequest($"文件大小超过最大限制 {_uploadSettings.MaxFileSize} 字节");
        }

        string? fileHash = null;
        using (var stream = file.OpenReadStream())
        {
            fileHash = await _deduplicationService.ComputeFileHashAsync(stream);
        }

        if (!string.IsNullOrWhiteSpace(fileHash))
        {
            var allFiles = await _fileRepository.GetAllAsync(1, 1000);
            var duplicateFile = allFiles.FirstOrDefault(f =>
                f.FileHash != null &&
                f.FileHash.Equals(fileHash, StringComparison.OrdinalIgnoreCase) &&
                f.FileSize == file.Length &&
                System.IO.File.Exists(f.FilePath));

            if (duplicateFile != null)
            {
                return Ok(new
                {
                    IsDuplicate = true,
                    DuplicateFileId = duplicateFile.Id,
                    FileName = file.FileName,
                    FileSize = file.Length,
                    Message = "秒传成功，文件已存在"
                });
            }
        }

        var fileId = Guid.NewGuid();
        var extension = Path.GetExtension(file.FileName);
        var storedFileName = $"{fileId}{extension}";
        var uploadPath = Path.Combine(Directory.GetCurrentDirectory(), _uploadSettings.UploadPath);
        var filePath = Path.Combine(uploadPath, storedFileName);

        using (var stream = new FileStream(filePath, FileMode.Create))
        {
            await file.CopyToAsync(stream);
        }

        var fileMetadata = new FileMetadata
        {
            Id = fileId,
            OriginalFileName = file.FileName,
            StoredFileName = storedFileName,
            ContentType = file.ContentType ?? "application/octet-stream",
            FileSize = file.Length,
            FilePath = filePath,
            FileHash = fileHash,
            CreatedAt = DateTime.UtcNow,
            UploadStatus = UploadStatus.Completed
        };

        await _fileRepository.AddAsync(fileMetadata);

        var result = new UploadFileResult
        {
            FileId = fileId,
            FileName = file.FileName,
            FileSize = file.Length,
            ContentType = file.ContentType ?? "application/octet-stream",
            UploadedAt = DateTime.UtcNow
        };

        return Ok(result);
    }

    [HttpPost("upload/check")]
    public async Task<IActionResult> CheckUpload([FromBody] UploadCheckRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.FileHash) || request.FileSize <= 0)
        {
            return BadRequest("文件哈希和大小不能为空");
        }

        var allFiles = await _fileRepository.GetAllAsync(1, 1000);
        var duplicateFile = allFiles.FirstOrDefault(f =>
            f.FileHash != null &&
            f.FileHash.Equals(request.FileHash, StringComparison.OrdinalIgnoreCase) &&
            f.FileSize == request.FileSize &&
            System.IO.File.Exists(f.FilePath));

        if (duplicateFile != null)
        {
            return Ok(new UploadCheckResult
            {
                ShouldUpload = false,
                IsDuplicate = true,
                DuplicateFileId = duplicateFile.Id,
                TotalChunks = request.TotalChunks
            });
        }

        var sessionId = request.FileHash + "_" + request.FileSize;
        var chunkStatus = await _chunkService.GetChunkStatusAsync(sessionId);

        if (chunkStatus.UploadedChunks > 0)
        {
            return Ok(new UploadCheckResult
            {
                ShouldUpload = true,
                IsDuplicate = false,
                HasPartialUpload = true,
                UploadFileId = sessionId,
                UploadedChunks = chunkStatus.UploadedChunkIndices,
                UploadedChunkCount = chunkStatus.UploadedChunks,
                TotalChunks = chunkStatus.TotalChunks > 0 ? chunkStatus.TotalChunks : request.TotalChunks
            });
        }

        return Ok(new UploadCheckResult
        {
            ShouldUpload = true,
            IsDuplicate = false,
            HasPartialUpload = false,
            TotalChunks = request.TotalChunks
        });
    }

    [HttpPost("upload/chunk")]
    public async Task<IActionResult> UploadChunk([FromForm] ChunkUploadRequest request, IFormFile file)
    {
        if (file == null || file.Length == 0)
        {
            return BadRequest("分片文件不能为空");
        }

        if (string.IsNullOrWhiteSpace(request.FileId))
        {
            if (!string.IsNullOrWhiteSpace(request.FileHash))
            {
                request.FileId = request.FileHash + "_" + request.TotalFileSize;
            }
            else
            {
                request.FileId = Guid.NewGuid().ToString();
            }
        }

        using var stream = file.OpenReadStream();
        var result = await _chunkService.UploadChunkAsync(request, stream);

        if (!result.Success)
        {
            return BadRequest(result);
        }

        return Ok(result);
    }

    [HttpGet("chunks/{fileId}/status")]
    public async Task<IActionResult> GetChunkStatus(string fileId)
    {
        var status = await _chunkService.GetChunkStatusAsync(fileId);
        return Ok(status);
    }

    [HttpDelete("chunks/{fileId}")]
    public async Task<IActionResult> CleanupChunks(string fileId)
    {
        var success = await _chunkService.CleanupChunksAsync(fileId);
        if (!success)
        {
            return NotFound("未找到该文件的分片数据");
        }
        return Ok("分片清理成功");
    }

    [HttpGet("download/{id}")]
    public async Task<IActionResult> Download(Guid id, [FromQuery] string? token = null)
    {
        var fileMetadata = await _fileRepository.GetByIdAsync(id);

        if (fileMetadata == null)
        {
            return NotFound("文件不存在");
        }

        if (!System.IO.File.Exists(fileMetadata.FilePath))
        {
            return NotFound("文件在磁盘上不存在");
        }

        fileMetadata.LastAccessedAt = DateTime.UtcNow;
        await _fileRepository.UpdateAsync(fileMetadata);

        var fileName = fileMetadata.OriginalFileName;
        var safeFileName = GetSafeFileName(fileName);
        var encodedFileName = Uri.EscapeDataString(fileName);

        var contentDisposition = $"attachment; filename=\"{safeFileName}\"; filename*=UTF-8''{encodedFileName}";
        Response.Headers.Append("Content-Disposition", contentDisposition);

        var fileStream = new FileStream(fileMetadata.FilePath, FileMode.Open, FileAccess.Read, FileShare.Read);
        return File(fileStream, fileMetadata.ContentType, enableRangeProcessing: true);
    }

    private static string GetSafeFileName(string fileName)
    {
        if (string.IsNullOrWhiteSpace(fileName))
            return "download";

        var safeName = new StringBuilder(fileName.Length);

        foreach (var c in fileName)
        {
            if (c == '\"' || c == '\\' || c == '/' || c == ';' || c == '\r' || c == '\n')
            {
                safeName.Append('_');
            }
            else if (c < 32 || c > 126)
            {
                safeName.Append('_');
            }
            else
            {
                safeName.Append(c);
            }
        }

        var result = safeName.ToString();
        return string.IsNullOrWhiteSpace(result) ? "download" : result;
    }

    [HttpGet("download/signed/{id}")]
    public async Task<IActionResult> DownloadWithToken(Guid id, [FromQuery] string token)
    {
        if (string.IsNullOrWhiteSpace(token))
        {
            return Unauthorized("缺少访问令牌");
        }

        if (!_tokenService.ValidateDownloadToken(id, token))
        {
            return Unauthorized("无效或已过期的访问令牌");
        }

        return await Download(id, null);
    }

    [HttpGet("{id}/download-url")]
    public async Task<IActionResult> GetSignedDownloadUrl(Guid id)
    {
        var fileMetadata = await _fileRepository.GetByIdAsync(id);

        if (fileMetadata == null)
        {
            return NotFound("文件不存在");
        }

        var token = _tokenService.GenerateDownloadToken(id);
        var encodedToken = Uri.EscapeDataString(token);

        var baseUrl = $"{Request.Scheme}://{Request.Host}{Request.PathBase}";
        var downloadUrl = $"{baseUrl}/api/file/download/signed/{id}?token={encodedToken}";

        return Ok(new
        {
            FileId = id,
            DownloadUrl = downloadUrl,
            ExpiresAt = DateTime.UtcNow.AddMinutes(30)
        });
    }

    [HttpGet("{id}")]
    public async Task<IActionResult> GetFileInfo(Guid id)
    {
        var fileMetadata = await _fileRepository.GetByIdAsync(id);

        if (fileMetadata == null)
        {
            return NotFound("文件不存在");
        }

        return Ok(new
        {
            fileMetadata.Id,
            fileMetadata.OriginalFileName,
            fileMetadata.ContentType,
            fileMetadata.FileSize,
            fileMetadata.FileHash,
            fileMetadata.CreatedAt,
            fileMetadata.LastAccessedAt,
            fileMetadata.UploadStatus,
            fileMetadata.TotalChunks
        });
    }

    [HttpDelete("{id}")]
    public async Task<IActionResult> Delete(Guid id)
    {
        var fileMetadata = await _fileRepository.GetByIdAsync(id);

        if (fileMetadata == null)
        {
            return NotFound("文件不存在");
        }

        if (System.IO.File.Exists(fileMetadata.FilePath))
        {
            System.IO.File.Delete(fileMetadata.FilePath);
        }

        await _fileRepository.DeleteAsync(id);

        return Ok("文件删除成功");
    }

    [HttpGet]
    public async Task<IActionResult> GetFiles(int page = 1, int pageSize = 20)
    {
        var total = await _fileRepository.GetTotalCountAsync();
        var files = await _fileRepository.GetAllAsync(page, pageSize);

        var result = files.Select(f => new
        {
            f.Id,
            f.OriginalFileName,
            f.ContentType,
            f.FileSize,
            f.FileHash,
            f.CreatedAt,
            f.UploadStatus
        }).ToList();

        return Ok(new
        {
            Total = total,
            Page = page,
            PageSize = pageSize,
            Files = result
        });
    }
}
