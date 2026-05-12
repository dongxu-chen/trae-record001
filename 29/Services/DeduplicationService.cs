using System.Security.Cryptography;
using System.Text;

namespace FileStorageService.Services;

public class DeduplicationService : IDeduplicationService
{
    public async Task<string?> ComputeFileHashAsync(Stream stream)
    {
        if (stream == null || !stream.CanRead)
            return null;

        using var md5 = MD5.Create();
        var hashBytes = await md5.ComputeHashAsync(stream);
        return ConvertHashToString(hashBytes);
    }

    public async Task<string?> ComputeFileHashAsync(string filePath)
    {
        if (!File.Exists(filePath))
            return null;

        using var stream = new FileStream(filePath, FileMode.Open, FileAccess.Read, FileShare.Read);
        using var md5 = MD5.Create();
        var hashBytes = await md5.ComputeHashAsync(stream);
        return ConvertHashToString(hashBytes);
    }

    public async Task<string> ComputeChunkHashAsync(Stream chunkStream)
    {
        if (chunkStream == null)
            return string.Empty;

        var position = chunkStream.Position;
        chunkStream.Seek(0, SeekOrigin.Begin);

        using var md5 = MD5.Create();
        var hashBytes = await md5.ComputeHashAsync(chunkStream);

        chunkStream.Seek(position, SeekOrigin.Begin);
        return ConvertHashToString(hashBytes);
    }

    private static string ConvertHashToString(byte[] hashBytes)
    {
        var sb = new StringBuilder(hashBytes.Length * 2);
        foreach (var b in hashBytes)
        {
            sb.Append(b.ToString("x2"));
        }
        return sb.ToString();
    }
}
