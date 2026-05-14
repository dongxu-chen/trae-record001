#ifndef LOG_WIDGET_H
#define LOG_WIDGET_H

#include <QWidget>
#include <QTableWidget>
#include <QPushButton>
#include <QComboBox>
#include <QLabel>
#include <QDateTime>
#include <QList>

class LogWidget : public QWidget
{
    Q_OBJECT

public:
    enum LogLevel {
        Info = 0,
        Success,
        Warning,
        Error,
        Debug
    };

    enum LogType {
        Connection = 0,
        Transfer,
        Command,
        Response,
        System
    };

    struct LogEntry {
        QDateTime timestamp;
        LogLevel level;
        LogType type;
        QString message;
        QString details;
    };

    explicit LogWidget(QWidget *parent = nullptr);
    ~LogWidget();

public slots:
    void addLog(LogLevel level, LogType type, const QString &message, const QString &details = QString());
    void addInfo(const QString &message, LogType type = System);
    void addSuccess(const QString &message, LogType type = System);
    void addWarning(const QString &message, LogType type = System);
    void addError(const QString &message, LogType type = System);
    void addDebug(const QString &message, LogType type = System);
    void clearLogs();
    void exportLogs();

private slots:
    void onFilterChanged(int index);
    void onLogDoubleClicked(int row, int column);

private:
    void setupUI();
    void applyFilter();
    QString levelToString(LogLevel level) const;
    QString typeToString(LogType type) const;
    QString getLevelColor(LogLevel level) const;
    QIcon getLevelIcon(LogLevel level) const;

    QTableWidget *m_tableWidget;
    QPushButton *m_clearButton;
    QPushButton *m_exportButton;
    QComboBox *m_levelFilter;
    QComboBox *m_typeFilter;
    QLabel *m_countLabel;

    QList<LogEntry> m_allLogs;
    LogLevel m_currentLevelFilter;
    LogType m_currentTypeFilter;
};

#endif // LOG_WIDGET_H
