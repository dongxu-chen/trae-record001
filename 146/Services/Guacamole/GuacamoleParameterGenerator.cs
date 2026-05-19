using CloudDesktop.Api.Models.Guacamole;

namespace CloudDesktop.Api.Services.Guacamole;

public interface IGuacamoleParameterGenerator
{
    Dictionary<string, string> GenerateParameters(GuacamoleConnection connection);
    Dictionary<string, string> GenerateRdpParameters(GuacamoleConnection connection);
    Dictionary<string, string> GenerateVncParameters(GuacamoleConnection connection);
    Dictionary<string, string> GenerateSshParameters(GuacamoleConnection connection);
}

public class GuacamoleParameterGenerator : IGuacamoleParameterGenerator
{
    public Dictionary<string, string> GenerateParameters(GuacamoleConnection connection)
    {
        return connection.Protocol switch
        {
            GuacamoleProtocol.RDP => GenerateRdpParameters(connection),
            GuacamoleProtocol.VNC => GenerateVncParameters(connection),
            GuacamoleProtocol.SSH => GenerateSshParameters(connection),
            _ => throw new NotSupportedException($"Protocol {connection.Protocol} is not supported")
        };
    }

    public Dictionary<string, string> GenerateRdpParameters(GuacamoleConnection connection)
    {
        var parameters = new Dictionary<string, string>
        {
            ["protocol"] = "rdp",
            ["hostname"] = connection.Hostname,
            ["port"] = (connection.Port > 0 ? connection.Port : 3389).ToString(),
            ["width"] = connection.Width.ToString(),
            ["height"] = connection.Height.ToString(),
            ["dpi"] = connection.Dpi.ToString(),
            ["color-depth"] = connection.ColorDepth.ToString(),
            ["audio"] = connection.EnableAudio.ToString().ToLower(),
            ["enable-audio-input"] = connection.EnableAudioInput.ToString().ToLower(),
            ["enable-printing"] = connection.EnablePrinting.ToString().ToLower(),
            ["enable-drive"] = connection.EnableDrive.ToString().ToLower(),
            ["disable-wallpaper"] = (!connection.EnableWallpaper).ToString().ToLower(),
            ["disable-theming"] = (!connection.EnableTheming).ToString().ToLower(),
            ["enable-font-smoothing"] = connection.EnableFontSmoothing.ToString().ToLower(),
            ["disable-full-window-drag"] = (!connection.EnableFullWindowDrag).ToString().ToLower(),
            ["disable-desktop-composition"] = (!connection.EnableDesktopComposition).ToString().ToLower(),
            ["disable-menu-animations"] = (!connection.EnableMenuAnimations).ToString().ToLower(),
            ["disable-glyph-wrapping"] = connection.DisableGlyphWrapping.ToString().ToLower(),
            ["ignore-cert"] = connection.IgnoreCert.ToString().ToLower(),
            ["recording"] = connection.EnableRecording.ToString().ToLower()
        };

        if (!string.IsNullOrEmpty(connection.Username))
            parameters["username"] = connection.Username;

        if (!string.IsNullOrEmpty(connection.Password))
            parameters["password"] = connection.Password;

        if (!string.IsNullOrEmpty(connection.Domain))
            parameters["domain"] = connection.Domain;

        if (!string.IsNullOrEmpty(connection.DrivePath))
            parameters["drive-path"] = connection.DrivePath;

        if (connection.EnableRemoteApp && !string.IsNullOrEmpty(connection.RemoteAppProgram))
        {
            parameters["remote-app"] = "true";
            parameters["remote-app-program"] = connection.RemoteAppProgram;
            if (!string.IsNullOrEmpty(connection.RemoteAppArgs))
                parameters["remote-app-args"] = connection.RemoteAppArgs;
            if (!string.IsNullOrEmpty(connection.RemoteAppDir))
                parameters["remote-app-dir"] = connection.RemoteAppDir;
        }

        if (!string.IsNullOrEmpty(connection.RecordingPath) && connection.EnableRecording)
        {
            parameters["recording-path"] = connection.RecordingPath;
            parameters["recording-name"] = $"recording-{DateTime.UtcNow:yyyyMMddHHmmss}";
        }

        return parameters;
    }

    public Dictionary<string, string> GenerateVncParameters(GuacamoleConnection connection)
    {
        var parameters = new Dictionary<string, string>
        {
            ["protocol"] = "vnc",
            ["hostname"] = connection.Hostname,
            ["port"] = (connection.Port > 0 ? connection.Port : 5900).ToString(),
            ["width"] = connection.Width.ToString(),
            ["height"] = connection.Height.ToString(),
            ["dpi"] = connection.Dpi.ToString(),
            ["cursor"] = connection.EnableVncCursor.ToString().ToLower(),
            ["compression-level"] = connection.VncCompressionLevel.ToString(),
            ["jpeg"] = connection.EnableVncJpeg.ToString().ToLower(),
            ["jpeg-quality"] = connection.VncJpegQuality.ToString(),
            ["swap-red-blue"] = connection.EnableVncSwapRedBlue.ToString().ToLower(),
            ["read-only"] = connection.EnableVncReadOnly.ToString().ToLower(),
            ["recording"] = connection.EnableRecording.ToString().ToLower()
        };

        if (!string.IsNullOrEmpty(connection.Username))
            parameters["username"] = connection.Username;

        if (!string.IsNullOrEmpty(connection.Password))
            parameters["password"] = connection.Password;

        if (!string.IsNullOrEmpty(connection.RecordingPath) && connection.EnableRecording)
        {
            parameters["recording-path"] = connection.RecordingPath;
            parameters["recording-name"] = $"recording-{DateTime.UtcNow:yyyyMMddHHmmss}";
        }

        return parameters;
    }

    public Dictionary<string, string> GenerateSshParameters(GuacamoleConnection connection)
    {
        var parameters = new Dictionary<string, string>
        {
            ["protocol"] = "ssh",
            ["hostname"] = connection.Hostname,
            ["port"] = (connection.Port > 0 ? connection.Port : 22).ToString(),
            ["width"] = connection.Width.ToString(),
            ["height"] = connection.Height.ToString(),
            ["dpi"] = connection.Dpi.ToString(),
            ["font-size"] = connection.SshFontSize.ToString(),
            ["enable-sftp"] = connection.SshEnableSftp.ToString().ToLower(),
            ["recording"] = connection.EnableRecording.ToString().ToLower()
        };

        if (!string.IsNullOrEmpty(connection.SshFontName))
            parameters["font-name"] = connection.SshFontName;

        if (!string.IsNullOrEmpty(connection.Username))
            parameters["username"] = connection.Username;

        if (!string.IsNullOrEmpty(connection.Password))
            parameters["password"] = connection.Password;

        if (!string.IsNullOrEmpty(connection.SshPrivateKey))
            parameters["private-key"] = connection.SshPrivateKey;

        if (!string.IsNullOrEmpty(connection.SshPassphrase))
            parameters["passphrase"] = connection.SshPassphrase;

        if (!string.IsNullOrEmpty(connection.SshHostKey))
            parameters["host-key"] = connection.SshHostKey;

        if (!string.IsNullOrEmpty(connection.RecordingPath) && connection.EnableRecording)
        {
            parameters["recording-path"] = connection.RecordingPath;
            parameters["recording-name"] = $"recording-{DateTime.UtcNow:yyyyMMddHHmmss}";
        }

        return parameters;
    }
}
