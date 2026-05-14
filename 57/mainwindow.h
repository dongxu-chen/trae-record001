#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QTreeWidgetItem>
#include <QList>
#include <QTableWidgetItem>
#include "ftp_connection.h"
#include "transfer_thread.h"
#include "local_browser.h"
#include "site_manager.h"
#include "log_widget.h"

namespace Ui {
class MainWindow;
}

struct QueueItem {
    TransferThread::TransferInfo transferInfo;
    int priority;
    enum Status { Pending, Running, Completed, Failed, Paused } status;
    QString errorMessage;
    qint64 transferred;
    qint64 total;

    QueueItem() : priority(0), status(Pending), transferred(0), total(0) {}
};

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    explicit MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

private slots:
    void onConnectClicked();
    void onDisconnectClicked();
    void onRemoteItemDoubleClicked(QTreeWidgetItem *item, int column);
    void onUploadClicked();
    void onDownloadClicked();
    void onFtpConnected();
    void onFtpDisconnected();
    void onFtpError(const QString &error);
    void onFtpListReceived(const QList<FtpFileInfo> &fileList);
    void onTransferProgress(qint64 bytesTransferred, qint64 bytesTotal);
    void onTransferStarted(const QString &fileName, bool isUpload);
    void onTransferFinished(const QString &fileName, bool success);
    void onTransferError(const QString &error);
    void onTransferResumed(const QString &fileName, qint64 resumePosition);

    void onAddToQueueClicked();
    void onRemoveFromQueueClicked();
    void onStartQueueClicked();
    void onPauseQueueClicked();
    void onClearQueueClicked();
    void onMoveQueueUpClicked();
    void onMoveQueueDownClicked();

    void onSaveSiteClicked();
    void onLoadSiteClicked();
    void onDeleteSiteClicked();
    void onSiteSelected(const QString &siteName);

    void onQueueItemDoubleClicked(int row, int column);

private:
    void setupUI();
    void connectSignals();
    void populateRemoteTree(const QList<FtpFileInfo> &fileList);
    QString getSelectedRemoteFile();
    QString getSelectedLocalFile();
    void appendLog(const QString &message);

    void addToQueue(const TransferThread::TransferInfo &info);
    void processQueue();
    void updateQueueTable();
    QueueItem* getCurrentQueueItem();
    void loadSiteComboBox();

    Ui::MainWindow *ui;
    FtpConnection *m_ftpConnection;
    TransferThread *m_transferThread;
    LocalBrowser *m_localBrowser;
    SiteManager *m_siteManager;
    LogWidget *m_logWidget;

    bool m_connected;
    QString m_currentRemotePath;

    QList<QueueItem> m_transferQueue;
    int m_currentQueueIndex;
    bool m_queueRunning;
    bool m_queuePaused;
};

#endif // MAINWINDOW_H
