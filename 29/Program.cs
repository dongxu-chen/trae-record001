using FileStorageService.Models;
using FileStorageService.Services;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

builder.Services.AddSingleton<IFileRepository, InMemoryFileRepository>();
builder.Services.AddScoped<ITokenService, TokenService>();
builder.Services.AddScoped<IChunkService, ChunkService>();
builder.Services.AddScoped<IDeduplicationService, DeduplicationService>();
builder.Services.AddHostedService<BackgroundCleanupService>();

var uploadPath = builder.Configuration.GetValue<string>("UploadSettings:UploadPath") ?? "uploads";
var fullUploadPath = Path.Combine(Directory.GetCurrentDirectory(), uploadPath);
if (!Directory.Exists(fullUploadPath))
{
    Directory.CreateDirectory(fullUploadPath);
}

var chunkPath = builder.Configuration.GetValue<string>("UploadSettings:ChunkPath") ?? "chunks";
var fullChunkPath = Path.Combine(Directory.GetCurrentDirectory(), chunkPath);
if (!Directory.Exists(fullChunkPath))
{
    Directory.CreateDirectory(fullChunkPath);
}

builder.Services.Configure<UploadSettings>(builder.Configuration.GetSection("UploadSettings"));
builder.Services.Configure<TokenSettings>(builder.Configuration.GetSection("TokenSettings"));

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseHttpsRedirection();

app.UseAuthorization();

app.MapControllers();

app.Run();
