using System.Collections.Concurrent;
using System.Net.WebSockets;
using System.Text;
using CloudDesktop.Api.Data;
using CloudDesktop.Api.Models.Guacamole;
using Microsoft.EntityFrameworkCore;

namespace CloudDesktop.Api.Services.Guacamole;

public interface IGuacamoleTunnel
{
    Task HandleWebSocketAsync(WebSocket webSocket, Guid connectionId, Guid userId, string clientIp);
    Task DisconnectSessionAsync(Guid sessionId);
    int GetActiveConnectionCount();
    IEnumerable<Guid> GetActiveSessionIds();
}

public class GuacamoleTunnel : IGuacamoleTunnel
{
    private static readonly ConcurrentDictionary<Guid, WebSocket> _activeConnections = new();
    private static readonly ConcurrentDictionary<Guid, CancellationTokenSource> _cancellationTokenSources = new();
    private readonly IServiceScopeFactory _scopeFactory;
    private readonly IGuacamoleParameterGenerator _parameterGenerator;
    private readonly ILogger<GuacamoleTunnel> _logger;

    public GuacamoleTunnel(
        IServiceScopeFactory scopeFactory,
        IGuacamoleParameterGenerator parameterGenerator,
        ILogger<GuacamoleTunnel> logger)
    {
        _scopeFactory = scopeFactory;
        _parameterGenerator = parameterGenerator;
        _logger = logger;
    }

    public async Task HandleWebSocketAsync(WebSocket webSocket, Guid connectionId, Guid userId, string clientIp)
    {
        var sessionId = Guid.NewGuid();
        var cts = new CancellationTokenSource();
        _cancellationTokenSources[sessionId] = cts;
        _activeConnections[sessionId] = webSocket;

        GuacamoleSession? session = null;
        Stream? recordingStream = null;

        try
        {
            using var scope = _scopeFactory.CreateScope();
            var context = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();

            var connection = await context.GuacamoleConnections
                .FirstOrDefaultAsync(c => c.Id == connectionId && c.IsActive);

            if (connection == null)
            {
                await SendErrorAsync(webSocket, "Connection not found");
                return;
            }

            var user = await context.Users.FindAsync(userId);
            if (user == null)
            {
                await SendErrorAsync(webSocket, "User not found");
                return;
            }

            session = new GuacamoleSession
            {
                Id = sessionId,
                ConnectionId = connectionId,
                UserId = userId,
                ConnectionName = connection.Name,
                Protocol = connection.Protocol,
                State = GuacamoleConnectionState.Connecting,
                ClientIpAddress = clientIp,
                DisplayWidth = connection.Width,
                DisplayHeight = connection.Height,
                DisplayDpi = connection.Dpi,
                HasRecording = connection.EnableRecording
            };
            context.GuacamoleSessions.Add(session);
            await context.SaveChangesAsync();

            if (connection.EnableRecording && !string.IsNullOrEmpty(connection.RecordingPath))
            {
                var recordingDir = Path.GetDirectoryName(connection.RecordingPath);
                if (!string.IsNullOrEmpty(recordingDir) && !Directory.Exists(recordingDir))
                {
                    Directory.CreateDirectory(recordingDir);
                }
                var recordingFilePath = Path.Combine(connection.RecordingPath, $"{sessionId}.guac");
                recordingStream = new FileStream(recordingFilePath, FileMode.Create, FileAccess.Write, FileShare.Read);
                session.RecordingPath = recordingFilePath;
            }

            var parameters = _parameterGenerator.GenerateParameters(connection);
            await SendHandshakeAsync(webSocket, parameters);

            session.State = GuacamoleConnectionState.Connected;
            session.ConnectedAt = DateTime.UtcNow;
            await context.SaveChangesAsync();

            await HandleDataTransferAsync(webSocket, session, context, recordingStream, cts.Token);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error in Guacamole tunnel for session {SessionId}", sessionId);
            if (session != null)
            {
                session.ErrorMessage = ex.Message;
            }
        }
        finally
        {
            if (recordingStream != null)
            {
                await recordingStream.DisposeAsync();
            }

            await CleanupSessionAsync(sessionId, session);
            _activeConnections.TryRemove(sessionId, out _);
            _cancellationTokenSources.TryRemove(sessionId, out var _);
            cts.Dispose();
        }
    }

    private async Task HandleDataTransferAsync(WebSocket webSocket, GuacamoleSession session,
        ApplicationDbContext context, Stream? recordingStream, CancellationToken cancellationToken)
    {
        var buffer = new byte[4 * 1024 * 1024];
        var parser = new GuacamoleProtocolParser();

        while (webSocket.State == WebSocketState.Open && !cancellationToken.IsCancellationRequested)
        {
            try
            {
                var result = await webSocket.ReceiveAsync(new ArraySegment<byte>(buffer), cancellationToken);

                if (result.MessageType == WebSocketMessageType.Close)
                {
                    await webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Closing", cancellationToken);
                    break;
                }

                if (result.MessageType == WebSocketMessageType.Text && result.Count > 0)
                {
                    var message = Encoding.UTF8.GetString(buffer, 0, result.Count);
                    session.BytesReceived += result.Count;

                    var instructions = parser.Feed(message);

                    foreach (var instruction in instructions)
                    {
                        await ProcessInstructionAsync(session, instruction, context);

                        if (recordingStream != null)
                        {
                            var data = Encoding.UTF8.GetBytes(instruction.ToString());
                            await recordingStream.WriteAsync(data, 0, data.Length, cancellationToken);
                        }
                    }

                    var response = GenerateServerResponse(instructions);
                    if (!string.IsNullOrEmpty(response))
                    {
                        var responseBytes = Encoding.UTF8.GetBytes(response);
                        await webSocket.SendAsync(new ArraySegment<byte>(responseBytes),
                            WebSocketMessageType.Text, true, cancellationToken);
                        session.BytesSent += responseBytes.Length;
                    }
                }
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Error processing WebSocket message for session {SessionId}", session.Id);
                break;
            }
        }
    }

    private async Task ProcessInstructionAsync(GuacamoleSession session, GuacamoleInstruction instruction,
        ApplicationDbContext context)
    {
        switch (instruction.Opcode)
        {
            case "key":
                session.KeyEventCount++;
                break;
            case "mouse":
                session.MouseEventCount++;
                break;
            case "sync":
                session.FrameCount++;
                break;
            case "disconnect":
                session.DisconnectReason = "Client initiated disconnect";
                break;
        }

        session.UpdatedAt = DateTime.UtcNow;
        await context.SaveChangesAsync();
    }

    private string GenerateServerResponse(IEnumerable<GuacamoleInstruction> instructions)
    {
        var sb = new StringBuilder();

        foreach (var instruction in instructions)
        {
            switch (instruction.Opcode)
            {
                case "size":
                    sb.Append(GuacamoleInstruction.Create("size", instruction.Args.ToArray()));
                    break;
                case "connect":
                    sb.Append(GuacamoleInstruction.Create("ready", "0"));
                    break;
            }
        }

        return sb.ToString();
    }

    private async Task SendHandshakeAsync(WebSocket webSocket, Dictionary<string, string> parameters)
    {
        var argsList = new List<string> { "VERSION_1_5_0" };
        argsList.AddRange(parameters.Keys);

        var argsInstruction = GuacamoleInstruction.Create("args", argsList.ToArray());
        var buffer = Encoding.UTF8.GetBytes(argsInstruction.ToString());
        await webSocket.SendAsync(new ArraySegment<byte>(buffer), WebSocketMessageType.Text, true, CancellationToken.None);
    }

    private async Task SendErrorAsync(WebSocket webSocket, string message)
    {
        var instruction = GuacamoleInstruction.Create("error", message, "1");
        var buffer = Encoding.UTF8.GetBytes(instruction.ToString());
        await webSocket.SendAsync(new ArraySegment<byte>(buffer), WebSocketMessageType.Text, true, CancellationToken.None);
        await webSocket.CloseAsync(WebSocketCloseStatus.InternalServerError, message, CancellationToken.None);
    }

    private async Task CleanupSessionAsync(Guid sessionId, GuacamoleSession? session)
    {
        using var scope = _scopeFactory.CreateScope();
        var context = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();

        if (session == null)
        {
            session = await context.GuacamoleSessions.FindAsync(sessionId);
        }

        if (session != null)
        {
            session.State = GuacamoleConnectionState.Disconnected;
            session.DisconnectedAt = DateTime.UtcNow;
            if (session.ConnectedAt.HasValue)
            {
                session.Duration = session.DisconnectedAt - session.ConnectedAt;
            }
            session.UpdatedAt = DateTime.UtcNow;

            if (!string.IsNullOrEmpty(session.RecordingPath) && File.Exists(session.RecordingPath))
            {
                var fileInfo = new FileInfo(session.RecordingPath);
                session.RecordingSizeBytes = fileInfo.Length;
            }

            await context.SaveChangesAsync();
        }
    }

    public async Task DisconnectSessionAsync(Guid sessionId)
    {
        if (_cancellationTokenSources.TryGetValue(sessionId, out var cts))
        {
            await cts.CancelAsync();
        }

        if (_activeConnections.TryGetValue(sessionId, out var webSocket) &&
            webSocket.State == WebSocketState.Open)
        {
            try
            {
                await webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Admin initiated disconnect",
                    CancellationToken.None);
            }
            catch
            {
                // Ignore cleanup errors
            }
        }
    }

    public int GetActiveConnectionCount() => _activeConnections.Count;

    public IEnumerable<Guid> GetActiveSessionIds() => _activeConnections.Keys;
}
