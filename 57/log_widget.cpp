#include "log_widget.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QHeaderView>
#include <QMessageBox>
#include <QFileDialog>
#include <QTextStream>
#include <QFile>
#include <QApplication>
#include <QStyle>
#include <QMenu>
#include <QClipboard>
#include <QAction>

LogWidget::LogWidget(QWidget *parent) :
    QWidget(parent),
    m_tableWidget(nullptr),
    m_clearButton(nullptr),
    m_exportButton(nullptr),
    m_levelFilter(nullptr),
    m_typeFilter(nullptr),
    m_countLabel(nullptr),
    m_currentLevelFilter(Info),
    m_currentTypeFilter(static_cast<LogType>(-1))
{
    setupUI();
}

LogWidget::~LogWidget()
{
}

void LogWidget::setupUI()
{
    QVBoxLayout *mainLayout = new QVBoxLayout(this);

    QHBoxLayout *toolbarLayout = new QHBoxLayout();

    m_levelFilter = new QComboBox();
    m_levelFilter->addItem(tr("所有级别"), -1);
    m_levelFilter->addItem(tr("信息"), Info);
    m_levelFilter->addItem(tr("成功"), Success);
    m_levelFilter->addItem(tr("警告"), Warning);
    m_levelFilter->addItem(tr("错误"), Error);
    m_levelFilter->addItem(tr("调试"), Debug);
    connect(m_levelFilter, static_cast<void(QComboBox::*)(int)>(&QComboBox::currentIndexChanged),
            this, &LogWidget::onFilterChanged);

    m_typeFilter = new QComboBox();
    m_typeFilter->addItem(tr("所有类型"), -1);
    m_typeFilter->addItem(tr("连接"), Connection);
    m_typeFilter->addItem(tr("传输"), Transfer);
    m_typeFilter->addItem(tr("命令"), Command);
    m_typeFilter->addItem(tr("响应"), Response);
    m_typeFilter->addItem(tr("系统"), System);
    connect(m_typeFilter, static_cast<void(QComboBox::*)(int)>(&QComboBox::currentIndexChanged),
            this, &LogWidget::onFilterChanged);

    m_clearButton = new QPushButton(tr("清空"));
    connect(m_clearButton, &QPushButton::clicked, this, &LogWidget::clearLogs);

    m_exportButton = new QPushButton(tr("导出"));
    connect(m_exportButton, &QPushButton::clicked, this, &LogWidget::exportLogs);

    m_countLabel = new QLabel(tr("0 条记录"));

    toolbarLayout->addWidget(new QLabel(tr("级别:")));
    toolbarLayout->addWidget(m_levelFilter);
    toolbarLayout->addWidget(new QLabel(tr("类型:")));
    toolbarLayout->addWidget(m_typeFilter);
    toolbarLayout->addStretch();
    toolbarLayout->addWidget(m_countLabel);
    toolbarLayout->addWidget(m_clearButton);
    toolbarLayout->addWidget(m_exportButton);

    m_tableWidget = new QTableWidget();
    m_tableWidget->setColumnCount(4);
    m_tableWidget->setHorizontalHeaderLabels(QStringList() << tr("时间") << tr("级别") << tr("类型") << tr("消息"));
    m_tableWidget->setSelectionBehavior(QAbstractItemView::SelectRows);
    m_tableWidget->setEditTriggers(QAbstractItemView::NoEditTriggers);
    m_tableWidget->setAlternatingRowColors(true);
    m_tableWidget->setContextMenuPolicy(Qt::CustomContextMenu);

    QHeaderView *header = m_tableWidget->horizontalHeader();
    header->setStretchLastSection(true);
    m_tableWidget->setColumnWidth(0, 180);
    m_tableWidget->setColumnWidth(1, 60);
    m_tableWidget->setColumnWidth(2, 60);

    connect(m_tableWidget, &QTableWidget::cellDoubleClicked, this, &LogWidget::onLogDoubleClicked);

    mainLayout->addLayout(toolbarLayout);
    mainLayout->addWidget(m_tableWidget);

    setLayout(mainLayout);
}

void LogWidget::addLog(LogLevel level, LogType type, const QString &message, const QString &details)
{
    LogEntry entry;
    entry.timestamp = QDateTime::currentDateTime();
    entry.level = level;
    entry.type = type;
    entry.message = message;
    entry.details = details;

    m_allLogs.append(entry);
    applyFilter();
}

void LogWidget::addInfo(const QString &message, LogType type)
{
    addLog(Info, type, message);
}

void LogWidget::addSuccess(const QString &message, LogType type)
{
    addLog(Success, type, message);
}

void LogWidget::addWarning(const QString &message, LogType type)
{
    addLog(Warning, type, message);
}

void LogWidget::addError(const QString &message, LogType type)
{
    addLog(Error, type, message);
}

void LogWidget::addDebug(const QString &message, LogType type)
{
    addLog(Debug, type, message);
}

void LogWidget::clearLogs()
{
    if (m_allLogs.isEmpty()) return;

    QMessageBox::StandardButton reply = QMessageBox::question(
        this, tr("确认"), tr("确定要清空所有日志吗？"),
        QMessageBox::Yes | QMessageBox::No);

    if (reply == QMessageBox::Yes) {
        m_allLogs.clear();
        m_tableWidget->setRowCount(0);
        m_countLabel->setText(tr("0 条记录"));
    }
}

void LogWidget::exportLogs()
{
    if (m_allLogs.isEmpty()) {
        QMessageBox::information(this, tr("提示"), tr("没有可导出的日志"));
        return;
    }

    QString fileName = QFileDialog::getSaveFileName(
        this, tr("导出日志"),
        QString("ftp_log_%1.txt").arg(QDateTime::currentDateTime().toString("yyyyMMdd_HHmmss")),
        tr("文本文件 (*.txt);;所有文件 (*)"));

    if (fileName.isEmpty()) return;

    QFile file(fileName);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        QMessageBox::critical(this, tr("错误"), tr("无法打开文件: %1").arg(file.errorString()));
        return;
    }

    QTextStream out(&file);
    out.setCodec("UTF-8");

    out << "FTP Client Log Export" << Qt::endl;
    out << "Export Time: " << QDateTime::currentDateTime().toString("yyyy-MM-dd HH:mm:ss") << Qt::endl;
    out << "Total Records: " << m_allLogs.size() << Qt::endl;
    out << QString(80, '-') << Qt::endl << Qt::endl;

    foreach (const LogEntry &entry, m_allLogs) {
        out << "[" << entry.timestamp.toString("yyyy-MM-dd HH:mm:ss") << "] ";
        out << "[" << levelToString(entry.level) << "] ";
        out << "[" << typeToString(entry.type) << "] ";
        out << entry.message << Qt::endl;
        if (!entry.details.isEmpty()) {
            out << "  Details: " << entry.details << Qt::endl;
        }
    }

    file.close();
    QMessageBox::information(this, tr("完成"), tr("日志已导出到: %1").arg(fileName));
}

void LogWidget::onFilterChanged(int)
{
    applyFilter();
}

void LogWidget::onLogDoubleClicked(int row, int)
{
    if (row < 0 || row >= m_tableWidget->rowCount()) return;

    QTableWidgetItem *item = m_tableWidget->item(row, 3);
    if (item) {
        QString message = item->text();
        QMessageBox::information(this, tr("日志详情"), message);
    }
}

void LogWidget::applyFilter()
{
    int levelData = m_levelFilter->currentData().toInt();
    int typeData = m_typeFilter->currentData().toInt();

    m_currentLevelFilter = (levelData == -1) ? static_cast<LogLevel>(-1) : static_cast<LogLevel>(levelData);
    m_currentTypeFilter = (typeData == -1) ? static_cast<LogType>(-1) : static_cast<LogType>(typeData);

    m_tableWidget->setRowCount(0);
    int visibleCount = 0;

    foreach (const LogEntry &entry, m_allLogs) {
        bool levelMatch = (m_currentLevelFilter == static_cast<LogLevel>(-1)) || (entry.level == m_currentLevelFilter);
        bool typeMatch = (m_currentTypeFilter == static_cast<LogType>(-1)) || (entry.type == m_currentTypeFilter);

        if (levelMatch && typeMatch) {
            int row = m_tableWidget->rowCount();
            m_tableWidget->insertRow(row);

            QTableWidgetItem *timeItem = new QTableWidgetItem(entry.timestamp.toString("yyyy-MM-dd HH:mm:ss"));
            m_tableWidget->setItem(row, 0, timeItem);

            QTableWidgetItem *levelItem = new QTableWidgetItem(levelToString(entry.level));
            levelItem->setForeground(getLevelColor(entry.level));
            levelItem->setIcon(getLevelIcon(entry.level));
            m_tableWidget->setItem(row, 1, levelItem);

            QTableWidgetItem *typeItem = new QTableWidgetItem(typeToString(entry.type));
            m_tableWidget->setItem(row, 2, typeItem);

            QTableWidgetItem *msgItem = new QTableWidgetItem(entry.message);
            if (!entry.details.isEmpty()) {
                msgItem->setToolTip(entry.details);
            }
            m_tableWidget->setItem(row, 3, msgItem);

            visibleCount++;
        }
    }

    m_countLabel->setText(tr("%1 条记录 (共 %2 条)").arg(visibleCount).arg(m_allLogs.size()));
    m_tableWidget->scrollToBottom();
}

QString LogWidget::levelToString(LogLevel level) const
{
    switch (level) {
    case Info: return tr("信息");
    case Success: return tr("成功");
    case Warning: return tr("警告");
    case Error: return tr("错误");
    case Debug: return tr("调试");
    default: return tr("未知");
    }
}

QString LogWidget::typeToString(LogType type) const
{
    switch (type) {
    case Connection: return tr("连接");
    case Transfer: return tr("传输");
    case Command: return tr("命令");
    case Response: return tr("响应");
    case System: return tr("系统");
    default: return tr("未知");
    }
}

QString LogWidget::getLevelColor(LogLevel level) const
{
    switch (level) {
    case Info: return "#000000";
    case Success: return "#008000";
    case Warning: return "#FFA500";
    case Error: return "#FF0000";
    case Debug: return "#808080";
    default: return "#000000";
    }
}

QIcon LogWidget::getLevelIcon(LogLevel level) const
{
    QStyle *style = QApplication::style();
    switch (level) {
    case Info: return style->standardIcon(QStyle::SP_MessageBoxInformation);
    case Success: return style->standardIcon(QStyle::SP_DialogApplyButton);
    case Warning: return style->standardIcon(QStyle::SP_MessageBoxWarning);
    case Error: return style->standardIcon(QStyle::SP_MessageBoxCritical);
    case Debug: return style->standardIcon(QStyle::SP_FileDialogInfoView);
    default: return QIcon();
    }
}
