#include "ftp_connection.h"
#include <QDebug>
#include <QRegularExpression>

FtpConnection::FtpConnection(QObject *parent) :
    QObject(parent),
    m_controlSocket(new QTcpSocket(this)),
    m_dataSocket(new QTcpSocket(this)),
    m_port(21),
    m_isConnected(false),
    m_lastReplyCode(0),
    m_waitingForPassiveMode(false),
    m_waitingForList(false)
{
    connect(m_controlSocket, &QTcpSocket::connected, this, &FtpConnection::onControlSocketConnected);
    connect(m_controlSocket, &QTcpSocket::readyRead, this, &FtpConnection::onControlSocketReadyRead);
    connect(m_controlSocket, &QTcpSocket::disconnected, this, &FtpConnection::onControlSocketDisconnected);
    connect(m_controlSocket, static_cast<void(QAbstractSocket::*)(QAbstractSocket::SocketError)>(&QAbstractSocket::error),
            this, &FtpConnection::onControlSocketError);

    connect(m_dataSocket, &QTcpSocket::connected, this, &FtpConnection::onDataSocketConnected);
    connect(m_dataSocket, &QTcpSocket::readyRead, this, &FtpConnection::onDataSocketReadyRead);
    connect(m_dataSocket, &QTcpSocket::disconnected, this, &FtpConnection::onDataSocketDisconnected);
}

FtpConnection::~FtpConnection()
{
    disconnectFromServer();
}

void FtpConnection::connectToServer(const QString &host, int port, const QString &user, const QString &password)
{
    m_host = host;
    m_port = port;
    m_user = user;
    m_password = password;
    m_currentPath = "/";
    m_controlBuffer.clear();
    m_commandQueue.clear();
    m_isConnected = false;

    if (m_controlSocket->isOpen()) {
        m_controlSocket->close();
    }

    m_controlSocket->connectToHost(m_host, m_port);
}

void FtpConnection::disconnectFromServer()
{
    if (m_isConnected) {
        sendCommand("QUIT");
    }

    if (m_dataSocket->isOpen()) {
        m_dataSocket->close();
    }

    if (m_controlSocket->isOpen()) {
        m_controlSocket->close();
    }

    m_isConnected = false;
}

void FtpConnection::listDirectory(const QString &path)
{
    if (!m_isConnected) return;

    m_pendingListPath = path;
    m_waitingForList = true;
    m_dataBuffer.clear();
    enterPassiveMode();
}

bool FtpConnection::isConnected() const
{
    return m_isConnected;
}

void FtpConnection::sendCommand(const QString &command)
{
    if (m_controlSocket->isOpen() && m_controlSocket->state() == QAbstractSocket::ConnectedState) {
        QString cmd = command + "\r\n";
        m_controlSocket->write(cmd.toUtf8());
        m_controlSocket->flush();
    }
}

void FtpConnection::onControlSocketConnected()
{
}

void FtpConnection::onControlSocketReadyRead()
{
    m_controlBuffer.append(m_controlSocket->readAll());

    while (m_controlBuffer.contains("\r\n")) {
        int index = m_controlBuffer.indexOf("\r\n");
        QString line = QString::fromUtf8(m_controlBuffer.left(index));
        m_controlBuffer.remove(0, index + 2);

        int replyCode = parseReplyCode(line);
        if (replyCode > 0) {
            m_lastReplyCode = replyCode;
            m_lastReplyMessage = line.mid(4);
            processReply();
        }
    }
}

int FtpConnection::parseReplyCode(const QString &line)
{
    if (line.length() >= 3 && line[0].isDigit()) {
        return line.left(3).toInt();
    }
    return 0;
}

void FtpConnection::processReply()
{
    switch (m_lastReplyCode) {
    case 220:
        if (!m_isConnected) {
            sendCommand(QString("USER %1").arg(m_user));
        }
        break;

    case 331:
        sendCommand(QString("PASS %1").arg(m_password));
        break;

    case 230:
        m_isConnected = true;
        emit connected();
        break;

    case 227:
        if (m_waitingForPassiveMode) {
            m_waitingForPassiveMode = false;
            processPassiveModeResponse(m_lastReplyMessage);
        }
        break;

    case 150:
    case 125:
        break;

    case 226:
        if (m_waitingForList && m_dataBuffer.size() > 0) {
            QList<FtpFileInfo> fileList = parseListResponse(m_dataBuffer);
            emit listReceived(fileList);
            m_waitingForList = false;
            m_dataBuffer.clear();
        }
        break;

    case 221:
    case 231:
        m_isConnected = false;
        emit disconnected();
        break;

    case 530:
        emit error(tr("登录失败: 用户名或密码错误"));
        break;

    case 550:
        emit error(tr("操作失败: %1").arg(m_lastReplyMessage));
        break;

    default:
        if (m_lastReplyCode >= 500) {
            emit error(tr("FTP 错误: %1").arg(m_lastReplyMessage));
        }
        break;
    }
}

void FtpConnection::processPassiveModeResponse(const QString &response)
{
    QRegularExpression re("(\\d+),(\\d+),(\\d+),(\\d+),(\\d+),(\\d+)");
    QRegularExpressionMatchIterator it = re.globalMatch(response);

    if (it.hasNext()) {
        QRegularExpressionMatch match = it.next();
        QString ip = QString("%1.%2.%3.%4")
            .arg(match.captured(1).toInt())
            .arg(match.captured(2).toInt())
            .arg(match.captured(3).toInt())
            .arg(match.captured(4).toInt());
        quint16 port1 = static_cast<quint16>(match.captured(5).toUInt());
        quint16 port2 = static_cast<quint16>(match.captured(6).toUInt());
        int port = (static_cast<int>(port1) * 256) + static_cast<int>(port2);

        m_dataSocket->connectToHost(ip, port);
    }
}

void FtpConnection::onControlSocketDisconnected()
{
    m_isConnected = false;
    emit disconnected();
}

void FtpConnection::onControlSocketError(QAbstractSocket::SocketError errorCode)
{
    Q_UNUSED(errorCode)
    emit error(tr("连接错误: %1").arg(m_controlSocket->errorString()));
}

void FtpConnection::onDataSocketConnected()
{
    if (m_waitingForList) {
        QString path = m_pendingListPath;
        if (path.isEmpty()) path = "/";
        sendCommand(QString("LIST %1").arg(path));
    }
}

void FtpConnection::onDataSocketReadyRead()
{
    m_dataBuffer.append(m_dataSocket->readAll());
}

void FtpConnection::onDataSocketDisconnected()
{
}

void FtpConnection::enterPassiveMode()
{
    m_waitingForPassiveMode = true;
    sendCommand("PASV");
}

QList<FtpFileInfo> FtpConnection::parseListResponse(const QByteArray &data)
{
    QList<FtpFileInfo> fileList;
    QStringList lines = QString::fromUtf8(data).split("\r\n", QString::SkipEmptyParts);

    for (const QString &line : lines) {
        if (line.isEmpty()) continue;

        FtpFileInfo info;
        info.name = "";
        info.size = 0;
        info.isDir = false;
        info.lastModified = QDateTime();

        if (line.startsWith("d") || line.startsWith('-') || line.startsWith('l')) {
            QRegularExpression re("^([dl-])([rwxstST-]+)\\s+(\\d+)\\s+(\\w+)\\s+(\\w+)\\s+(\\d+)\\s+(\\w+\\s+\\d+\\s+\\d{1,2}:\\d{2}|\\w+\\s+\\d+\\s+\\d{4})\\s+(.+)$");
            QRegularExpressionMatch match = re.match(line);

            if (match.hasMatch()) {
                QString type = match.captured(1);
                QString sizeStr = match.captured(6);
                QString dateStr = match.captured(7);
                QString name = match.captured(8);

                info.name = name;
                info.size = sizeStr.toLongLong();
                info.isDir = (type == "d");

                if (dateStr.contains(":")) {
                    QRegularExpression dateRe("(\\w+)\\s+(\\d+)\\s+(\\d{1,2}):(\\d{2})");
                    QRegularExpressionMatch dateMatch = dateRe.match(dateStr);
                    if (dateMatch.hasMatch()) {
                        int year = QDate::currentDate().year();
                        QString month = dateMatch.captured(1);
                        int day = dateMatch.captured(2).toInt();
                        int hour = dateMatch.captured(3).toInt();
                        int minute = dateMatch.captured(4).toInt();

                        QMap<QString, int> monthMap;
                        monthMap["Jan"] = 1; monthMap["Feb"] = 2; monthMap["Mar"] = 3;
                        monthMap["Apr"] = 4; monthMap["May"] = 5; monthMap["Jun"] = 6;
                        monthMap["Jul"] = 7; monthMap["Aug"] = 8; monthMap["Sep"] = 9;
                        monthMap["Oct"] = 10; monthMap["Nov"] = 11; monthMap["Dec"] = 12;

                        int monthNum = monthMap.value(month, 1);
                        info.lastModified = QDateTime(QDate(year, monthNum, day), QTime(hour, minute));
                    }
                } else {
                    QRegularExpression dateRe("(\\w+)\\s+(\\d+)\\s+(\\d{4})");
                    QRegularExpressionMatch dateMatch = dateRe.match(dateStr);
                    if (dateMatch.hasMatch()) {
                        int year = dateMatch.captured(3).toInt();
                        QString month = dateMatch.captured(1);
                        int day = dateMatch.captured(2).toInt();

                        QMap<QString, int> monthMap;
                        monthMap["Jan"] = 1; monthMap["Feb"] = 2; monthMap["Mar"] = 3;
                        monthMap["Apr"] = 4; monthMap["May"] = 5; monthMap["Jun"] = 6;
                        monthMap["Jul"] = 7; monthMap["Aug"] = 8; monthMap["Sep"] = 9;
                        monthMap["Oct"] = 10; monthMap["Nov"] = 11; monthMap["Dec"] = 12;

                        int monthNum = monthMap.value(month, 1);
                        info.lastModified = QDateTime(QDate(year, monthNum, day), QTime(0, 0));
                    }
                }

                fileList.append(info);
            }
        }
    }

    return fileList;
}
