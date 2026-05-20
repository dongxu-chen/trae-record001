using CloudDesktop.Api.Data;
using CloudDesktop.Api.Services;
using CloudDesktop.Api.Services.Guacamole;
using Microsoft.EntityFrameworkCore;
using Microsoft.OpenApi.Models;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();

builder.Services.AddDbContext<ApplicationDbContext>(options =>
    options.UseInMemoryDatabase("CloudDesktopDb"));

builder.Services.AddScoped<IPortPoolService, PortPoolService>();
builder.Services.AddScoped<IGpuService, GpuService>();
builder.Services.AddScoped<ISessionRecordingService, SessionRecordingService>();
builder.Services.AddScoped<IClipboardService, ClipboardService>();
builder.Services.AddScoped<IHealthCheckService, HealthCheckService>();
builder.Services.AddScoped<IDesktopPoolService, DesktopPoolService>();
builder.Services.AddScoped<ISessionService, SessionService>();
builder.Services.AddScoped<IUserQuotaService, UserQuotaService>();
builder.Services.AddScoped<IConnectionBrokerService, ConnectionBrokerService>();
builder.Services.AddScoped<IGuacamoleParameterGenerator, GuacamoleParameterGenerator>();
builder.Services.AddSingleton<IGuacamoleTunnel, GuacamoleTunnel>();

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new OpenApiInfo
    {
        Title = "Cloud Desktop Management API",
        Version = "v1",
        Description = "API for managing cloud desktop pools, sessions, connection brokering, user quotas, GPU passthrough, session recording, clipboard control, health checks, and Apache Guacamole HTML5 client with RDP/VNC/SSH support"
    });
});

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI(c =>
    {
        c.SwaggerEndpoint("/swagger/v1/swagger.json", "Cloud Desktop Management API v1");
    });
}

app.UseWebSockets();
app.UseHttpsRedirection();
app.UseStaticFiles();
app.UseAuthorization();
app.MapControllers();

app.MapGet("/", async context =>
{
    context.Response.Redirect("/index.html");
    await Task.CompletedTask;
});

using (var scope = app.Services.CreateScope())
{
    var services = scope.ServiceProvider;
    var context = services.GetRequiredService<ApplicationDbContext>();
    await SeedData.Initialize(context);
}

app.Run();
