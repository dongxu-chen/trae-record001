using System.Diagnostics;
using System.IO;
using System.Text;
using BiliLiveMonitor.Models;

namespace BiliLiveMonitor;

public class Notification : IDisposable
{
    private readonly NotifyIcon _notifyIcon;
    private readonly Form _ownerForm;
    private readonly bool _canUseToast;
    private readonly string _appId;

    public event EventHandler? Click;

    public Notification(Form owner)
    {
        _ownerForm = owner;
        _appId = "BiliLiveMonitor";
        _notifyIcon = new NotifyIcon
        {
            Icon = SystemIcons.Application,
            Visible = true,
            Text = "B站直播监控"
        };

        _notifyIcon.MouseClick += (s, e) =>
        {
            if (e.Button == MouseButtons.Left)
            {
                Click?.Invoke(this, EventArgs.Empty);
            }
        };

        _notifyIcon.DoubleClick += (s, e) =>
        {
            Click?.Invoke(this, EventArgs.Empty);
        };

        _canUseToast = CheckCanUseToast();
    }

    private bool CheckCanUseToast()
    {
        if (Environment.OSVersion.Version < new Version(10, 0, 14393))
            return false;

        try
        {
            EnsureAppRegistration();
            return true;
        }
        catch
        {
            return false;
        }
    }

    private void EnsureAppRegistration()
    {
        try
        {
            var shortcutDir = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                "Microsoft", "Windows", "Start Menu", "Programs"
            );
            var shortcutPath = Path.Combine(shortcutDir, "B站直播监控.lnk");

            if (!File.Exists(shortcutPath))
            {
                CreateShortcut(shortcutPath);
            }
        }
        catch
        {
        }
    }

    private void CreateShortcut(string shortcutPath)
    {
        try
        {
            var exePath = Application.ExecutablePath;

            if (string.IsNullOrEmpty(exePath) || exePath.EndsWith(".dll"))
            {
                exePath = Process.GetCurrentProcess().MainModule?.FileName ?? string.Empty;
            }

            if (string.IsNullOrEmpty(exePath))
                return;

            var psScript = $@"
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{shortcutPath.Replace("'", "''")}')
$Shortcut.TargetPath = '{exePath.Replace("'", "''")}'
$Shortcut.WorkingDirectory = '{Path.GetDirectoryName(exePath)?.Replace("'", "''") ?? ""}'
$Shortcut.Description = 'B站直播监控'
$Shortcut.Save()
";
            ExecutePowerShellScript(psScript);
        }
        catch
        {
        }
    }

    public void ShowLiveNotification(LiveRoom room)
    {
        if (!IsVisible()) return;

        var title = $"{room.UName} 开播了！";
        var message = string.IsNullOrEmpty(room.Title) ? "直播间" : room.Title;

        if (_canUseToast)
        {
            try
            {
                ShowToastNotification(title, message, room.Cover);
                return;
            }
            catch
            {
            }
        }

        _notifyIcon.ShowBalloonTip(5000, title, message, ToolTipIcon.Info);
    }

    public void ShowMessage(string title, string message, ToolTipIcon icon = ToolTipIcon.Info)
    {
        if (!IsVisible()) return;

        if (_canUseToast)
        {
            try
            {
                ShowToastNotification(title, message, string.Empty);
                return;
            }
            catch
            {
            }
        }

        _notifyIcon.ShowBalloonTip(3000, title, message, icon);
    }

    private void ShowToastNotification(string title, string message, string imageUrl)
    {
        var xml = BuildToastXml(title, message, imageUrl);

        var psScript = $@"
$ErrorActionPreference = 'SilentlyContinue'
Add-Type -AssemblyName System.Windows.Forms
$app = '{_appId}'

$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$textElements = $template.GetElementsByTagName('text')
$textElements.Item(0).AppendChild($template.CreateTextNode('{EscapeForPs(title)}'))
$textElements.Item(1).AppendChild($template.CreateTextNode('{EscapeForPs(message)}'))

$toast = New-Object Windows.UI.Notifications.ToastNotification($template)
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app)
$notifier.Show($toast)
";
        ExecutePowerShellScript(psScript);
    }

    private string BuildToastXml(string title, string message, string imageUrl)
    {
        var sb = new StringBuilder();
        sb.Append("<toast><visual><binding template=\"ToastText02\">");
        sb.AppendFormat("<text id=\"1\">{0}</text>", EscapeXml(title));
        sb.AppendFormat("<text id=\"2\">{0}</text>", EscapeXml(message));
        sb.Append("</binding></visual></toast>");
        return sb.ToString();
    }

    private string EscapeXml(string value)
    {
        return value
            .Replace("&", "&amp;")
            .Replace("<", "&lt;")
            .Replace(">", "&gt;")
            .Replace("\"", "&quot;")
            .Replace("'", "&apos;");
    }

    private string EscapeForPs(string value)
    {
        return value
            .Replace("'", "''")
            .Replace("\"", "`\"")
            .Replace("`", "``");
    }

    private void ExecutePowerShellScript(string script)
    {
        try
        {
            var startInfo = new ProcessStartInfo
            {
                FileName = "powershell.exe",
                Arguments = $"-NoProfile -ExecutionPolicy Bypass -Command \"{script}\"",
                UseShellExecute = false,
                CreateNoWindow = true,
                WindowStyle = ProcessWindowStyle.Hidden
            };

            using var process = Process.Start(startInfo);
            process?.WaitForExit(5000);
        }
        catch
        {
            throw;
        }
    }

    public void SetContextMenu(ContextMenuStrip menu)
    {
        _notifyIcon.ContextMenuStrip = menu;
    }

    public void Hide()
    {
        _notifyIcon.Visible = false;
    }

    public void Show()
    {
        _notifyIcon.Visible = true;
    }

    public bool IsVisible()
    {
        return _notifyIcon.Visible;
    }

    public void Dispose()
    {
        _notifyIcon.Dispose();
    }
}
