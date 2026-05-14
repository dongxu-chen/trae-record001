#include "site_manager.h"
#include <QDir>
#include <QFile>
#include <QDataStream>
#include <QUuid>
#include <QDateTime>
#include <QStandardPaths>
#include <QDebug>

SiteManager::SiteManager(QObject *parent) :
    QObject(parent)
{
    QString appDataPath = QStandardPaths::writableLocation(QStandardPaths::AppDataLocation);
    QDir().mkpath(appDataPath);
    m_settingsPath = appDataPath + "/ftp_sites.dat";
    loadSites();
}

SiteManager::~SiteManager()
{
    saveSites();
}

bool SiteManager::loadSites()
{
    m_sites.clear();

    QFile file(m_settingsPath);
    if (!file.exists()) {
        return true;
    }

    if (!file.open(QIODevice::ReadOnly)) {
        qWarning() << "无法打开站点文件:" << file.errorString();
        return false;
    }

    QDataStream in(&file);
    in.setVersion(QDataStream::Qt_5_0);

    int count;
    in >> count;

    for (int i = 0; i < count; ++i) {
        SiteInfo site;
        in >> site.id;
        in >> site.name;
        in >> site.host;
        in >> site.port;
        in >> site.user;
        QString encryptedPassword;
        in >> encryptedPassword;
        site.password = decrypt(encryptedPassword);
        in >> site.localPath;
        in >> site.remotePath;
        in >> site.enableResume;
        in >> site.usePassiveMode;

        if (!site.id.isEmpty()) {
            m_sites.append(site);
        }
    }

    file.close();
    return true;
}

bool SiteManager::saveSites()
{
    QFile file(m_settingsPath);
    if (!file.open(QIODevice::WriteOnly)) {
        qWarning() << "无法保存站点文件:" << file.errorString();
        return false;
    }

    QDataStream out(&file);
    out.setVersion(QDataStream::Qt_5_0);

    out << m_sites.size();

    foreach (const SiteInfo &site, m_sites) {
        out << site.id;
        out << site.name;
        out << site.host;
        out << site.port;
        out << site.user;
        out << encrypt(site.password);
        out << site.localPath;
        out << site.remotePath;
        out << site.enableResume;
        out << site.usePassiveMode;
    }

    file.close();
    emit sitesChanged();
    return true;
}

QList<SiteInfo> SiteManager::getAllSites() const
{
    return m_sites;
}

SiteInfo SiteManager::getSite(const QString &id) const
{
    foreach (const SiteInfo &site, m_sites) {
        if (site.id == id) {
            return site;
        }
    }
    return SiteInfo();
}

bool SiteManager::addSite(const SiteInfo &site)
{
    SiteInfo newSite = site;
    if (newSite.id.isEmpty()) {
        newSite.id = generateId();
    }

    for (int i = 0; i < m_sites.size(); ++i) {
        if (m_sites[i].id == newSite.id) {
            return false;
        }
    }

    m_sites.append(newSite);
    return saveSites();
}

bool SiteManager::updateSite(const SiteInfo &site)
{
    for (int i = 0; i < m_sites.size(); ++i) {
        if (m_sites[i].id == site.id) {
            m_sites[i] = site;
            return saveSites();
        }
    }
    return false;
}

bool SiteManager::removeSite(const QString &id)
{
    for (int i = 0; i < m_sites.size(); ++i) {
        if (m_sites[i].id == id) {
            m_sites.removeAt(i);
            return saveSites();
        }
    }
    return false;
}

QString SiteManager::generateId() const
{
    return QUuid::createUuid().toString();
}

QString SiteManager::getKey() const
{
    QString machineId = QString::fromLocal8Bit(qgetenv("COMPUTERNAME"));
    if (machineId.isEmpty()) {
        machineId = QString::fromLocal8Bit(qgetenv("HOSTNAME"));
    }
    if (machineId.isEmpty()) {
        machineId = "FtpClientDefaultKey";
    }

    QByteArray hash = QCryptographicHash::hash(machineId.toUtf8(), QCryptographicHash::Sha256);
    return QString(hash.toHex().left(16));
}

QString SiteManager::encrypt(const QString &plainText) const
{
    if (plainText.isEmpty()) {
        return QString();
    }

    QString key = getKey();
    QByteArray data = plainText.toUtf8();
    QByteArray keyBytes = key.toUtf8();

    QByteArray encrypted;
    for (int i = 0; i < data.size(); ++i) {
        encrypted.append(data[i] ^ keyBytes[i % keyBytes.size()]);
    }

    return QString::fromLatin1(encrypted.toBase64());
}

QString SiteManager::decrypt(const QString &cipherText) const
{
    if (cipherText.isEmpty()) {
        return QString();
    }

    QString key = getKey();
    QByteArray data = QByteArray::fromBase64(cipherText.toLatin1());
    QByteArray keyBytes = key.toUtf8();

    QByteArray decrypted;
    for (int i = 0; i < data.size(); ++i) {
        decrypted.append(data[i] ^ keyBytes[i % keyBytes.size()]);
    }

    return QString::fromUtf8(decrypted);
}
