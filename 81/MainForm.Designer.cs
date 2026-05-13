namespace BiliLiveMonitor;

partial class MainForm
{
    private System.ComponentModel.IContainer components = null;

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            if (components != null)
            {
                components.Dispose();
            }
            _checker?.Dispose();
            _notification?.Dispose();
            _trayMenu?.Dispose();
        }
        base.Dispose(disposing);
    }
}
