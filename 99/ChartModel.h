#ifndef CHARTMODEL_H
#define CHARTMODEL_H

#include <QAbstractListModel>
#include <QObject>
#include <QList>
#include <QVariant>
#include <QColor>
#include <QMutex>
#include <QQueue>
#include <QTimer>
#include "plugin_interface.h"

class ChartPluginManager;

class ChartModel : public QAbstractListModel
{
    Q_OBJECT
    Q_PROPERTY(QString title READ title WRITE setTitle NOTIFY titleChanged)
    Q_PROPERTY(QString xAxisLabel READ xAxisLabel WRITE setXAxisLabel NOTIFY xAxisLabelChanged)
    Q_PROPERTY(QString yAxisLabel READ yAxisLabel WRITE setYAxisLabel NOTIFY yAxisLabelChanged)
    Q_PROPERTY(QColor lineColor READ lineColor WRITE setLineColor NOTIFY lineColorChanged)
    Q_PROPERTY(int pointCount READ pointCount NOTIFY pointCountChanged)
    Q_PROPERTY(int maxBufferSize READ maxBufferSize WRITE setMaxBufferSize NOTIFY maxBufferSizeChanged)
    Q_PROPERTY(bool useRollingBuffer READ useRollingBuffer WRITE setUseRollingBuffer NOTIFY useRollingBufferChanged)
    Q_PROPERTY(int currentChartType READ currentChartType WRITE setCurrentChartType NOTIFY currentChartTypeChanged)
    Q_PROPERTY(QStringList availableChartTypes READ availableChartTypes NOTIFY availableChartTypesChanged)
    Q_PROPERTY(bool autoScrollX READ autoScrollX WRITE setAutoScrollX NOTIFY autoScrollXChanged)
    Q_PROPERTY(qreal visibleTimeRange READ visibleTimeRange WRITE setVisibleTimeRange NOTIFY visibleTimeRangeChanged)
    Q_PROPERTY(qreal dataRate READ dataRate NOTIFY dataRateChanged)

public:
    enum Roles {
        XRole = Qt::UserRole + 1,
        YRole
    };

    explicit ChartModel(QObject *parent = nullptr);
    ~ChartModel();

    int rowCount(const QModelIndex &parent = QModelIndex()) const override;
    QVariant data(const QModelIndex &index, int role = Qt::DisplayRole) const override;
    QHash<int, QByteArray> roleNames() const override;

    QString title() const;
    void setTitle(const QString &title);

    QString xAxisLabel() const;
    void setXAxisLabel(const QString &label);

    QString yAxisLabel() const;
    void setYAxisLabel(const QString &label);

    QColor lineColor() const;
    void setLineColor(const QColor &color);

    int pointCount() const;
    int maxBufferSize() const;
    void setMaxBufferSize(int size);

    bool useRollingBuffer() const;
    void setUseRollingBuffer(bool enable);

    int currentChartType() const;
    void setCurrentChartType(int type);

    QStringList availableChartTypes() const;

    bool autoScrollX() const;
    void setAutoScrollX(bool enable);

    qreal visibleTimeRange() const;
    void setVisibleTimeRange(qreal seconds);

    qreal dataRate() const;

    Q_INVOKABLE void addPoint(qreal x, qreal y);
    Q_INVOKABLE void addPoints(const QVariantList &points);
    Q_INVOKABLE void removePoint(int index);
    Q_INVOKABLE void removePoints(int from, int count);
    Q_INVOKABLE void updatePoint(int index, qreal x, qreal y);
    Q_INVOKABLE void clearPoints();
    Q_INVOKABLE QVariantList pointsAsVariantList() const;
    Q_INVOKABLE QVariantList getDownsampledPoints(int maxPoints) const;
    Q_INVOKABLE QVariantMap getMinMax() const;
    Q_INVOKABLE QVariantMap getVisibleRange() const;

    Q_INVOKABLE void loadChartPlugins();
    Q_INVOKABLE void setChartTypeByName(const QString &name);
    Q_INVOKABLE QString currentChartTypeName() const;

    QList<ChartDataPoint> dataPoints() const;

    Q_INVOKABLE void start();
    Q_INVOKABLE void stop();

signals:
    void titleChanged();
    void xAxisLabelChanged();
    void yAxisLabelChanged();
    void lineColorChanged();
    void pointCountChanged();
    void maxBufferSizeChanged();
    void useRollingBufferChanged();
    void currentChartTypeChanged();
    void availableChartTypesChanged();
    void autoScrollXChanged();
    void visibleTimeRangeChanged();
    void dataRateChanged();
    void newPointsAdded(int count);
    void bufferOverflow(int droppedPoints);

private slots:
    void processPendingData();
    void updateDataRate();

private:
    mutable QMutex m_mutex;
    QList<ChartDataPoint> m_points;
    QQueue<QPair<qreal, qreal>> m_pendingData;
    QTimer *m_processTimer;
    QTimer *m_rateTimer;

    QString m_title;
    QString m_xAxisLabel;
    QString m_yAxisLabel;
    QColor m_lineColor;

    int m_maxBufferSize;
    bool m_useRollingBuffer;
    int m_currentChartType;
    bool m_autoScrollX;
    qreal m_visibleTimeRange;

    qint64 m_lastRateTime;
    qreal m_dataRate;
    int m_pointsSinceLastRate;

    ChartPluginManager *m_pluginManager;

    void trimBuffer();
};

#endif // CHARTMODEL_H
