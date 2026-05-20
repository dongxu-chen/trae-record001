using CloudDesktop.Api.Models;
using CloudDesktop.Api.Models.Enums;

namespace CloudDesktop.Api.Data;

public static class SeedData
{
    public static async Task Initialize(ApplicationDbContext context)
    {
        if (!context.Users.Any())
        {
            var users = new List<User>
            {
                new User
                {
                    Id = Guid.NewGuid(),
                    Username = "admin",
                    Email = "admin@clouddesktop.com",
                    FullName = "System Administrator",
                    Department = "IT",
                    IsActive = true,
                    CreatedAt = DateTime.UtcNow
                },
                new User
                {
                    Id = Guid.NewGuid(),
                    Username = "john.doe",
                    Email = "john.doe@clouddesktop.com",
                    FullName = "John Doe",
                    Department = "Engineering",
                    IsActive = true,
                    CreatedAt = DateTime.UtcNow
                },
                new User
                {
                    Id = Guid.NewGuid(),
                    Username = "jane.smith",
                    Email = "jane.smith@clouddesktop.com",
                    FullName = "Jane Smith",
                    Department = "Finance",
                    IsActive = true,
                    CreatedAt = DateTime.UtcNow
                }
            };

            context.Users.AddRange(users);
            await context.SaveChangesAsync();
        }

        if (!context.DesktopPools.Any())
        {
            var adminUser = context.Users.First(u => u.Username == "admin");
            var johnUser = context.Users.First(u => u.Username == "john.doe");
            var janeUser = context.Users.First(u => u.Username == "jane.smith");

            var engineeringPool = new DesktopPool
            {
                Id = Guid.NewGuid(),
                Name = "Engineering Pool",
                Description = "Desktop pool for engineering department",
                Status = DesktopPoolStatus.Available,
                MaxDesktops = 10,
                CurrentDesktops = 3,
                DefaultProtocol = ConnectionProtocol.RDP,
                DefaultPort = 3389,
                PortRangeStart = 3389,
                PortRangeEnd = 3489,
                CpuCores = 4,
                MemoryGB = 16,
                StorageGB = 200,
                CreatedAt = DateTime.UtcNow
            };

            var financePool = new DesktopPool
            {
                Id = Guid.NewGuid(),
                Name = "Finance Pool",
                Description = "Desktop pool for finance department",
                Status = DesktopPoolStatus.Available,
                MaxDesktops = 5,
                CurrentDesktops = 2,
                DefaultProtocol = ConnectionProtocol.RDP,
                DefaultPort = 3389,
                PortRangeStart = 3490,
                PortRangeEnd = 3590,
                CpuCores = 2,
                MemoryGB = 8,
                StorageGB = 100,
                CreatedAt = DateTime.UtcNow
            };

            context.DesktopPools.AddRange(engineeringPool, financePool);
            await context.SaveChangesAsync();

            var engineeringDesktops = new List<Desktop>
            {
                new Desktop
                {
                    Id = Guid.NewGuid(),
                    DesktopPoolId = engineeringPool.Id,
                    Name = "ENG-Desktop-001",
                    ComputerName = "ENG001",
                    IpAddress = "192.168.1.101",
                    Port = 3389,
                    Status = DesktopStatus.Available,
                    Protocol = ConnectionProtocol.RDP,
                    CpuCores = 4,
                    MemoryGB = 16,
                    StorageGB = 200,
                    CreatedAt = DateTime.UtcNow
                },
                new Desktop
                {
                    Id = Guid.NewGuid(),
                    DesktopPoolId = engineeringPool.Id,
                    Name = "ENG-Desktop-002",
                    ComputerName = "ENG002",
                    IpAddress = "192.168.1.102",
                    Port = 3389,
                    Status = DesktopStatus.Available,
                    Protocol = ConnectionProtocol.RDP,
                    CpuCores = 4,
                    MemoryGB = 16,
                    StorageGB = 200,
                    CreatedAt = DateTime.UtcNow
                },
                new Desktop
                {
                    Id = Guid.NewGuid(),
                    DesktopPoolId = engineeringPool.Id,
                    Name = "ENG-Desktop-003",
                    ComputerName = "ENG003",
                    IpAddress = "192.168.1.103",
                    Port = 3389,
                    Status = DesktopStatus.Available,
                    Protocol = ConnectionProtocol.RDP,
                    CpuCores = 4,
                    MemoryGB = 16,
                    StorageGB = 200,
                    CreatedAt = DateTime.UtcNow
                }
            };

            var financeDesktops = new List<Desktop>
            {
                new Desktop
                {
                    Id = Guid.NewGuid(),
                    DesktopPoolId = financePool.Id,
                    Name = "FIN-Desktop-001",
                    ComputerName = "FIN001",
                    IpAddress = "192.168.1.201",
                    Port = 3389,
                    Status = DesktopStatus.Available,
                    Protocol = ConnectionProtocol.RDP,
                    CpuCores = 2,
                    MemoryGB = 8,
                    StorageGB = 100,
                    CreatedAt = DateTime.UtcNow
                },
                new Desktop
                {
                    Id = Guid.NewGuid(),
                    DesktopPoolId = financePool.Id,
                    Name = "FIN-Desktop-002",
                    ComputerName = "FIN002",
                    IpAddress = "192.168.1.202",
                    Port = 3389,
                    Status = DesktopStatus.Available,
                    Protocol = ConnectionProtocol.RDP,
                    CpuCores = 2,
                    MemoryGB = 8,
                    StorageGB = 100,
                    CreatedAt = DateTime.UtcNow
                }
            };

            context.Desktops.AddRange(engineeringDesktops);
            context.Desktops.AddRange(financeDesktops);
            await context.SaveChangesAsync();

            var quotas = new List<UserQuota>
            {
                new UserQuota
                {
                    Id = Guid.NewGuid(),
                    UserId = johnUser.Id,
                    DesktopPoolId = engineeringPool.Id,
                    MaxConcurrentSessions = 2,
                    CurrentActiveSessions = 0,
                    MaxDailySessionMinutes = 480,
                    TodayUsedMinutes = 0,
                    MaxMonthlySessionMinutes = 9600,
                    MonthUsedMinutes = 0,
                    CreatedAt = DateTime.UtcNow
                },
                new UserQuota
                {
                    Id = Guid.NewGuid(),
                    UserId = janeUser.Id,
                    DesktopPoolId = financePool.Id,
                    MaxConcurrentSessions = 1,
                    CurrentActiveSessions = 0,
                    MaxDailySessionMinutes = 480,
                    TodayUsedMinutes = 0,
                    MaxMonthlySessionMinutes = 9600,
                    MonthUsedMinutes = 0,
                    CreatedAt = DateTime.UtcNow
                }
            };

            context.UserQuotas.AddRange(quotas);
            await context.SaveChangesAsync();

            var engineeringPortAllocations = new List<PortAllocation>();
            for (int port = engineeringPool.PortRangeStart; port <= engineeringPool.PortRangeEnd; port++)
            {
                var allocation = new PortAllocation
                {
                    Id = Guid.NewGuid(),
                    DesktopPoolId = engineeringPool.Id,
                    PortNumber = port,
                    IsAllocated = false,
                    CreatedAt = DateTime.UtcNow
                };

                var desktop = engineeringDesktops.FirstOrDefault(d => d.Port == port);
                if (desktop != null)
                {
                    allocation.DesktopId = desktop.Id;
                    allocation.IsAllocated = true;
                    allocation.AllocatedAt = DateTime.UtcNow;
                }

                engineeringPortAllocations.Add(allocation);
            }

            var financePortAllocations = new List<PortAllocation>();
            for (int port = financePool.PortRangeStart; port <= financePool.PortRangeEnd; port++)
            {
                var allocation = new PortAllocation
                {
                    Id = Guid.NewGuid(),
                    DesktopPoolId = financePool.Id,
                    PortNumber = port,
                    IsAllocated = false,
                    CreatedAt = DateTime.UtcNow
                };

                var desktop = financeDesktops.FirstOrDefault(d => d.Port == port);
                if (desktop != null)
                {
                    allocation.DesktopId = desktop.Id;
                    allocation.IsAllocated = true;
                    allocation.AllocatedAt = DateTime.UtcNow;
                }

                financePortAllocations.Add(allocation);
            }

            context.PortAllocations.AddRange(engineeringPortAllocations);
            context.PortAllocations.AddRange(financePortAllocations);
            await context.SaveChangesAsync();
        }
    }
}
