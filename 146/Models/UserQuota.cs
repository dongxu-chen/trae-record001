using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace CloudDesktop.Api.Models;

public class UserQuota
{
    [Key]
    public Guid Id { get; set; }

    [Required]
    [ForeignKey(nameof(User))]
    public Guid UserId { get; set; }

    [Required]
    [ForeignKey(nameof(DesktopPool))]
    public Guid DesktopPoolId { get; set; }

    public int MaxConcurrentSessions { get; set; } = 1;

    public int CurrentActiveSessions { get; set; } = 0;

    public int MaxDailySessionMinutes { get; set; } = 480;

    public int TodayUsedMinutes { get; set; } = 0;

    public int MaxMonthlySessionMinutes { get; set; } = 9600;

    public int MonthUsedMinutes { get; set; } = 0;

    public DateTime? LastResetDate { get; set; }

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    public DateTime? UpdatedAt { get; set; }

    public User User { get; set; } = null!;

    public DesktopPool DesktopPool { get; set; } = null!;
}
