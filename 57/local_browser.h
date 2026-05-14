#ifndef LOCAL_BROWSER_H
#define LOCAL_BROWSER_H

#include <QObject>
#include <QString>
#include <QTreeWidget>
#include <QTreeWidgetItem>
#include <QSet>

class LocalBrowser : public QObject
{
    Q_OBJECT

public:
    explicit LocalBrowser(QObject *parent = nullptr);
    ~LocalBrowser();

    void setTreeWidget(QTreeWidget *treeWidget);
    void loadRoot();
    QString getSelectedFile() const;
    QString getCurrentPath() const;

private slots:
    void onItemExpanded(QTreeWidgetItem *item);
    void onItemCollapsed(QTreeWidgetItem *item);
    void onItemClicked(QTreeWidgetItem *item, int column);

private:
    void loadChildren(QTreeWidgetItem *parentItem, const QString &path);
    void addDrives();
    QTreeWidgetItem *createItem(const QString &path, bool isDir, bool isSymLink);
    bool wouldCreateCycle(const QString &path, const QString &canonicalPath);
    QString getCanonicalPath(const QString &path);

    QTreeWidget *m_treeWidget;
    QString m_currentPath;
    QSet<QString> m_visitedCanonicalPaths;
};

#endif // LOCAL_BROWSER_H
