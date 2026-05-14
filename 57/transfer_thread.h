#ifndef TRANSFER_THREAD_H
#define TRANSFER_THREAD_H

#include <QThread>
#include <QString>
#include <QTcpSocket>
#include <QFile>

class TransferThread : public QThread
{
    Q_OBJECT

public:
    enum TransferMode {
        Download,
        Upload
    };

    struct TransferInfo {
        TransferMode mode;
        QString localFile;
        QString remoteFile;
        QString host;
        int port;
        QString user;
        QString password;
        qint64 resumePosition;
        bool enableResume;
    };

    explicit TransferThread(QObject *parent = nullptr);
    ~TransferThread();

    void setTransferMode(TransferMode mode);
    void setLocalFile(const QString &filePath);
    void setRemoteFile(const QString &filePath);
    void setFtpParams(const QString &host, int port, const QString &user, const QString &password);
    void setTransferInfo(const TransferInfo &info);
    void setResumePosition(qint64 position);
    void setResumeEnabled(bool enabled);
    qint64 getResumePosition() const;

signals:
    void progress(qint64 bytesTransferred, qint64 bytesTotal);
    void started(const QString &fileName, bool isUpload);
    void finished(const QString &fileName, bool success);
    void error(const QString &errorMessage);
    void resumed(const QString &fileName, qint64 resumePosition);

protected:
    void run() override;

private:
    bool connectToFtp();
    bool enterPassiveMode(QString &dataHost, int &dataPort);
    bool login();
    bool downloadFile();
    bool uploadFile();
    bool seekRemoteFile(qint64 position);
    qint64 getRemoteFileSize();
    qint64 getLocalFileSize();
    int sendCommand(const QString &command, QString &response);
    int parseReplyCode(const QString &line);
    bool parsePassiveResponse(const QString &response, QString &host, int &port);

    TransferInfo m_transferInfo;
    TransferMode m_mode;
    QString m_localFile;
    QString m_remoteFile;
    QString m_host;
    int m_port;
    QString m_user;
    QString m_password;
    QTcpSocket *m_controlSocket;
    QTcpSocket *m_dataSocket;
    bool m_stopFlag;
};

#endif // TRANSFER_THREAD_H
