#include "local_browser.h"
#include <QDir>
#include <QFileInfo>
#include <QStorageInfo>
#include <QApplication>
#include <QStyle>
#include <QDebug>

LocalBrowser::LocalBrowser(QObject *parent) :
    QObject(parent),
    m_treeWidget(nullptr)
{
}

LocalBrowser::~LocalBrowser()
{
}

void LocalBrowser::setTreeWidget(QTreeWidget *treeWidget)
{
    m_treeWidget = treeWidget;
    if (m_treeWidget) {
        m_treeWidget->setColumnCount(2);
        m_treeWidget->setHeaderLabels(QStringList() << tr("名称") << tr("大小"));
        m_treeWidget->setColumnWidth(0, 250);
        connect(m_treeWidget, &QTreeWidget::itemExpanded, this, &LocalBrowser::onItemExpanded);
        connect(m_treeWidget, &QTreeWidget::itemCollapsed, this, &LocalBrowser::onItemCollapsed);
        connect(m_treeWidget, &QTreeWidget::itemClicked, this, &LocalBrowser::onItemClicked);
    }
}

void LocalBrowser::loadRoot()
{
    if (!m_treeWidget) return;

    m_treeWidget->clear();
    m_visitedCanonicalPaths.clear();

#ifdef Q_OS_WIN
    addDrives();
#else
    QTreeWidgetItem *rootItem = new QTreeWidgetItem(m_treeWidget);
    rootItem->setText(0, tr("根目录"));
    rootItem->setIcon(0, QApplication::style()->standardIcon(QStyle::SP_DirIcon));
    rootItem->setData(0, Qt::UserRole, "/");
    rootItem->setData(0, Qt::UserRole + 1, true);
    rootItem->setData(0, Qt::UserRole + 2, false);

    QString canonicalRoot = getCanonicalPath("/");
    if (!canonicalRoot.isEmpty()) {
        rootItem->setData(0, Qt::UserRole + 3, canonicalRoot);
    }

    QTreeWidgetItem *placeholder = new QTreeWidgetItem(rootItem);
    placeholder->setText(0, "Loading...");
#endif
}

void LocalBrowser::addDrives()
{
    foreach (const QStorageInfo &storage, QStorageInfo::mountedVolumes()) {
        if (storage.isValid() && storage.isReady()) {
            QString drivePath = storage.rootPath();
            QTreeWidgetItem *driveItem = new QTreeWidgetItem(m_treeWidget);

            QString displayName = storage.displayName();
            if (displayName.isEmpty()) {
                displayName = drivePath;
            } else {
                displayName = QString("%1 (%2)").arg(displayName).arg(drivePath);
            }

            driveItem->setText(0, displayName);
            driveItem->setIcon(0, QApplication::style()->standardIcon(QStyle::SP_DriveHDIcon));
            driveItem->setData(0, Qt::UserRole, drivePath);
            driveItem->setData(0, Qt::UserRole + 1, true);
            driveItem->setData(0, Qt::UserRole + 2, false);

            QString canonicalPath = getCanonicalPath(drivePath);
            if (!canonicalPath.isEmpty()) {
                driveItem->setData(0, Qt::UserRole + 3, canonicalPath);
            }

            QTreeWidgetItem *placeholder = new QTreeWidgetItem(driveItem);
            placeholder->setText(0, "Loading...");
        }
    }
}

void LocalBrowser::onItemExpanded(QTreeWidgetItem *item)
{
    if (!item) return;

    if (item->childCount() == 1 && item->child(0)->text(0) == "Loading...") {
        item->takeChild(0);
        QString path = item->data(0, Qt::UserRole).toString();

        QString canonicalPath = item->data(0, Qt::UserRole + 3).toString();
        if (canonicalPath.isEmpty()) {
            canonicalPath = getCanonicalPath(path);
        }

        if (!canonicalPath.isEmpty()) {
            m_visitedCanonicalPaths.insert(canonicalPath);
        }

        loadChildren(item, path);
    }
}

void LocalBrowser::onItemCollapsed(QTreeWidgetItem *item)
{
    if (!item) return;

    QString canonicalPath = item->data(0, Qt::UserRole + 3).toString();
    if (!canonicalPath.isEmpty()) {
        m_visitedCanonicalPaths.remove(canonicalPath);
    }

    for (int i = item->childCount() - 1; i >= 0; --i) {
        QTreeWidgetItem *child = item->child(i);
        QString childCanonical = child->data(0, Qt::UserRole + 3).toString();
        if (!childCanonical.isEmpty()) {
            m_visitedCanonicalPaths.remove(childCanonical);
        }
        delete child;
    }

    QTreeWidgetItem *placeholder = new QTreeWidgetItem(item);
    placeholder->setText(0, "Loading...");
}

void LocalBrowser::onItemClicked(QTreeWidgetItem *item, int)
{
    if (!item) return;

    QString path = item->data(0, Qt::UserRole).toString();
    bool isDir = item->data(0, Qt::UserRole + 1).toBool();

    if (isDir) {
        m_currentPath = path;
    } else {
        m_currentPath = QFileInfo(path).absolutePath();
    }
}

void LocalBrowser::loadChildren(QTreeWidgetItem *parentItem, const QString &path)
{
    QDir dir(path);
    if (!dir.exists()) return;

    dir.setFilter(QDir::AllDirs | QDir::Files | QDir::NoDotAndDotDot);
    dir.setSorting(QDir::DirsFirst | QDir::Name);

    QFileInfoList entries = dir.entryInfoList();

    QList<QTreeWidgetItem *> dirItems;
    QList<QTreeWidgetItem *> fileItems;

    QString parentCanonical = parentItem->data(0, Qt::UserRole + 3).toString();

    foreach (const QFileInfo &info, entries) {
        QString itemPath = info.absoluteFilePath();
        bool isSymLink = info.isSymLink();
        bool isDir = info.isDir();

        if (isDir) {
            QString canonical = getCanonicalPath(itemPath);
            bool wouldCycle = wouldCreateCycle(parentCanonical, canonical);

            if (wouldCycle) {
                qDebug() << "Skipping symlink cycle:" << itemPath << "->" << canonical;
                continue;
            }

            QTreeWidgetItem *item = createItem(itemPath, true, isSymLink);
            if (!canonical.isEmpty()) {
                item->setData(0, Qt::UserRole + 3, canonical);
            }
            dirItems.append(item);
        } else {
            QTreeWidgetItem *item = createItem(itemPath, false, isSymLink);
            item->setText(1, QString::number(info.size()));
            fileItems.append(item);
        }
    }

    parentItem->addChildren(dirItems);
    parentItem->addChildren(fileItems);
}

QTreeWidgetItem *LocalBrowser::createItem(const QString &path, bool isDir, bool isSymLink)
{
    QTreeWidgetItem *item = new QTreeWidgetItem();
    QFileInfo info(path);

    QString displayName = info.fileName();
    if (isSymLink) {
        displayName = QString("%1@").arg(displayName);
    }

    item->setText(0, displayName);
    item->setData(0, Qt::UserRole, path);
    item->setData(0, Qt::UserRole + 1, isDir);
    item->setData(0, Qt::UserRole + 2, isSymLink);

    if (isDir) {
        if (isSymLink) {
            item->setIcon(0, QApplication::style()->standardIcon(QStyle::SP_DirLinkIcon));
        } else {
            item->setIcon(0, QApplication::style()->standardIcon(QStyle::SP_DirIcon));
        }
        QTreeWidgetItem *placeholder = new QTreeWidgetItem(item);
        placeholder->setText(0, "Loading...");
    } else {
        if (isSymLink) {
            item->setIcon(0, QApplication::style()->standardIcon(QStyle::SP_FileLinkIcon));
        } else {
            item->setIcon(0, QApplication::style()->standardIcon(QStyle::SP_FileIcon));
        }
    }

    return item;
}

QString LocalBrowser::getCanonicalPath(const QString &path)
{
    QFileInfo info(path);
    if (info.exists()) {
        if (info.isSymLink()) {
            QString target = info.symLinkTarget();
            if (!target.isEmpty()) {
                QFileInfo targetInfo(target);
                if (targetInfo.exists()) {
                    return targetInfo.canonicalFilePath();
                }
            }
        }
        return info.canonicalFilePath();
    }
    return QString();
}

bool LocalBrowser::wouldCreateCycle(const QString &parentCanonical, const QString &canonicalPath)
{
    if (canonicalPath.isEmpty()) {
        return false;
    }

    if (m_visitedCanonicalPaths.contains(canonicalPath)) {
        return true;
    }

    if (!parentCanonical.isEmpty() && !canonicalPath.isEmpty()) {
        if (canonicalPath == parentCanonical) {
            return true;
        }
        if (canonicalPath.startsWith(parentCanonical + QDir::separator())) {
            return true;
        }
    }

    return false;
}

QString LocalBrowser::getSelectedFile() const
{
    if (!m_treeWidget) return QString();

    QTreeWidgetItem *item = m_treeWidget->currentItem();
    if (!item) return QString();

    bool isDir = item->data(0, Qt::UserRole + 1).toBool();
    if (isDir) return QString();

    return item->data(0, Qt::UserRole).toString();
}

QString LocalBrowser::getCurrentPath() const
{
    if (m_currentPath.isEmpty()) {
        if (!m_treeWidget) return QDir::homePath();

        QTreeWidgetItem *item = m_treeWidget->currentItem();
        if (item) {
            bool isDir = item->data(0, Qt::UserRole + 1).toBool();
            QString path = item->data(0, Qt::UserRole).toString();
            if (isDir) {
                return path;
            } else {
                return QFileInfo(path).absolutePath();
            }
        }
        return QDir::homePath();
    }
    return m_currentPath;
}
