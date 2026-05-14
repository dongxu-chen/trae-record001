#ifndef SITE_MANAGER_H
#define SITE_MANAGER_H

#include <QObject>
#include <QString>
#include <QList>
#include <QSettings>
#include <QCryptographicHash>

struct SiteInfo {
    QString id;
    QString name;
    QString host;
    int port;
    QString user;
    QString password;
    QString localPath;
    QString remotePath;
    bool enableResume;
    bool usePassiveMode;

    SiteInfo() : port(21), enableResume(true), usePassiveMode(true) {}
};

class SiteManager : public QObject
{
    Q_OBJECT

public:
    explicit SiteManager(QObject *parent = nullptr);
    ~SiteManager();

    bool loadSites();
    bool saveSites();

    QList<SiteInfo> getAllSites() const;
    SiteInfo getSite(const QString &id) const;

    bool addSite(const SiteInfo &site);
    bool updateSite(const SiteInfo &site);
    bool removeSite(const QString &id);

    QString generateId() const;

signals:
    void sitesChanged();

private:
    QString encrypt(const QString &plainText) const;
    QString decrypt(const QString &cipherText) const;
    QString getKey() const;

    QList<SiteInfo> m_sites;
    QString m_settingsPath;
};

#endif // SITE_MANAGER_H
