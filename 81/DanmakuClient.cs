using System.IO;
using System.IO.Compression;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Threading;
using BiliLiveMonitor.Models;

namespace BiliLiveMonitor;

public class DanmakuClient : IDisposable
{
    private readonly long _roomId;
    private ClientWebSocket? _ws;
    private CancellationTokenSource? _cts;
    private System.Threading.Timer? _heartbeatTimer;
    private readonly HttpClient _httpClient;
    private bool _isRunning;
    private readonly Random _random = new();

    private const short ProtocolVersionNormal = 1;
    private const short ProtocolVersionBrotli = 3;
    private const int PacketHeaderSize = 16;
    private const int OperationHeartbeat = 2;
    private const int OperationHeartbeatReply = 3;
    private const int OperationMessage = 5;
    private const int OperationAuth = 7;
    private const int OperationAuthReply = 8;

    public event EventHandler<DanmakuMessage>? DanmakuReceived;
    public event EventHandler<GiftMessage>? GiftReceived;
    public event EventHandler<SuperChatMessage>? SuperChatReceived;
    public event EventHandler? Connected;
    public event EventHandler<string>? Disconnected;
    public event EventHandler<LiveStatusMessage>? LiveStatusChanged;

    public DanmakuClient(long roomId, HttpClient httpClient)
    {
        _roomId = roomId;
        _httpClient = httpClient;
    }

    public async Task<bool> ConnectAsync()
    {
        if (_isRunning) return true;

        try
        {
            _cts = new CancellationTokenSource();

            var (host, token, realRoomId) = await GetDanmuInfoAsync();
            if (string.IsNullOrEmpty(host) || string.IsNullOrEmpty(token))
            {
                return false;
            }

            _ws = new ClientWebSocket();
            var uri = new Uri($"wss://{host}:443/sub");
            await _ws.ConnectAsync(uri, _cts.Token);

            await SendAuthAsync(realRoomId, token);

            _isRunning = true;
            StartHeartbeat();
            _ = ReceiveLoopAsync();

            Connected?.Invoke(this, EventArgs.Empty);
            return true;
        }
        catch (Exception ex)
        {
            Disconnected?.Invoke(this, ex.Message);
            Dispose();
            return false;
        }
    }

    private async Task<(string Host, string Token, long RealRoomId)> GetDanmuInfoAsync()
    {
        try
        {
            var url = $"https://api.live.bilibili.com/xlive/web-room/v1/index/getDanmuInfo?id={_roomId}&type=0";
            using var request = new HttpRequestMessage(HttpMethod.Get, url);
            AddRequestHeaders(request);

            var response = await _httpClient.SendAsync(request);
            response.EnsureSuccessStatusCode();

            var json = await response.Content.ReadAsStringAsync();
            var jsonNode = JsonNode.Parse(json);

            if (jsonNode?["code"]?.GetValue<int>() != 0)
            {
                return (string.Empty, string.Empty, _roomId);
            }

            var data = jsonNode["data"];
            if (data == null) return (string.Empty, string.Empty, _roomId);

            var hostList = data["host_list"]?.AsArray();
            var host = hostList?.FirstOrDefault()?["host"]?.GetValue<string>() ?? "broadcastlv.chat.bilibili.com";
            var token = data["token"]?.GetValue<string>() ?? string.Empty;
            var realRoomId = data["room_id"]?.GetValue<long>() ?? _roomId;

            return (host, token, realRoomId);
        }
        catch
        {
            return ("broadcastlv.chat.bilibili.com", string.Empty, _roomId);
        }
    }

    private async Task SendAuthAsync(long realRoomId, string token)
    {
        if (_ws == null || _cts == null) return;

        var authObj = new
        {
            uid = 0,
            roomid = realRoomId,
            protover = 3,
            platform = "web",
            type = 2,
            key = token
        };

        var authJson = JsonSerializer.Serialize(authObj);
        var packet = BuildPacket(OperationAuth, authJson);

        await _ws.SendAsync(new ArraySegment<byte>(packet), WebSocketMessageType.Binary, true, _cts.Token);
    }

    private void StartHeartbeat()
    {
        _heartbeatTimer = new System.Threading.Timer(async _ =>
        {
            try
            {
                if (_ws != null && _ws.State == WebSocketState.Open && _cts != null)
                {
                    var heartbeat = BuildPacket(OperationHeartbeat, "[object Object]");
                    await _ws.SendAsync(new ArraySegment<byte>(heartbeat), WebSocketMessageType.Binary, true, _cts.Token);
                }
            }
            catch
            {
            }
        }, null, 30000, 30000);
    }

    private async Task ReceiveLoopAsync()
    {
        if (_ws == null || _cts == null) return;

        var buffer = new byte[65536];
        using var ms = new MemoryStream();

        while (_isRunning && !_cts.Token.IsCancellationRequested)
        {
            try
            {
                WebSocketReceiveResult result;
                do
                {
                    result = await _ws.ReceiveAsync(new ArraySegment<byte>(buffer), _cts.Token);
                    if (result.MessageType == WebSocketMessageType.Close)
                    {
                        await _ws.CloseAsync(WebSocketCloseStatus.NormalClosure, string.Empty, CancellationToken.None);
                        _isRunning = false;
                        break;
                    }
                    ms.Write(buffer, 0, result.Count);
                } while (!result.EndOfMessage);

                if (ms.Length > 0)
                {
                    var data = ms.ToArray();
                    ProcessPacket(data);
                }
                ms.SetLength(0);
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch (Exception ex)
            {
                if (_isRunning)
                {
                    Disconnected?.Invoke(this, ex.Message);
                }
                break;
            }
        }

        _isRunning = false;
    }

    private void ProcessPacket(byte[] data)
    {
        var offset = 0;
        while (offset < data.Length)
        {
            if (offset + PacketHeaderSize > data.Length) break;

            var packetLength = ReadInt32BigEndian(data, offset);
            var headerLength = ReadInt16BigEndian(data, offset + 4);
            var protocolVersion = ReadInt16BigEndian(data, offset + 6);
            var operation = ReadInt32BigEndian(data, offset + 8);
            var sequenceId = ReadInt32BigEndian(data, offset + 12);

            if (packetLength <= 0 || offset + packetLength > data.Length) break;

            var bodyLength = packetLength - headerLength;
            var body = new byte[bodyLength];
            Array.Copy(data, offset + headerLength, body, 0, bodyLength);

            switch (operation)
            {
                case OperationAuthReply:
                    break;
                case OperationHeartbeatReply:
                    break;
                case OperationMessage:
                    if (protocolVersion == ProtocolVersionBrotli)
                    {
                        var decompressed = DecompressBrotli(body);
                        if (decompressed != null)
                        {
                            ProcessPacket(decompressed);
                        }
                    }
                    else
                    {
                        ParseMessage(body);
                    }
                    break;
            }

            offset += packetLength;
        }
    }

    private byte[]? DecompressBrotli(byte[] compressed)
    {
        try
        {
            using var input = new MemoryStream(compressed);
            using var output = new MemoryStream();
            using var brotli = new BrotliStream(input, CompressionMode.Decompress);
            brotli.CopyTo(output);
            return output.ToArray();
        }
        catch
        {
            return null;
        }
    }

    private void ParseMessage(byte[] body)
    {
        try
        {
            var json = Encoding.UTF8.GetString(body);
            var jsonNode = JsonNode.Parse(json);
            if (jsonNode == null) return;

            var cmd = jsonNode["cmd"]?.GetValue<string>() ?? string.Empty;

            switch (cmd)
            {
                case "DANMU_MSG":
                    ParseDanmaku(jsonNode);
                    break;
                case "SEND_GIFT":
                    ParseGift(jsonNode);
                    break;
                case "SUPER_CHAT_MESSAGE":
                    ParseSuperChat(jsonNode);
                    break;
                case "SUPER_CHAT_MESSAGE_JPN":
                    ParseSuperChat(jsonNode);
                    break;
                case "LIVE":
                    LiveStatusChanged?.Invoke(this, new LiveStatusMessage { Status = 1, RoomId = _roomId });
                    break;
                case "PREPARING":
                    LiveStatusChanged?.Invoke(this, new LiveStatusMessage { Status = 0, RoomId = _roomId });
                    break;
                case "ROOM_CHANGE":
                    break;
            }
        }
        catch
        {
        }
    }

    private void ParseDanmaku(JsonNode jsonNode)
    {
        try
        {
            var info = jsonNode["info"];
            if (info == null) return;

            var infoArr = info.AsArray();
            if (infoArr.Count < 3) return;

            var content = infoArr[1]?.GetValue<string>() ?? string.Empty;

            var userInfo = infoArr[2]?.AsArray();
            var uid = userInfo?[0]?.GetValue<long>() ?? 0;
            var uname = userInfo?[1]?.GetValue<string>() ?? string.Empty;

            DanmakuReceived?.Invoke(this, new DanmakuMessage
            {
                Uid = uid,
                Uname = uname,
                Content = content,
                Timestamp = DateTime.Now,
                MsgType = 1,
                Price = 0
            });
        }
        catch
        {
        }
    }

    private void ParseGift(JsonNode jsonNode)
    {
        try
        {
            var data = jsonNode["data"];
            if (data == null) return;

            GiftReceived?.Invoke(this, new GiftMessage
            {
                Uid = data["uid"]?.GetValue<long>() ?? 0,
                Uname = data["uname"]?.GetValue<string>() ?? string.Empty,
                GiftName = data["giftName"]?.GetValue<string>() ?? string.Empty,
                GiftId = data["giftId"]?.GetValue<long>() ?? 0,
                Count = data["num"]?.GetValue<int>() ?? 1,
                Price = data["price"]?.GetValue<int>() ?? 0,
                TotalCoin = data["total_coin"]?.GetValue<int>() ?? 0,
                Timestamp = DateTime.Now
            });
        }
        catch
        {
        }
    }

    private void ParseSuperChat(JsonNode jsonNode)
    {
        try
        {
            var data = jsonNode["data"];
            if (data == null) return;

            SuperChatReceived?.Invoke(this, new SuperChatMessage
            {
                Uid = data["uid"]?.GetValue<long>() ?? 0,
                Uname = data["user_info"]?["uname"]?.GetValue<string>() ?? string.Empty,
                Content = data["message"]?.GetValue<string>() ?? string.Empty,
                Message = data["message"]?.GetValue<string>() ?? string.Empty,
                Price = data["price"]?.GetValue<int>() ?? 0,
                Timestamp = DateTime.Now
            });
        }
        catch
        {
        }
    }

    private byte[] BuildPacket(int operation, string body)
    {
        var bodyBytes = Encoding.UTF8.GetBytes(body);
        var packetLength = PacketHeaderSize + bodyBytes.Length;
        var packet = new byte[packetLength];

        WriteInt32BigEndian(packet, 0, packetLength);
        WriteInt16BigEndian(packet, 4, PacketHeaderSize);
        WriteInt16BigEndian(packet, 6, 1);
        WriteInt32BigEndian(packet, 8, operation);
        WriteInt32BigEndian(packet, 12, 1);
        Array.Copy(bodyBytes, 0, packet, PacketHeaderSize, bodyBytes.Length);

        return packet;
    }

    private void AddRequestHeaders(HttpRequestMessage request)
    {
        request.Headers.UserAgent.ParseAdd(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        );
        request.Headers.Referrer = new Uri("https://live.bilibili.com/");
    }

    private static int ReadInt32BigEndian(byte[] buffer, int offset)
    {
        return (buffer[offset] << 24) | (buffer[offset + 1] << 16) | (buffer[offset + 2] << 8) | buffer[offset + 3];
    }

    private static short ReadInt16BigEndian(byte[] buffer, int offset)
    {
        return (short)((buffer[offset] << 8) | buffer[offset + 1]);
    }

    private static void WriteInt32BigEndian(byte[] buffer, int offset, int value)
    {
        buffer[offset] = (byte)(value >> 24);
        buffer[offset + 1] = (byte)(value >> 16);
        buffer[offset + 2] = (byte)(value >> 8);
        buffer[offset + 3] = (byte)value;
    }

    private static void WriteInt16BigEndian(byte[] buffer, int offset, short value)
    {
        buffer[offset] = (byte)(value >> 8);
        buffer[offset + 1] = (byte)value;
    }

    public void Disconnect()
    {
        _isRunning = false;
        _heartbeatTimer?.Dispose();
        _heartbeatTimer = null;
        _cts?.Cancel();

        try
        {
            if (_ws != null && _ws.State == WebSocketState.Open)
            {
                _ws.CloseAsync(WebSocketCloseStatus.NormalClosure, string.Empty, CancellationToken.None).Wait(5000);
            }
        }
        catch
        {
        }

        _ws?.Dispose();
        _ws = null;
        _cts?.Dispose();
        _cts = null;
    }

    public void Dispose()
    {
        Disconnect();
    }
}

public class LiveStatusMessage
{
    public long RoomId { get; set; }
    public int Status { get; set; }
}
