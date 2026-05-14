#include "mainwindow.h"
#include "ui_mainwindow.h"
#include <QMessageBox>
#include <QDateTime>
#include <QInputDialog>
#include <QTabWidget>
#include <QSplitter>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGroupBox>
#include <QLabel>
#include <QPushButton>
#include <QComboBox>
#include <QTableWidget>
#include <QHeaderView>
#include <QFileInfo>
#include <QDebug>

MainWindow::MainWindow(QWidget *parent) :
    QMainWindow(parent),
    ui(new Ui::MainWindow),
    m_ftpConnection(new FtpConnection(this)),
    m_transferThread(new TransferThread(this)),
    m_localBrowser(new LocalBrowser(this)),
    m_siteManager(new SiteManager(this)),
    m_logWidget(nullptr),
    m_connected(false),
    m_currentRemotePath("/"),
    m_currentQueueIndex(-1),
    m_queueRunning(false),
    m_queuePaused(false)
{
    ui->setupUi(this);

    QTabWidget *bottomTabWidget = new QTabWidget();

    QWidget *queuePage = new QWidget();
    QVBoxLayout *queueLayout = new QVBoxLayout(queuePage);

    QTableWidget *queueTable = new QTableWidget();
    queueTable->setObjectName("queueTableWidget");
    queueTable->setColumnCount(6);
    queueTable->setHorizontalHeaderLabels(QStringList() 
        << tr("文件名") << tr("类型") << tr("状态") << tr("进度") << tr("大小") << tr("优先级"));
    queueTable->setSelectionBehavior(QAbstractItemView::SelectRows);
    queueTable->setEditTriggers(QAbstractItemView::NoEditTriggers);
    queueTable->horizontalHeader()->setStretchLastSection(true);
    queueTable->setColumnWidth(0, 250);
    queueTable->setColumnWidth(1, 80);
    queueTable->setColumnWidth(2, 80);
    queueTable->setColumnWidth(3, 100);
    queueTable->setColumnWidth(4, 100);

    QHBoxLayout *queueButtonLayout = new QHBoxLayout();
    QPushButton *addToQueueBtn = new QPushButton(tr("添加到队列"));
    QPushButton *removeFromQueueBtn = new QPushButton(tr("移除"));
    QPushButton *startQueueBtn = new QPushButton(tr("开始队列"));
    QPushButton *pauseQueueBtn = new QPushButton(tr("暂停"));
    QPushButton *clearQueueBtn = new QPushButton(tr("清空"));
    QPushButton *moveUpBtn = new QPushButton(tr("上移"));
    QPushButton *moveDownBtn = new QPushButton(tr("下移"));

    addToQueueBtn->setObjectName("addToQueueButton");
    removeFromQueueBtn->setObjectName("removeFromQueueButton");
    startQueueBtn->setObjectName("startQueueButton");
    pauseQueueBtn->setObjectName("pauseQueueButton");
    clearQueueBtn->setObjectName("clearQueueButton");
    moveUpBtn->setObjectName("moveQueueUpButton");
    moveDownBtn->setObjectName("moveQueueDownButton");

    queueButtonLayout->addWidget(addToQueueBtn);
    queueButtonLayout->addWidget(removeFromQueueBtn);
    queueButtonLayout->addWidget(startQueueBtn);
    queueButtonLayout->addWidget(pauseQueueBtn);
    queueButtonLayout->addWidget(clearQueueBtn);
    queueButtonLayout->addStretch();
    queueButtonLayout->addWidget(moveUpBtn);
    queueButtonLayout->addWidget(moveDownBtn);

    queueLayout->addWidget(queueTable);
    queueLayout->addLayout(queueButtonLayout);

    m_logWidget = new LogWidget();

    bottomTabWidget->addTab(queuePage, tr("传输队列"));
    bottomTabWidget->addTab(m_logWidget, tr("传输日志"));

    QWidget *central = ui->centralWidget;
    QVBoxLayout *centralLayout = new QVBoxLayout(central);
    centralLayout->setContentsMargins(0, 0, 0, 0);

    QWidget *topContainer = new QWidget();
    QVBoxLayout *topLayout = new QVBoxLayout(topContainer);
    topLayout->setContentsMargins(0, 0, 0, 0);

    QLayoutItem *item;
    while ((item = ui->verticalLayout->takeAt(0)) != nullptr) {
        if (item->widget()) {
            topLayout->addWidget(item->widget());
        } else if (item->layout()) {
            topLayout->addLayout(item->layout());
        }
        delete item;
    }

    centralLayout->addWidget(topContainer);
    centralLayout->addWidget(bottomTabWidget);

    setupUI();
    connectSignals();
    m_localBrowser->setTreeWidget(ui->localTreeWidget);
    m_localBrowser->loadRoot();
    loadSiteComboBox();
    updateQueueTable();
}

MainWindow::~MainWindow()
{
    if (m_connected) {
        m_ftpConnection->disconnectFromServer();
    }
    delete ui;
}

void MainWindow::setupUI()
{
    ui->portSpinBox->setValue(21);
    ui->connectButton->setEnabled(true);
    ui->disconnectButton->setEnabled(false);
    ui->uploadButton->setEnabled(false);
    ui->downloadButton->setEnabled(false);
    ui->progressBar->setVisible(false);
    ui->remoteTreeWidget->setColumnCount(4);
    ui->remoteTreeWidget->setHeaderLabels(QStringList() << tr("名称") << tr("大小") << tr("类型") << tr("修改时间"));
    ui->remoteTreeWidget->setColumnWidth(0, 200);

    QWidget *siteWidget = new QWidget();
    QHBoxLayout *siteLayout = new QHBoxLayout(siteWidget);
    siteLayout->setContentsMargins(0, 0, 0, 0);

    QLabel *siteLabel = new QLabel(tr("站点:"));
    QComboBox *siteCombo = new QComboBox();
    siteCombo->setObjectName("siteComboBox");
    siteCombo->setEditable(true);
    siteCombo->setMinimumWidth(150);

    QPushButton *saveSiteBtn = new QPushButton(tr("保存"));
    QPushButton *deleteSiteBtn = new QPushButton(tr("删除"));
    saveSiteBtn->setObjectName("saveSiteButton");
    deleteSiteBtn->setObjectName("deleteSiteButton");

    siteLayout->addWidget(siteLabel);
    siteLayout->addWidget(siteCombo);
    siteLayout->addWidget(saveSiteBtn);
    siteLayout->addWidget(deleteSiteBtn);
    siteLayout->addStretch();

    QLayout *connLayout = ui->connectionGroupBox->layout();
    if (connLayout) {
        static_cast<QBoxLayout*>(connLayout)->insertWidget(0, siteWidget);
    }
}

void MainWindow::connectSignals()
{
    connect(ui->connectButton, &QPushButton::clicked, this, &MainWindow::onConnectClicked);
    connect(ui->disconnectButton, &QPushButton::clicked, this, &MainWindow::onDisconnectClicked);
    connect(ui->uploadButton, &QPushButton::clicked, this, &MainWindow::onUploadClicked);
    connect(ui->downloadButton, &QPushButton::clicked, this, &MainWindow::onDownloadClicked);
    connect(ui->remoteTreeWidget, &QTreeWidget::itemDoubleClicked, this, &MainWindow::onRemoteItemDoubleClicked);

    connect(m_ftpConnection, &FtpConnection::connected, this, &MainWindow::onFtpConnected);
    connect(m_ftpConnection, &FtpConnection::disconnected, this, &MainWindow::onFtpDisconnected);
    connect(m_ftpConnection, &FtpConnection::error, this, &MainWindow::onFtpError);
    connect(m_ftpConnection, &FtpConnection::listReceived, this, &MainWindow::onFtpListReceived);

    connect(m_transferThread, &TransferThread::progress, this, &MainWindow::onTransferProgress);
    connect(m_transferThread, &TransferThread::started, this, &MainWindow::onTransferStarted);
    connect(m_transferThread, &TransferThread::finished, this, &MainWindow::onTransferFinished);
    connect(m_transferThread, &TransferThread::error, this, &MainWindow::onTransferError);
    connect(m_transferThread, &TransferThread::resumed, this, &MainWindow::onTransferResumed);

    QPushButton *addToQueueBtn = findChild<QPushButton*>("addToQueueButton");
    QPushButton *removeFromQueueBtn = findChild<QPushButton*>("removeFromQueueButton");
    QPushButton *startQueueBtn = findChild<QPushButton*>("startQueueButton");
    QPushButton *pauseQueueBtn = findChild<QPushButton*>("pauseQueueButton");
    QPushButton *clearQueueBtn = findChild<QPushButton*>("clearQueueButton");
    QPushButton *moveUpBtn = findChild<QPushButton*>("moveQueueUpButton");
    QPushButton *moveDownBtn = findChild<QPushButton*>("moveQueueDownButton");

    if (addToQueueBtn) connect(addToQueueBtn, &QPushButton::clicked, this, &MainWindow::onAddToQueueClicked);
    if (removeFromQueueBtn) connect(removeFromQueueBtn, &QPushButton::clicked, this, &MainWindow::onRemoveFromQueueClicked);
    if (startQueueBtn) connect(startQueueBtn, &QPushButton::clicked, this, &MainWindow::onStartQueueClicked);
    if (pauseQueueBtn) connect(pauseQueueBtn, &QPushButton::clicked, this, &MainWindow::onPauseQueueClicked);
    if (clearQueueBtn) connect(clearQueueBtn, &QPushButton::clicked, this, &MainWindow::onClearQueueClicked);
    if (moveUpBtn) connect(moveUpBtn, &QPushButton::clicked, this, &MainWindow::onMoveQueueUpClicked);
    if (moveDownBtn) connect(moveDownBtn, &QPushButton::clicked, this, &MainWindow::onMoveQueueDownClicked);

    QPushButton *saveSiteBtn = findChild<QPushButton*>("saveSiteButton");
    QPushButton *deleteSiteBtn = findChild<QPushButton*>("deleteSiteButton");
    QComboBox *siteCombo = findChild<QComboBox*>("siteComboBox");

    if (saveSiteBtn) connect(saveSiteBtn, &QPushButton::clicked, this, &MainWindow::onSaveSiteClicked);
    if (deleteSiteBtn) connect(deleteSiteBtn, &QPushButton::clicked, this, &MainWindow::onDeleteSiteClicked);
    if (siteCombo) {
        connect(siteCombo, static_cast<void(QComboBox::*)(const QString&)>(&QComboBox::activated),
                this, &MainWindow::onSiteSelected);
    }

    QTableWidget *queueTable = findChild<QTableWidget*>("queueTableWidget");
    if (queueTable) {
        connect(queueTable, &QTableWidget::cellDoubleClicked, this, &MainWindow::onQueueItemDoubleClicked);
    }
}

void MainWindow::onConnectClicked()
{
    QString host = ui->hostLineEdit->text().trimmed();
    int port = ui->portSpinBox->value();
    QString user = ui->userLineEdit->text().trimmed();
    QString password = ui->passwordLineEdit->text();

    if (host.isEmpty()) {
        QMessageBox::warning(this, tr("警告"), tr("请输入 FTP 服务器地址"));
        return;
    }

    m_ftpConnection->connectToServer(host, port, user, password);
    appendLog(tr("正在连接到 %1:%2...").arg(host).arg(port));
    if (m_logWidget) {
        m_logWidget->addInfo(tr("连接到 %1:%2").arg(host).arg(port), LogWidget::Connection);
    }
}

void MainWindow::onDisconnectClicked()
{
    m_ftpConnection->disconnectFromServer();
}

void MainWindow::onFtpConnected()
{
    m_connected = true;
    ui->connectButton->setEnabled(false);
    ui->disconnectButton->setEnabled(true);
    ui->uploadButton->setEnabled(true);
    ui->downloadButton->setEnabled(true);
    m_currentRemotePath = "/";
    m_ftpConnection->listDirectory(m_currentRemotePath);
    appendLog(tr("已连接到 FTP 服务器"));
    if (m_logWidget) {
        m_logWidget->addSuccess(tr("FTP 连接成功"), LogWidget::Connection);
    }
}

void MainWindow::onFtpDisconnected()
{
    m_connected = false;
    ui->connectButton->setEnabled(true);
    ui->disconnectButton->setEnabled(false);
    ui->uploadButton->setEnabled(false);
    ui->downloadButton->setEnabled(false);
    ui->remoteTreeWidget->clear();
    ui->progressBar->setVisible(false);
    appendLog(tr("已断开连接"));
    if (m_logWidget) {
        m_logWidget->addInfo(tr("FTP 连接已断开"), LogWidget::Connection);
    }
}

void MainWindow::onFtpError(const QString &error)
{
    QMessageBox::critical(this, tr("错误"), error);
    appendLog(tr("错误: %1").arg(error));
    if (m_logWidget) {
        m_logWidget->addError(error, LogWidget::Connection);
    }
}

void MainWindow::onFtpListReceived(const QList<FtpFileInfo> &fileList)
{
    populateRemoteTree(fileList);
}

void MainWindow::populateRemoteTree(const QList<FtpFileInfo> &fileList)
{
    ui->remoteTreeWidget->clear();

    if (!m_currentRemotePath.isEmpty() && m_currentRemotePath != "/") {
        QTreeWidgetItem *parentItem = new QTreeWidgetItem(ui->remoteTreeWidget);
        parentItem->setText(0, tr(".."));
        parentItem->setIcon(0, style()->standardIcon(QStyle::SP_DirIcon));
        parentItem->setText(2, tr("上级目录"));
        parentItem->setData(0, Qt::UserRole, "..");
    }

    for (const FtpFileInfo &info : fileList) {
        QTreeWidgetItem *item = new QTreeWidgetItem(ui->remoteTreeWidget);
        item->setText(0, info.name);
        item->setData(0, Qt::UserRole, info.name);
        item->setData(0, Qt::UserRole + 1, info.isDir);

        if (info.isDir) {
            item->setIcon(0, style()->standardIcon(QStyle::SP_DirIcon));
            item->setText(2, tr("目录"));
        } else {
            item->setIcon(0, style()->standardIcon(QStyle::SP_FileIcon));
            item->setText(1, QString::number(info.size));
            item->setText(2, tr("文件"));
        }

        if (info.lastModified.isValid()) {
            item->setText(3, info.lastModified.toString("yyyy-MM-dd HH:mm:ss"));
        }
    }
}

void MainWindow::onRemoteItemDoubleClicked(QTreeWidgetItem *item, int)
{
    if (!item) return;

    bool isDir = item->data(0, Qt::UserRole + 1).toBool();
    QString name = item->data(0, Qt::UserRole).toString();

    if (name == "..") {
        if (m_currentRemotePath != "/") {
            QString parentPath = m_currentRemotePath.left(m_currentRemotePath.lastIndexOf('/'));
            if (parentPath.isEmpty()) parentPath = "/";
            m_currentRemotePath = parentPath;
            m_ftpConnection->listDirectory(m_currentRemotePath);
        }
    } else if (isDir) {
        if (m_currentRemotePath.endsWith('/')) {
            m_currentRemotePath += name;
        } else {
            m_currentRemotePath += "/" + name;
        }
        m_ftpConnection->listDirectory(m_currentRemotePath);
    }
}

void MainWindow::onUploadClicked()
{
    QString localFile = getSelectedLocalFile();
    if (localFile.isEmpty()) {
        QMessageBox::information(this, tr("提示"), tr("请选择要上传的本地文件"));
        return;
    }

    if (!m_transferThread->isRunning()) {
        QString remoteFile = m_currentRemotePath;
        if (!remoteFile.endsWith('/')) remoteFile += '/';
        remoteFile += QFileInfo(localFile).fileName();

        TransferThread::TransferInfo info;
        info.mode = TransferThread::Upload;
        info.localFile = localFile;
        info.remoteFile = remoteFile;
        info.host = ui->hostLineEdit->text().trimmed();
        info.port = ui->portSpinBox->value();
        info.user = ui->userLineEdit->text().trimmed();
        info.password = ui->passwordLineEdit->text();
        info.enableResume = true;
        info.resumePosition = 0;

        m_transferThread->setTransferInfo(info);
        m_transferThread->start();
    }
}

void MainWindow::onDownloadClicked()
{
    QString remoteFile = getSelectedRemoteFile();
    if (remoteFile.isEmpty()) {
        QMessageBox::information(this, tr("提示"), tr("请选择要下载的远程文件"));
        return;
    }

    if (!m_transferThread->isRunning()) {
        QString localDir = m_localBrowser->getCurrentPath();
        QString localFile = localDir + "/" + QFileInfo(remoteFile).fileName();

        TransferThread::TransferInfo info;
        info.mode = TransferThread::Download;
        info.localFile = localFile;
        info.remoteFile = remoteFile;
        info.host = ui->hostLineEdit->text().trimmed();
        info.port = ui->portSpinBox->value();
        info.user = ui->userLineEdit->text().trimmed();
        info.password = ui->passwordLineEdit->text();
        info.enableResume = true;
        info.resumePosition = 0;

        m_transferThread->setTransferInfo(info);
        m_transferThread->start();
    }
}

QString MainWindow::getSelectedRemoteFile()
{
    QTreeWidgetItem *item = ui->remoteTreeWidget->currentItem();
    if (!item) return QString();

    QString name = item->data(0, Qt::UserRole).toString();
    if (name == "..") return QString();

    bool isDir = item->data(0, Qt::UserRole + 1).toBool();
    if (isDir) return QString();

    QString remoteFile = m_currentRemotePath;
    if (!remoteFile.endsWith('/')) remoteFile += '/';
    remoteFile += name;
    return remoteFile;
}

QString MainWindow::getSelectedLocalFile()
{
    return m_localBrowser->getSelectedFile();
}

void MainWindow::onTransferStarted(const QString &fileName, bool isUpload)
{
    ui->progressBar->setVisible(true);
    ui->progressBar->setValue(0);
    ui->uploadButton->setEnabled(false);
    ui->downloadButton->setEnabled(false);
    appendLog(tr("%1: %2").arg(isUpload ? tr("开始上传") : tr("开始下载")).arg(fileName));
    if (m_logWidget) {
        m_logWidget->addInfo(tr("%1: %2").arg(isUpload ? tr("上传") : tr("下载")).arg(fileName), LogWidget::Transfer);
    }
}

void MainWindow::onTransferProgress(qint64 bytesTransferred, qint64 bytesTotal)
{
    if (bytesTotal > 0) {
        double percentDouble = (static_cast<double>(bytesTransferred) / static_cast<double>(bytesTotal)) * 100.0;
        int percent = qMin(100, static_cast<int>(percentDouble + 0.5));
        percent = qMax(0, percent);
        ui->progressBar->setValue(percent);

        if (m_currentQueueIndex >= 0 && m_currentQueueIndex < m_transferQueue.size()) {
            m_transferQueue[m_currentQueueIndex].transferred = bytesTransferred;
            m_transferQueue[m_currentQueueIndex].total = bytesTotal;
            updateQueueTable();
        }
    }
}

void MainWindow::onTransferFinished(const QString &fileName, bool success)
{
    ui->progressBar->setVisible(false);
    ui->uploadButton->setEnabled(true);
    ui->downloadButton->setEnabled(true);

    if (m_currentQueueIndex >= 0 && m_currentQueueIndex < m_transferQueue.size()) {
        m_transferQueue[m_currentQueueIndex].status = success ? QueueItem::Completed : QueueItem::Failed;
    }

    if (success) {
        appendLog(tr("传输完成: %1").arg(fileName));
        if (m_logWidget) {
            m_logWidget->addSuccess(tr("传输完成: %1").arg(fileName), LogWidget::Transfer);
        }
        if (m_connected) {
            m_ftpConnection->listDirectory(m_currentRemotePath);
        }
    } else {
        appendLog(tr("传输失败: %1").arg(fileName));
        if (m_logWidget) {
            m_logWidget->addError(tr("传输失败: %1").arg(fileName), LogWidget::Transfer);
        }
    }

    updateQueueTable();

    if (m_queueRunning) {
        processQueue();
    }
}

void MainWindow::onTransferError(const QString &error)
{
    ui->progressBar->setVisible(false);
    ui->uploadButton->setEnabled(true);
    ui->downloadButton->setEnabled(true);
    QMessageBox::critical(this, tr("传输错误"), error);
    appendLog(tr("传输错误: %1").arg(error));
    if (m_logWidget) {
        m_logWidget->addError(error, LogWidget::Transfer);
    }

    if (m_currentQueueIndex >= 0 && m_currentQueueIndex < m_transferQueue.size()) {
        m_transferQueue[m_currentQueueIndex].status = QueueItem::Failed;
        m_transferQueue[m_currentQueueIndex].errorMessage = error;
        updateQueueTable();
    }

    if (m_queueRunning) {
        processQueue();
    }
}

void MainWindow::onTransferResumed(const QString &fileName, qint64 resumePosition)
{
    appendLog(tr("断点续传: %1 (从 %2 字节继续)").arg(fileName).arg(resumePosition));
    if (m_logWidget) {
        m_logWidget->addInfo(tr("断点续传: %1 (从 %2 字节)").arg(fileName).arg(resumePosition), LogWidget::Transfer);
    }
}

void MainWindow::appendLog(const QString &message)
{
    QString timestamp = QDateTime::currentDateTime().toString("yyyy-MM-dd HH:mm:ss");
    ui->logTextEdit->append(QString("[%1] %2").arg(timestamp).arg(message));
}

void MainWindow::addToQueue(const TransferThread::TransferInfo &info)
{
    QueueItem item;
    item.transferInfo = info;
    item.status = QueueItem::Pending;
    item.priority = 0;
    item.transferred = 0;
    item.total = 0;

    m_transferQueue.append(item);
    updateQueueTable();
    appendLog(tr("已添加到队列: %1").arg(QFileInfo(info.localFile).fileName()));
    if (m_logWidget) {
        m_logWidget->addInfo(tr("添加到队列: %1").arg(QFileInfo(info.localFile).fileName()), LogWidget::System);
    }
}

void MainWindow::processQueue()
{
    if (m_queuePaused) {
        return;
    }

    m_currentQueueIndex = -1;
    for (int i = 0; i < m_transferQueue.size(); ++i) {
        if (m_transferQueue[i].status == QueueItem::Pending) {
            m_currentQueueIndex = i;
            break;
        }
    }

    if (m_currentQueueIndex < 0) {
        m_queueRunning = false;
        appendLog(tr("队列处理完成"));
        if (m_logWidget) {
            m_logWidget->addSuccess(tr("传输队列处理完成"), LogWidget::System);
        }
        return;
    }

    QueueItem &item = m_transferQueue[m_currentQueueIndex];
    item.status = QueueItem::Running;
    updateQueueTable();

    m_transferThread->setTransferInfo(item.transferInfo);
    m_transferThread->start();
}

void MainWindow::updateQueueTable()
{
    QTableWidget *queueTable = findChild<QTableWidget*>("queueTableWidget");
    if (!queueTable) return;

    queueTable->setRowCount(0);

    for (int i = 0; i < m_transferQueue.size(); ++i) {
        const QueueItem &item = m_transferQueue[i];
        int row = queueTable->rowCount();
        queueTable->insertRow(row);

        QString fileName = QFileInfo(item.transferInfo.localFile).fileName();
        if (fileName.isEmpty()) {
            fileName = QFileInfo(item.transferInfo.remoteFile).fileName();
        }

        queueTable->setItem(row, 0, new QTableWidgetItem(fileName));

        QString typeStr = (item.transferInfo.mode == TransferThread::Upload) ? tr("上传") : tr("下载");
        queueTable->setItem(row, 1, new QTableWidgetItem(typeStr));

        QString statusStr;
        switch (item.status) {
        case QueueItem::Pending: statusStr = tr("等待"); break;
        case QueueItem::Running: statusStr = tr("运行中"); break;
        case QueueItem::Completed: statusStr = tr("完成"); break;
        case QueueItem::Failed: statusStr = tr("失败"); break;
        case QueueItem::Paused: statusStr = tr("暂停"); break;
        default: statusStr = tr("未知"); break;
        }
        queueTable->setItem(row, 2, new QTableWidgetItem(statusStr));

        QString progressStr;
        if (item.total > 0) {
            double percent = (static_cast<double>(item.transferred) / item.total) * 100.0;
            progressStr = QString("%1%").arg(static_cast<int>(percent));
        } else {
            progressStr = tr("等待中");
        }
        queueTable->setItem(row, 3, new QTableWidgetItem(progressStr));

        QString sizeStr;
        if (item.total > 0) {
            if (item.total > 1024 * 1024 * 1024) {
                sizeStr = QString("%1 GB").arg(item.total / (1024.0 * 1024 * 1024), 0, 'f', 2);
            } else if (item.total > 1024 * 1024) {
                sizeStr = QString("%1 MB").arg(item.total / (1024.0 * 1024), 0, 'f', 2);
            } else if (item.total > 1024) {
                sizeStr = QString("%1 KB").arg(item.total / 1024.0, 0, 'f', 2);
            } else {
                sizeStr = QString("%1 B").arg(item.total);
            }
        }
        queueTable->setItem(row, 4, new QTableWidgetItem(sizeStr));

        queueTable->setItem(row, 5, new QTableWidgetItem(QString::number(item.priority)));
    }
}

QueueItem* MainWindow::getCurrentQueueItem()
{
    QTableWidget *queueTable = findChild<QTableWidget*>("queueTableWidget");
    if (!queueTable) return nullptr;

    int row = queueTable->currentRow();
    if (row >= 0 && row < m_transferQueue.size()) {
        return &m_transferQueue[row];
    }
    return nullptr;
}

void MainWindow::loadSiteComboBox()
{
    QComboBox *siteCombo = findChild<QComboBox*>("siteComboBox");
    if (!siteCombo) return;

    siteCombo->clear();
    siteCombo->addItem(tr("--- 选择站点 ---"), QString());

    QList<SiteInfo> sites = m_siteManager->getAllSites();
    foreach (const SiteInfo &site, sites) {
        siteCombo->addItem(site.name, site.id);
    }
}

void MainWindow::onAddToQueueClicked()
{
    TransferThread::TransferInfo info;
    info.host = ui->hostLineEdit->text().trimmed();
    info.port = ui->portSpinBox->value();
    info.user = ui->userLineEdit->text().trimmed();
    info.password = ui->passwordLineEdit->text();
    info.enableResume = true;
    info.resumePosition = 0;

    QString localFile = getSelectedLocalFile();
    QString remoteFile = getSelectedRemoteFile();

    if (!localFile.isEmpty()) {
        info.mode = TransferThread::Upload;
        info.localFile = localFile;
        QString remotePath = m_currentRemotePath;
        if (!remotePath.endsWith('/')) remotePath += '/';
        info.remoteFile = remotePath + QFileInfo(localFile).fileName();
        addToQueue(info);
    } else if (!remoteFile.isEmpty()) {
        info.mode = TransferThread::Download;
        info.remoteFile = remoteFile;
        QString localDir = m_localBrowser->getCurrentPath();
        info.localFile = localDir + "/" + QFileInfo(remoteFile).fileName();
        addToQueue(info);
    } else {
        QMessageBox::information(this, tr("提示"), tr("请选择要添加到队列的本地或远程文件"));
    }
}

void MainWindow::onRemoveFromQueueClicked()
{
    QTableWidget *queueTable = findChild<QTableWidget*>("queueTableWidget");
    if (!queueTable) return;

    int row = queueTable->currentRow();
    if (row >= 0 && row < m_transferQueue.size()) {
        if (m_transferQueue[row].status == QueueItem::Running) {
            QMessageBox::warning(this, tr("警告"), tr("无法删除正在运行的任务"));
            return;
        }
        m_transferQueue.removeAt(row);
        updateQueueTable();
    }
}

void MainWindow::onStartQueueClicked()
{
    if (m_transferQueue.isEmpty()) {
        QMessageBox::information(this, tr("提示"), tr("队列为空"));
        return;
    }

    bool hasPending = false;
    foreach (const QueueItem &item, m_transferQueue) {
        if (item.status == QueueItem::Pending) {
            hasPending = true;
            break;
        }
    }

    if (!hasPending) {
        QMessageBox::information(this, tr("提示"), tr("没有等待中的任务"));
        return;
    }

    m_queueRunning = true;
    m_queuePaused = false;
    appendLog(tr("开始处理传输队列"));
    if (m_logWidget) {
        m_logWidget->addInfo(tr("开始处理传输队列"), LogWidget::System);
    }
    processQueue();
}

void MainWindow::onPauseQueueClicked()
{
    m_queuePaused = !m_queuePaused;
    if (m_queuePaused) {
        appendLog(tr("队列已暂停"));
        if (m_logWidget) {
            m_logWidget->addInfo(tr("队列已暂停"), LogWidget::System);
        }
    } else {
        appendLog(tr("队列继续"));
        if (m_logWidget) {
            m_logWidget->addInfo(tr("队列继续"), LogWidget::System);
        }
        if (m_queueRunning) {
            processQueue();
        }
    }
}

void MainWindow::onClearQueueClicked()
{
    if (m_queueRunning) {
        QMessageBox::warning(this, tr("警告"), tr("请先停止队列再清空"));
        return;
    }

    QMessageBox::StandardButton reply = QMessageBox::question(
        this, tr("确认"), tr("确定要清空队列吗？"),
        QMessageBox::Yes | QMessageBox::No);

    if (reply == QMessageBox::Yes) {
        m_transferQueue.clear();
        updateQueueTable();
        appendLog(tr("队列已清空"));
    }
}

void MainWindow::onMoveQueueUpClicked()
{
    QTableWidget *queueTable = findChild<QTableWidget*>("queueTableWidget");
    if (!queueTable) return;

    int row = queueTable->currentRow();
    if (row > 0 && row < m_transferQueue.size()) {
        m_transferQueue.swap(row, row - 1);
        updateQueueTable();
        queueTable->selectRow(row - 1);
    }
}

void MainWindow::onMoveQueueDownClicked()
{
    QTableWidget *queueTable = findChild<QTableWidget*>("queueTableWidget");
    if (!queueTable) return;

    int row = queueTable->currentRow();
    if (row >= 0 && row < m_transferQueue.size() - 1) {
        m_transferQueue.swap(row, row + 1);
        updateQueueTable();
        queueTable->selectRow(row + 1);
    }
}

void MainWindow::onSaveSiteClicked()
{
    QString name = QInputDialog::getText(this, tr("保存站点"), tr("站点名称:"));
    if (name.isEmpty()) return;

    SiteInfo site;
    site.id = m_siteManager->generateId();
    site.name = name;
    site.host = ui->hostLineEdit->text().trimmed();
    site.port = ui->portSpinBox->value();
    site.user = ui->userLineEdit->text().trimmed();
    site.password = ui->passwordLineEdit->text();
    site.localPath = m_localBrowser->getCurrentPath();
    site.remotePath = m_currentRemotePath;

    if (m_siteManager->addSite(site)) {
        loadSiteComboBox();
        QMessageBox::information(this, tr("完成"), tr("站点已保存"));
        if (m_logWidget) {
            m_logWidget->addSuccess(tr("站点已保存: %1").arg(name), LogWidget::System);
        }
    } else {
        QMessageBox::warning(this, tr("错误"), tr("保存站点失败"));
    }
}

void MainWindow::onLoadSiteClicked()
{
    QComboBox *siteCombo = findChild<QComboBox*>("siteComboBox");
    if (!siteCombo) return;

    QString siteId = siteCombo->currentData().toString();
    if (siteId.isEmpty()) return;

    SiteInfo site = m_siteManager->getSite(siteId);
    if (site.id.isEmpty()) {
        QMessageBox::warning(this, tr("错误"), tr("站点不存在"));
        return;
    }

    ui->hostLineEdit->setText(site.host);
    ui->portSpinBox->setValue(site.port);
    ui->userLineEdit->setText(site.user);
    ui->passwordLineEdit->setText(site.password);

    appendLog(tr("已加载站点: %1").arg(site.name));
    if (m_logWidget) {
        m_logWidget->addInfo(tr("已加载站点: %1").arg(site.name), LogWidget::System);
    }
}

void MainWindow::onDeleteSiteClicked()
{
    QComboBox *siteCombo = findChild<QComboBox*>("siteComboBox");
    if (!siteCombo) return;

    QString siteId = siteCombo->currentData().toString();
    if (siteId.isEmpty()) {
        QMessageBox::information(this, tr("提示"), tr("请选择要删除的站点"));
        return;
    }

    QString siteName = siteCombo->currentText();
    QMessageBox::StandardButton reply = QMessageBox::question(
        this, tr("确认"), tr("确定要删除站点 \"%1\" 吗？").arg(siteName),
        QMessageBox::Yes | QMessageBox::No);

    if (reply == QMessageBox::Yes) {
        if (m_siteManager->removeSite(siteId)) {
            loadSiteComboBox();
            appendLog(tr("已删除站点: %1").arg(siteName));
            if (m_logWidget) {
                m_logWidget->addInfo(tr("已删除站点: %1").arg(siteName), LogWidget::System);
            }
        }
    }
}

void MainWindow::onSiteSelected(const QString &)
{
    onLoadSiteClicked();
}

void MainWindow::onQueueItemDoubleClicked(int row, int)
{
    if (row < 0 || row >= m_transferQueue.size()) return;

    const QueueItem &item = m_transferQueue[row];
    QString info = tr("文件: %1\n").arg(QFileInfo(item.transferInfo.localFile).fileName());
    info += tr("类型: %1\n").arg(item.transferInfo.mode == TransferThread::Upload ? tr("上传") : tr("下载"));
    info += tr("本地: %1\n").arg(item.transferInfo.localFile);
    info += tr("远程: %1\n").arg(item.transferInfo.remoteFile);
    if (!item.errorMessage.isEmpty()) {
        info += tr("\n错误: %1").arg(item.errorMessage);
    }

    QMessageBox::information(this, tr("任务详情"), info);
}
