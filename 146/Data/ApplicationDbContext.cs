using CloudDesktop.Api.Models;
using CloudDesktop.Api.Models.Guacamole;
using Microsoft.EntityFrameworkCore;

namespace CloudDesktop.Api.Data;

public class ApplicationDbContext : DbContext
{
    public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options)
        : base(options)
    {
    }

    public DbSet<DesktopPool> DesktopPools { get; set; }
    public DbSet<Desktop> Desktops { get; set; }
    public DbSet<Session> Sessions { get; set; }
    public DbSet<User> Users { get; set; }
    public DbSet<UserQuota> UserQuotas { get; set; }
    public DbSet<PortAllocation> PortAllocations { get; set; }
    public DbSet<GpuDevice> GpuDevices { get; set; }
    public DbSet<GpuAssignment> GpuAssignments { get; set; }
    public DbSet<SessionRecording> SessionRecordings { get; set; }
    public DbSet<ClipboardConfiguration> ClipboardConfigurations { get; set; }
    public DbSet<ClipboardAuditLog> ClipboardAuditLogs { get; set; }
    public DbSet<DesktopHealthCheck> DesktopHealthChecks { get; set; }
    public DbSet<DesktopHealthConfiguration> DesktopHealthConfigurations { get; set; }
    public DbSet<RecoveryHistory> RecoveryHistories { get; set; }
    public DbSet<DesktopMetrics> DesktopMetrics { get; set; }

    // Guacamole Entities
    public DbSet<GuacamoleConnection> GuacamoleConnections { get; set; }
    public DbSet<GuacamoleSession> GuacamoleSessions { get; set; }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        modelBuilder.Entity<DesktopPool>()
            .HasMany(dp => dp.Desktops)
            .WithOne(d => d.DesktopPool)
            .HasForeignKey(d => d.DesktopPoolId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<DesktopPool>()
            .HasMany(dp => dp.UserQuotas)
            .WithOne(uq => uq.DesktopPool)
            .HasForeignKey(uq => uq.DesktopPoolId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<Desktop>()
            .HasMany(d => d.Sessions)
            .WithOne(s => s.Desktop)
            .HasForeignKey(s => s.DesktopId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<User>()
            .HasMany(u => u.Sessions)
            .WithOne(s => s.User)
            .HasForeignKey(s => s.UserId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<User>()
            .HasMany(u => u.UserQuotas)
            .WithOne(uq => uq.User)
            .HasForeignKey(uq => uq.UserId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<UserQuota>()
            .HasIndex(uq => new { uq.UserId, uq.DesktopPoolId })
            .IsUnique();

        modelBuilder.Entity<DesktopPool>()
            .HasMany(dp => dp.PortAllocations)
            .WithOne(pa => pa.DesktopPool)
            .HasForeignKey(pa => pa.DesktopPoolId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<PortAllocation>()
            .HasIndex(pa => new { pa.DesktopPoolId, pa.PortNumber })
            .IsUnique();

        modelBuilder.Entity<GpuDevice>()
            .HasMany(g => g.GpuAssignments)
            .WithOne(ga => ga.GpuDevice)
            .HasForeignKey(ga => ga.GpuDeviceId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<Desktop>()
            .HasMany(d => d.GpuAssignments)
            .WithOne(ga => ga.Desktop)
            .HasForeignKey(ga => ga.DesktopId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<GpuAssignment>()
            .HasIndex(ga => new { ga.GpuDeviceId, ga.DesktopId })
            .IsUnique();

        modelBuilder.Entity<SessionRecording>()
            .HasIndex(sr => sr.SessionId);

        modelBuilder.Entity<SessionRecording>()
            .HasIndex(sr => sr.UserId);

        modelBuilder.Entity<ClipboardConfiguration>()
            .HasIndex(cc => cc.DesktopPoolId);

        modelBuilder.Entity<ClipboardConfiguration>()
            .HasIndex(cc => cc.DesktopId);

        modelBuilder.Entity<ClipboardConfiguration>()
            .HasIndex(cc => cc.UserId);

        modelBuilder.Entity<ClipboardAuditLog>()
            .HasIndex(cal => cal.SessionId);

        modelBuilder.Entity<ClipboardAuditLog>()
            .HasIndex(cal => cal.UserId);

        modelBuilder.Entity<ClipboardAuditLog>()
            .HasIndex(cal => cal.Timestamp);

        modelBuilder.Entity<DesktopHealthCheck>()
            .HasIndex(dhc => dhc.DesktopId);

        modelBuilder.Entity<DesktopHealthCheck>()
            .HasIndex(dhc => dhc.CheckedAt);

        modelBuilder.Entity<DesktopHealthConfiguration>()
            .HasIndex(dhc => dhc.DesktopPoolId);

        modelBuilder.Entity<DesktopHealthConfiguration>()
            .HasIndex(dhc => dhc.DesktopId);

        modelBuilder.Entity<RecoveryHistory>()
            .HasIndex(rh => rh.DesktopId);

        modelBuilder.Entity<RecoveryHistory>()
            .HasIndex(rh => rh.StartedAt);

        modelBuilder.Entity<DesktopMetrics>()
            .HasIndex(dm => dm.DesktopId);

        modelBuilder.Entity<DesktopMetrics>()
            .HasIndex(dm => dm.Timestamp);
    }
}
