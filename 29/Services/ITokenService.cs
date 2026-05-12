namespace FileStorageService.Services;

public interface ITokenService
{
    string GenerateDownloadToken(Guid fileId);
    bool ValidateDownloadToken(Guid fileId, string token);
    string GenerateUploadToken(string fileName, long fileSize);
    bool ValidateUploadToken(string token, string fileName, long fileSize);
}
