using CloudDesktop.Api.Data;
using CloudDesktop.Api.Models;
using CloudDesktop.Api.Models.Enums;
using Microsoft.EntityFrameworkCore;

namespace CloudDesktop.Api.Services;

public interface ISessionRecordingService
{
    Task<List<SessionRecording>> GetRecordingsBySessionAsync(Guid sessionId);
    Task<List<SessionRecording>> GetRecordingsByUserAsync(Guid userId);
    Task<List<SessionRecording>> GetRecordingsByDesktopAsync(Guid desktopId);
    Task<SessionRecording?> GetRecordingByIdAsync(Guid id);
    Task<SessionRecording?> StartRecordingAsync(Guid sessionId, RecordingQuality quality = RecordingQuality.Medium);
    Task<bool> StopRecordingAsync(Guid recordingId);
    Task<bool> PauseRecordingAsync(Guid recordingId);
    Task<bool> ResumeRecordingAsync(Guid recordingId);
    Task<bool> DeleteRecordingAsync(Guid recordingId);
    Task<bool> UpdateRecordingStatusAsync(Guid recordingId, RecordingStatus status, long? fileSize = null, string? errorMessage = null);
}

public class SessionRecordingService : ISessionRecordingService
{
    private readonly ApplicationDbContext _context;

    public SessionRecordingService(ApplicationDbContext context)
    {
        _context = context;
    }

    public async Task<List<SessionRecording>> GetRecordingsBySessionAsync(Guid sessionId)
    {
        return await _context.SessionRecordings
            .Include(sr => sr.Session)
            .Include(sr => sr.User)
            .Include(sr => sr.Desktop)
            .Where(sr => sr.SessionId == sessionId)
            .OrderByDescending(sr => sr.CreatedAt)
            .ToListAsync();
    }

    public async Task<List<SessionRecording>> GetRecordingsByUserAsync(Guid userId)
    {
        return await _context.SessionRecordings
            .Include(sr => sr.Session)
            .Include(sr => sr.User)
            .Include(sr => sr.Desktop)
            .Where(sr => sr.UserId == userId)
            .OrderByDescending(sr => sr.CreatedAt)
            .ToListAsync();
    }

    public async Task<List<SessionRecording>> GetRecordingsByDesktopAsync(Guid desktopId)
    {
        return await _context.SessionRecordings
            .Include(sr => sr.Session)
            .Include(sr => sr.User)
            .Include(sr => sr.Desktop)
            .Where(sr => sr.DesktopId == desktopId)
            .OrderByDescending(sr => sr.CreatedAt)
            .ToListAsync();
    }

    public async Task<SessionRecording?> GetRecordingByIdAsync(Guid id)
    {
        return await _context.SessionRecordings
            .Include(sr => sr.Session)
            .Include(sr => sr.User)
            .Include(sr => sr.Desktop)
            .FirstOrDefaultAsync(sr => sr.Id == id);
    }

    public async Task<SessionRecording?> StartRecordingAsync(Guid sessionId, RecordingQuality quality = RecordingQuality.Medium)
    {
        var session = await _context.Sessions
            .Include(s => s.Desktop)
            .FirstOrDefaultAsync(s => s.Id == sessionId);

        if (session == null) return null;
        if (session.Status != SessionStatus.Active) return null;

        var desktop = session.Desktop;
        if (!desktop.SessionRecordingEnabled) return null;

        var existingRecording = await _context.SessionRecordings
            .FirstOrDefaultAsync(sr => sr.SessionId == sessionId &&
                (sr.Status == RecordingStatus.Recording || sr.Status == RecordingStatus.Paused));

        if (existingRecording != null) return existingRecording;

        var (width, height, fps) = GetQualitySettings(quality);
        var timestamp = DateTime.UtcNow.ToString("yyyyMMddHHmmss");
        var fileName = $"recording_{session.UserId}_{session.DesktopId}_{timestamp}.mp4";
        var filePath = Path.Combine("recordings", session.DesktopPoolId.ToString(), fileName);

        var recording = new SessionRecording
        {
            Id = Guid.NewGuid(),
            SessionId = sessionId,
            DesktopId = session.DesktopId,
            UserId = session.UserId,
            FileName = fileName,
            FilePath = filePath,
            Status = RecordingStatus.Recording,
            Quality = quality,
            Width = width,
            Height = height,
            Fps = fps,
            IncludeAudio = true,
            IncludeCursor = true,
            StartedAt = DateTime.UtcNow,
            CreatedAt = DateTime.UtcNow
        };

        _context.SessionRecordings.Add(recording);
        await _context.SaveChangesAsync();

        return recording;
    }

    public async Task<bool> StopRecordingAsync(Guid recordingId)
    {
        var recording = await _context.SessionRecordings.FindAsync(recordingId);
        if (recording == null) return false;
        if (recording.Status != RecordingStatus.Recording && recording.Status != RecordingStatus.Paused) return false;

        recording.Status = RecordingStatus.Stopped;
        recording.StoppedAt = DateTime.UtcNow;
        if (recording.StartedAt.HasValue)
        {
            recording.Duration = recording.StoppedAt.Value - recording.StartedAt.Value;
        }
        recording.UpdatedAt = DateTime.UtcNow;

        await _context.SaveChangesAsync();
        return true;
    }

    public async Task<bool> PauseRecordingAsync(Guid recordingId)
    {
        var recording = await _context.SessionRecordings.FindAsync(recordingId);
        if (recording == null) return false;
        if (recording.Status != RecordingStatus.Recording) return false;

        recording.Status = RecordingStatus.Paused;
        recording.UpdatedAt = DateTime.UtcNow;

        await _context.SaveChangesAsync();
        return true;
    }

    public async Task<bool> ResumeRecordingAsync(Guid recordingId)
    {
        var recording = await _context.SessionRecordings.FindAsync(recordingId);
        if (recording == null) return false;
        if (recording.Status != RecordingStatus.Paused) return false;

        recording.Status = RecordingStatus.Recording;
        recording.UpdatedAt = DateTime.UtcNow;

        await _context.SaveChangesAsync();
        return true;
    }

    public async Task<bool> DeleteRecordingAsync(Guid recordingId)
    {
        var recording = await _context.SessionRecordings.FindAsync(recordingId);
        if (recording == null) return false;

        _context.SessionRecordings.Remove(recording);
        await _context.SaveChangesAsync();

        if (!string.IsNullOrEmpty(recording.FilePath) && File.Exists(recording.FilePath))
        {
            try
            {
                File.Delete(recording.FilePath);
            }
            catch
            {
            }
        }

        return true;
    }

    public async Task<bool> UpdateRecordingStatusAsync(Guid recordingId, RecordingStatus status, long? fileSize = null, string? errorMessage = null)
    {
        var recording = await _context.SessionRecordings.FindAsync(recordingId);
        if (recording == null) return false;

        recording.Status = status;
        if (fileSize.HasValue) recording.FileSizeBytes = fileSize.Value;
        if (!string.IsNullOrEmpty(errorMessage)) recording.ErrorMessage = errorMessage;
        recording.UpdatedAt = DateTime.UtcNow;

        await _context.SaveChangesAsync();
        return true;
    }

    private (int width, int height, int fps) GetQualitySettings(RecordingQuality quality)
    {
        return quality switch
        {
            RecordingQuality.Low => (854, 480, 15),
            RecordingQuality.Medium => (1280, 720, 24),
            RecordingQuality.High => (1920, 1080, 30),
            RecordingQuality.Ultra => (2560, 1440, 60),
            _ => (1920, 1080, 30)
        };
    }
}
