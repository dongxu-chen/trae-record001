using System.Security.Cryptography;
using System.Text;
using FileStorageService.Models;
using Microsoft.Extensions.Options;

namespace FileStorageService.Services;

public class TokenService : ITokenService
{
    private readonly TokenSettings _settings;
    private readonly byte[] _keyBytes;
    private static readonly long MinUnixSeconds = DateTimeOffset.UnixEpoch.ToUnixTimeSeconds();
    private static readonly long MaxUnixSeconds = DateTimeOffset.MaxValue.ToUnixTimeSeconds();

    public TokenService(IOptions<TokenSettings> settings)
    {
        _settings = settings.Value;
        _keyBytes = Encoding.UTF8.GetBytes(_settings.SecretKey);
    }

    public string GenerateDownloadToken(Guid fileId)
    {
        var timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        var payload = $"{fileId}|{timestamp}|{_settings.ExpirationMinutes}";
        var signature = ComputeHmac(payload);
        return $"{payload}|{signature}";
    }

    public bool ValidateDownloadToken(Guid fileId, string token)
    {
        if (string.IsNullOrWhiteSpace(token))
            return false;

        var parts = token.Split('|');
        if (parts.Length != 4)
            return false;

        var tokenFileId = parts[0];
        var timestampStr = parts[1];
        var expirationMinutes = parts[2];
        var signature = parts[3];

        if (tokenFileId != fileId.ToString())
            return false;

        if (!long.TryParse(timestampStr, out var timestamp))
            return false;

        if (!IsValidUnixTimestamp(timestamp))
            return false;

        if (!int.TryParse(expirationMinutes, out var minutes) || minutes <= 0)
            return false;

        DateTimeOffset createdAt;
        try
        {
            createdAt = DateTimeOffset.FromUnixTimeSeconds(timestamp);
        }
        catch (ArgumentOutOfRangeException)
        {
            return false;
        }

        DateTimeOffset expiresAt;
        try
        {
            expiresAt = createdAt.AddMinutes(minutes);
        }
        catch (ArgumentOutOfRangeException)
        {
            return false;
        }

        if (DateTimeOffset.UtcNow > expiresAt)
            return false;

        var payload = $"{tokenFileId}|{timestampStr}|{expirationMinutes}";
        var expectedSignature = ComputeHmac(payload);

        return CryptographicEquals(signature, expectedSignature);
    }

    public string GenerateUploadToken(string fileName, long fileSize)
    {
        var timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        var payload = $"{fileName}|{fileSize}|{timestamp}|{_settings.ExpirationMinutes}";
        var signature = ComputeHmac(payload);
        return $"{payload}|{signature}";
    }

    public bool ValidateUploadToken(string token, string fileName, long fileSize)
    {
        if (string.IsNullOrWhiteSpace(token))
            return false;

        var parts = token.Split('|');
        if (parts.Length != 5)
            return false;

        var tokenFileName = parts[0];
        var tokenFileSize = parts[1];
        var timestampStr = parts[2];
        var expirationMinutes = parts[3];
        var signature = parts[4];

        if (tokenFileName != fileName)
            return false;

        if (!long.TryParse(tokenFileSize, out var tokenSize) || tokenSize != fileSize)
            return false;

        if (!long.TryParse(timestampStr, out var timestamp))
            return false;

        if (!IsValidUnixTimestamp(timestamp))
            return false;

        if (!int.TryParse(expirationMinutes, out var minutes) || minutes <= 0)
            return false;

        DateTimeOffset createdAt;
        try
        {
            createdAt = DateTimeOffset.FromUnixTimeSeconds(timestamp);
        }
        catch (ArgumentOutOfRangeException)
        {
            return false;
        }

        DateTimeOffset expiresAt;
        try
        {
            expiresAt = createdAt.AddMinutes(minutes);
        }
        catch (ArgumentOutOfRangeException)
        {
            return false;
        }

        if (DateTimeOffset.UtcNow > expiresAt)
            return false;

        var payload = $"{tokenFileName}|{tokenFileSize}|{timestampStr}|{expirationMinutes}";
        var expectedSignature = ComputeHmac(payload);

        return CryptographicEquals(signature, expectedSignature);
    }

    private static bool IsValidUnixTimestamp(long timestamp)
    {
        return timestamp >= MinUnixSeconds && timestamp <= MaxUnixSeconds;
    }

    private string ComputeHmac(string payload)
    {
        using var hmac = new HMACSHA256(_keyBytes);
        var payloadBytes = Encoding.UTF8.GetBytes(payload);
        var hashBytes = hmac.ComputeHash(payloadBytes);
        return Convert.ToBase64String(hashBytes);
    }

    private static bool CryptographicEquals(string a, string b)
    {
        if (a.Length != b.Length)
            return false;

        var bytesA = Encoding.UTF8.GetBytes(a);
        var bytesB = Encoding.UTF8.GetBytes(b);

        var result = 0;
        for (int i = 0; i < bytesA.Length; i++)
        {
            result |= bytesA[i] ^ bytesB[i];
        }
        return result == 0;
    }
}
