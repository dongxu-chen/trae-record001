#ifndef FTP_CONNECTION_H
#define FTP_CONNECTION_H

#include <QObject>
#include <QString>
#include <QList>
#include <QDateTime>
#include <QTcpSocket>

struct FtpFileInfo {
    QString name;
    qint64 size;
    bool isDir;
    QDateTime lastModified;
};

class FtpConnection : public QObject
{
    Q_OBJECT

public:
    explicit FtpConnection(QObject *parent = nullptr);
    ~FtpConnection();

    void connectToServer(const QString &host, int port, const QString &user, const QString &password);
    void disconnectFromServer();
    void listDirectory(const QString &path);
    bool isConnected() const;

signals:
    void connected();
    void disconnected();
    void error(const QString &errorMessage);
    void listReceived(const QList<FtpFileInfo> &fileList);

private slots:
    void onControlSocketConnected();
    void onControlSocketReadyRead();
    void onControlSocketDisconnected();
    void onControlSocketError(QAbstractSocket::SocketError);
    void onDataSocketConnected();
    void onDataSocketReadyRead();
    void onDataSocketDisconnected();

private:
    void sendCommand(const QString &command);
    void processReply();
    int parseReplyCode(const QString &line);
    QList<FtpFileInfo> parseListResponse(const QByteArray &data);
    void enterPassiveMode();
    void processPassiveModeResponse(const QString &response);

    QTcpSocket *m_controlSocket;
    QTcpSocket *m_dataSocket;
    QString m_host;
    int m_port;
    QString m_user;
    QString m_password;
    QString m_currentPath;
    bool m_isConnected;
    QByteArray m_controlBuffer;
    QByteArray m_dataBuffer;
    QString m_pendingListPath;
    QStringList m_commandQueue;
    int m_lastReplyCode;
    QString m_lastReplyMessage;
    bool m_waitingForPassiveMode;
    bool m_waitingForList;
};

#endif // FTP_CONNECTION_H
