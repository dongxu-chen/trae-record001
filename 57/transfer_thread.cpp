#include "transfer_thread.h"
#include <QFileInfo>
#include <QRegularExpression>
#include <QDebug>

TransferThread::TransferThread(QObject *parent) :
    QThread(parent),
    m_mode(Download),
    m_port(21),
    m_controlSocket(nullptr),
    m_dataSocket(nullptr),
    m_stopFlag(false)
{
    m_transferInfo.mode = Download;
    m_transferInfo.port = 21;
    m_transferInfo.resumePosition = 0;
    m_transferInfo.enableResume = true;
}

TransferThread::~TransferThread()
{
    m_stopFlag = true;
    wait();
}

void TransferThread::setTransferMode(TransferMode mode)
{
    m_mode = mode;
    m_transferInfo.mode = mode;
}

void TransferThread::setLocalFile(const QString &filePath)
{
    m_localFile = filePath;
    m_transferInfo.localFile = filePath;
}

void TransferThread::setRemoteFile(const QString &filePath)
{
    m_remoteFile = filePath;
    m_transferInfo.remoteFile = filePath;
}

void TransferThread::setFtpParams(const QString &host, int port, const QString &user, const QString &password)
{
    m_host = host;
    m_port = port;
    m_user = user;
    m_password = password;
    m_transferInfo.host = host;
    m_transferInfo.port = port;
    m_transferInfo.user = user;
    m_transferInfo.password = password;
}

void TransferThread::setTransferInfo(const TransferInfo &info)
{
    m_transferInfo = info;
    m_mode = info.mode;
    m_localFile = info.localFile;
    m_remoteFile = info.remoteFile;
    m_host = info.host;
    m_port = info.port;
    m_user = info.user;
    m_password = info.password;
}

void TransferThread::setResumePosition(qint64 position)
{
    m_transferInfo.resumePosition = position;
}

void TransferThread::setResumeEnabled(bool enabled)
{
    m_transferInfo.enableResume = enabled;
}

qint64 TransferThread::getResumePosition() const
{
    return m_transferInfo.resumePosition;
}

void TransferThread::run()
{
    m_stopFlag = false;
    m_controlSocket = new QTcpSocket();
    m_dataSocket = new QTcpSocket();

    QString fileName = (m_mode == Upload) ? QFileInfo(m_localFile).fileName() : QFileInfo(m_remoteFile).fileName();
    emit started(fileName, m_mode == Upload);

    bool success = false;

    if (connectToFtp() && login()) {
        if (m_mode == Download) {
            success = downloadFile();
        } else {
            success = uploadFile();
        }
    }

    if (m_controlSocket->isOpen()) {
        QString response;
        sendCommand("QUIT", response);
        m_controlSocket->close();
    }

    if (m_dataSocket->isOpen()) {
        m_dataSocket->close();
    }

    delete m_controlSocket;
    delete m_dataSocket;
    m_controlSocket = nullptr;
    m_dataSocket = nullptr;

    emit finished(fileName, success);
}

bool TransferThread::connectToFtp()
{
    m_controlSocket->connectToHost(m_host, m_port);
    if (!m_controlSocket->waitForConnected(10000)) {
        emit error(tr("无法连接到服务器: %1").arg(m_controlSocket->errorString()));
        return false;
    }

    QString response;
    int code = 0;

    if (m_controlSocket->waitForReadyRead(10000)) {
        response = QString::fromUtf8(m_controlSocket->readAll());
        code = parseReplyCode(response);
    }

    if (code != 220) {
        emit error(tr("服务器未响应连接请求"));
        return false;
    }

    return true;
}

bool TransferThread::login()
{
    QString response;
    int code;

    code = sendCommand(QString("USER %1").arg(m_user), response);
    if (code != 331 && code != 230) {
        emit error(tr("用户名错误"));
        return false;
    }

    if (code == 331) {
        code = sendCommand(QString("PASS %1").arg(m_password), response);
        if (code != 230) {
            emit error(tr("密码错误"));
            return false;
        }
    }

    return true;
}

bool TransferThread::enterPassiveMode(QString &dataHost, int &dataPort)
{
    QString response;
    int code = sendCommand("PASV", response);

    if (code != 227) {
        emit error(tr("无法进入被动模式"));
        return false;
    }

    return parsePassiveResponse(response, dataHost, dataPort);
}

bool TransferThread::parsePassiveResponse(const QString &response, QString &host, int &port)
{
    QRegularExpression re("(\\d+),(\\d+),(\\d+),(\\d+),(\\d+),(\\d+)");
    QRegularExpressionMatchIterator it = re.globalMatch(response);

    if (it.hasNext()) {
        QRegularExpressionMatch match = it.next();
        host = QString("%1.%2.%3.%4")
            .arg(match.captured(1).toInt())
            .arg(match.captured(2).toInt())
            .arg(match.captured(3).toInt())
            .arg(match.captured(4).toInt());
        quint16 port1 = static_cast<quint16>(match.captured(5).toUInt());
        quint16 port2 = static_cast<quint16>(match.captured(6).toUInt());
        port = (static_cast<int>(port1) * 256) + static_cast<int>(port2);
        return true;
    }

    return false;
}

bool TransferThread::downloadFile()
{
    QString dataHost;
    int dataPort;

    qint64 totalBytes = -1;
    qint64 resumePos = 0;
    QString response;

    int code = sendCommand(QString("SIZE %1").arg(m_remoteFile), response);
    if (code == 213) {
        QRegularExpression re("\\d+\\s+(\\d+)");
        QRegularExpressionMatchIterator it = re.globalMatch(response);
        if (it.hasNext()) {
            totalBytes = it.next().captured(1).toLongLong();
        }
    }

    if (m_transferInfo.enableResume) {
        QFileInfo localInfo(m_localFile);
        if (localInfo.exists() && localInfo.isFile() && localInfo.size() > 0) {
            if (m_transferInfo.resumePosition > 0) {
                resumePos = m_transferInfo.resumePosition;
            } else {
                resumePos = localInfo.size();
            }

            if (resumePos > 0 && totalBytes > 0 && resumePos < totalBytes) {
                if (seekRemoteFile(resumePos)) {
                    emit resumed(QFileInfo(m_remoteFile).fileName(), resumePos);
                } else {
                    resumePos = 0;
                }
            } else if (resumePos >= totalBytes && totalBytes > 0) {
                emit error(tr("文件已下载完成"));
                return true;
            }
        }
    }

    if (!enterPassiveMode(dataHost, dataPort)) {
        return false;
    }

    m_dataSocket->connectToHost(dataHost, dataPort);
    if (!m_dataSocket->waitForConnected(10000)) {
        emit error(tr("无法连接到数据端口: %1").arg(m_dataSocket->errorString()));
        return false;
    }

    code = sendCommand(QString("RETR %1").arg(m_remoteFile), response);
    if (code != 150 && code != 125) {
        emit error(tr("无法开始下载: %1").arg(response));
        m_dataSocket->close();
        return false;
    }

    if (totalBytes <= 0) {
        QRegularExpression re("(\\d+)\\s+(?:bytes|octets)");
        QRegularExpressionMatchIterator it = re.globalMatch(response);
        if (it.hasNext()) {
            totalBytes = it.next().captured(1).toLongLong();
        }
    }

    QFile file(m_localFile);
    QIODevice::OpenMode openMode = QIODevice::WriteOnly;
    if (resumePos > 0) {
        openMode = QIODevice::WriteOnly | QIODevice::Append;
    }
    if (!file.open(openMode)) {
        emit error(tr("无法打开本地文件: %1").arg(file.errorString()));
        m_dataSocket->close();
        return false;
    }

    qint64 bytesReceived = resumePos;
    const int bufferSize = 65536;
    char buffer[bufferSize];

    while (!m_stopFlag) {
        if (m_dataSocket->waitForReadyRead(30000)) {
            qint64 bytesRead = m_dataSocket->read(buffer, bufferSize);
            if (bytesRead > 0) {
                file.write(buffer, bytesRead);
                bytesReceived += bytesRead;
                emit progress(bytesReceived, totalBytes);
            } else if (bytesRead == 0) {
                break;
            }
        } else {
            if (m_dataSocket->state() == QAbstractSocket::UnconnectedState) {
                break;
            }
        }
    }

    file.close();
    m_dataSocket->close();

    if (m_controlSocket->waitForReadyRead(10000)) {
        response = QString::fromUtf8(m_controlSocket->readAll());
    }

    return !m_stopFlag;
}

bool TransferThread::uploadFile()
{
    QString response;
    qint64 resumePos = 0;
    qint64 totalBytes = getLocalFileSize();

    if (totalBytes <= 0) {
        emit error(tr("本地文件不存在或为空"));
        return false;
    }

    if (m_transferInfo.enableResume) {
        qint64 remoteSize = getRemoteFileSize();
        if (remoteSize > 0 && remoteSize < totalBytes) {
            if (m_transferInfo.resumePosition > 0) {
                resumePos = m_transferInfo.resumePosition;
            } else {
                resumePos = remoteSize;
            }

            if (resumePos > 0 && resumePos < totalBytes) {
                if (seekRemoteFile(resumePos)) {
                    emit resumed(QFileInfo(m_localFile).fileName(), resumePos);
                } else {
                    resumePos = 0;
                }
            } else if (resumePos >= totalBytes) {
                emit error(tr("文件已上传完成"));
                return true;
            }
        }
    }

    QString dataHost;
    int dataPort;

    if (!enterPassiveMode(dataHost, dataPort)) {
        return false;
    }

    m_dataSocket->connectToHost(dataHost, dataPort);
    if (!m_dataSocket->waitForConnected(10000)) {
        emit error(tr("无法连接到数据端口: %1").arg(m_dataSocket->errorString()));
        return false;
    }

    QString storCommand = (resumePos > 0) ? QString("APPE %1").arg(m_remoteFile) 
                                           : QString("STOR %1").arg(m_remoteFile);
    int code = sendCommand(storCommand, response);
    if (code != 150 && code != 125) {
        emit error(tr("无法开始上传: %1").arg(response));
        m_dataSocket->close();
        return false;
    }

    QFile file(m_localFile);
    if (!file.open(QIODevice::ReadOnly)) {
        emit error(tr("无法打开本地文件: %1").arg(file.errorString()));
        m_dataSocket->close();
        return false;
    }

    if (resumePos > 0) {
        if (!file.seek(resumePos)) {
            emit error(tr("无法定位到续传位置"));
            file.close();
            m_dataSocket->close();
            return false;
        }
    }

    qint64 bytesSent = resumePos;
    const int bufferSize = 65536;
    char buffer[bufferSize];

    while (!m_stopFlag && !file.atEnd()) {
        qint64 bytesRead = file.read(buffer, bufferSize);
        if (bytesRead > 0) {
            qint64 bytesWritten = m_dataSocket->write(buffer, bytesRead);
            if (bytesWritten != bytesRead) {
                emit error(tr("写入数据失败"));
                break;
            }
            m_dataSocket->flush();
            bytesSent += bytesWritten;
            emit progress(bytesSent, totalBytes);
        }
    }

    file.close();
    m_dataSocket->close();

    if (m_controlSocket->waitForReadyRead(30000)) {
        response = QString::fromUtf8(m_controlSocket->readAll());
    }

    return !m_stopFlag;
}

bool TransferThread::seekRemoteFile(qint64 position)
{
    QString response;
    int code = sendCommand(QString("REST %1").arg(position), response);
    return (code == 350);
}

qint64 TransferThread::getRemoteFileSize()
{
    QString response;
    int code = sendCommand(QString("SIZE %1").arg(m_remoteFile), response);
    if (code == 213) {
        QRegularExpression re("\\d+\\s+(\\d+)");
        QRegularExpressionMatchIterator it = re.globalMatch(response);
        if (it.hasNext()) {
            return it.next().captured(1).toLongLong();
        }
    }
    return -1;
}

qint64 TransferThread::getLocalFileSize()
{
    QFileInfo info(m_localFile);
    if (info.exists() && info.isFile()) {
        return info.size();
    }
    return -1;
}

int TransferThread::sendCommand(const QString &command, QString &response)
{
    QString cmd = command + "\r\n";
    m_controlSocket->write(cmd.toUtf8());
    m_controlSocket->flush();

    response.clear();
    int replyCode = 0;

    if (m_controlSocket->waitForReadyRead(30000)) {
        QByteArray data = m_controlSocket->readAll();
        response = QString::fromUtf8(data);
        replyCode = parseReplyCode(response);
    }

    return replyCode;
}

int TransferThread::parseReplyCode(const QString &line)
{
    if (line.length() >= 3 && line[0].isDigit()) {
        return line.left(3).toInt();
    }
    return 0;
}
