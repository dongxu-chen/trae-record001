#include "ChartModel.h"
#include "ChartPluginManager.h"
#include <QDateTime>
#include <QtMath>

ChartModel::ChartModel(QObject *parent)
    : QAbstractListModel(parent)
    , m_processTimer(new QTimer(this))
    , m_rateTimer(new QTimer(this))
    , m_title("Chart Title")
    , m_xAxisLabel("Time (s)")
    , m_yAxisLabel("Value")
    , m_lineColor("#3498db")
    , m_maxBufferSize(10000)
    , m_useRollingBuffer(true)
    , m_currentChartType(0)
    , m_autoScrollX(true)
    , m_visibleTimeRange(30.0)
    , m_lastRateTime(QDateTime::currentMSecsSinceEpoch())
    , m_dataRate(0.0)
    , m_pointsSinceLastRate(0)
    , m_pluginManager(new ChartPluginManager(this))
{
    connect(m_processTimer, &QTimer::timeout, this, &ChartModel::processPendingData);
    connect(m_rateTimer, &QTimer::timeout, this, &ChartModel::updateDataRate);
    
    m_processTimer->setInterval(30);
    m_rateTimer->setInterval(1000);
}

ChartModel::~ChartModel()
{
    stop();
}

void ChartModel::start()
{
    if (!m_processTimer->isActive()) {
        m_processTimer->start();
    }
    if (!m_rateTimer->isActive()) {
        m_rateTimer->start();
    }
}

void ChartModel::stop()
{
    if (m_processTimer->isActive()) {
        m_processTimer->stop();
    }
    if (m_rateTimer->isActive()) {
        m_rateTimer->stop();
    }
}

int ChartModel::rowCount(const QModelIndex &parent) const
{
    if (parent.isValid())
        return 0;
    QMutexLocker locker(&m_mutex);
    return m_points.size();
}

QVariant ChartModel::data(const QModelIndex &index, int role) const
{
    QMutexLocker locker(&m_mutex);
    
    if (!index.isValid() || index.row() >= m_points.size())
        return QVariant();

    const ChartDataPoint &point = m_points[index.row()];

    switch (role) {
    case XRole:
        return point.x;
    case YRole:
        return point.y;
    default:
        return QVariant();
    }
}

QHash<int, QByteArray> ChartModel::roleNames() const
{
    QHash<int, QByteArray> roles;
    roles[XRole] = "x";
    roles[YRole] = "y";
    return roles;
}

QString ChartModel::title() const
{
    return m_title;
}

void ChartModel::setTitle(const QString &title)
{
    if (m_title != title) {
        m_title = title;
        emit titleChanged();
    }
}

QString ChartModel::xAxisLabel() const
{
    return m_xAxisLabel;
}

void ChartModel::setXAxisLabel(const QString &label)
{
    if (m_xAxisLabel != label) {
        m_xAxisLabel = label;
        emit xAxisLabelChanged();
    }
}

QString ChartModel::yAxisLabel() const
{
    return m_yAxisLabel;
}

void ChartModel::setYAxisLabel(const QString &label)
{
    if (m_yAxisLabel != label) {
        m_yAxisLabel = label;
        emit yAxisLabelChanged();
    }
}

QColor ChartModel::lineColor() const
{
    return m_lineColor;
}

void ChartModel::setLineColor(const QColor &color)
{
    if (m_lineColor != color) {
        m_lineColor = color;
        emit lineColorChanged();
    }
}

int ChartModel::pointCount() const
{
    QMutexLocker locker(&m_mutex);
    return m_points.size();
}

int ChartModel::maxBufferSize() const
{
    return m_maxBufferSize;
}

void ChartModel::setMaxBufferSize(int size)
{
    if (m_maxBufferSize != size && size > 0) {
        m_maxBufferSize = size;
        emit maxBufferSizeChanged();
        trimBuffer();
    }
}

bool ChartModel::useRollingBuffer() const
{
    return m_useRollingBuffer;
}

void ChartModel::setUseRollingBuffer(bool enable)
{
    if (m_useRollingBuffer != enable) {
        m_useRollingBuffer = enable;
        emit useRollingBufferChanged();
    }
}

int ChartModel::currentChartType() const
{
    return m_currentChartType;
}

void ChartModel::setCurrentChartType(int type)
{
    if (m_currentChartType != type && type >= 0 && type < m_pluginManager->pluginCount()) {
        m_currentChartType = type;
        emit currentChartTypeChanged();
    }
}

QStringList ChartModel::availableChartTypes() const
{
    return m_pluginManager->pluginNames();
}

bool ChartModel::autoScrollX() const
{
    return m_autoScrollX;
}

void ChartModel::setAutoScrollX(bool enable)
{
    if (m_autoScrollX != enable) {
        m_autoScrollX = enable;
        emit autoScrollXChanged();
    }
}

qreal ChartModel::visibleTimeRange() const
{
    return m_visibleTimeRange;
}

void ChartModel::setVisibleTimeRange(qreal seconds)
{
    if (!qFuzzyCompare(m_visibleTimeRange, seconds) && seconds > 0) {
        m_visibleTimeRange = seconds;
        emit visibleTimeRangeChanged();
    }
}

qreal ChartModel::dataRate() const
{
    return m_dataRate;
}

void ChartModel::addPoint(qreal x, qreal y)
{
    QMutexLocker locker(&m_mutex);
    m_pendingData.enqueue(qMakePair(x, y));
    
    if (!m_processTimer->isActive()) {
        m_processTimer->start();
    }
}

void ChartModel::addPoints(const QVariantList &points)
{
    if (points.isEmpty())
        return;

    QMutexLocker locker(&m_mutex);
    
    for (const QVariant &v : points) {
        QVariantMap map = v.toMap();
        qreal x = map["x"].toReal();
        qreal y = map["y"].toReal();
        m_pendingData.enqueue(qMakePair(x, y));
    }
    
    if (!m_processTimer->isActive()) {
        m_processTimer->start();
    }
}

void ChartModel::removePoint(int index)
{
    QMutexLocker locker(&m_mutex);
    
    if (index < 0 || index >= m_points.size())
        return;

    beginRemoveRows(QModelIndex(), index, index);
    m_points.removeAt(index);
    endRemoveRows();
    emit pointCountChanged();
}

void ChartModel::removePoints(int from, int count)
{
    QMutexLocker locker(&m_mutex);
    
    if (from < 0 || count <= 0 || from + count > m_points.size())
        return;

    beginRemoveRows(QModelIndex(), from, from + count - 1);
    for (int i = 0; i < count; ++i) {
        m_points.removeAt(from);
    }
    endRemoveRows();
    emit pointCountChanged();
}

void ChartModel::updatePoint(int index, qreal x, qreal y)
{
    QMutexLocker locker(&m_mutex);
    
    if (index < 0 || index >= m_points.size())
        return;

    m_points[index].x = x;
    m_points[index].y = y;
    emit dataChanged(createIndex(index, 0), createIndex(index, 0), {XRole, YRole});
}

void ChartModel::clearPoints()
{
    QMutexLocker locker(&m_mutex);
    
    beginResetModel();
    m_points.clear();
    m_pendingData.clear();
    endResetModel();
    emit pointCountChanged();
}

QVariantList ChartModel::pointsAsVariantList() const
{
    QMutexLocker locker(&m_mutex);
    
    QVariantList list;
    list.reserve(m_points.size());
    for (const auto &point : m_points) {
        QVariantMap map;
        map["x"] = point.x;
        map["y"] = point.y;
        list.append(map);
    }
    return list;
}

QVariantList ChartModel::getDownsampledPoints(int maxPoints) const
{
    QMutexLocker locker(&m_mutex);
    
    if (maxPoints <= 0 || m_points.size() <= maxPoints) {
        QVariantList list;
        list.reserve(m_points.size());
        for (const auto &point : m_points) {
            QVariantMap map;
            map["x"] = point.x;
            map["y"] = point.y;
            list.append(map);
        }
        return list;
    }

    QVariantList result;
    result.reserve(maxPoints);

    double step = static_cast<double>(m_points.size() - 1) / (maxPoints - 1);
    for (int i = 0; i < maxPoints; ++i) {
        int idx = qMin(static_cast<int>(i * step), m_points.size() - 1);
        const ChartDataPoint &p = m_points[idx];
        QVariantMap map;
        map["x"] = p.x;
        map["y"] = p.y;
        result.append(map);
    }

    return result;
}

QVariantMap ChartModel::getMinMax() const
{
    QMutexLocker locker(&m_mutex);
    
    QVariantMap result;
    if (m_points.isEmpty()) {
        result["minX"] = 0.0;
        result["maxX"] = 10.0;
        result["minY"] = 0.0;
        result["maxY"] = 10.0;
        return result;
    }

    qreal minX = m_points[0].x, maxX = m_points[0].x;
    qreal minY = m_points[0].y, maxY = m_points[0].y;

    for (const auto &p : m_points) {
        minX = qMin(minX, p.x);
        maxX = qMax(maxX, p.x);
        minY = qMin(minY, p.y);
        maxY = qMax(maxY, p.y);
    }

    qreal xPad = (maxX - minX) * 0.1;
    qreal yPad = (maxY - minY) * 0.1;
    if (xPad == 0) xPad = 1.0;
    if (yPad == 0) yPad = 1.0;

    result["minX"] = minX - xPad;
    result["maxX"] = maxX + xPad;
    result["minY"] = minY - yPad;
    result["maxY"] = maxY + yPad;

    return result;
}

QVariantMap ChartModel::getVisibleRange() const
{
    QMutexLocker locker(&m_mutex);
    
    QVariantMap result;
    if (m_points.isEmpty()) {
        result["minX"] = 0.0;
        result["maxX"] = m_visibleTimeRange;
        result["minY"] = 0.0;
        result["maxY"] = 10.0;
        return result;
    }

    qreal maxX = m_points.last().x;
    qreal minX = maxX - m_visibleTimeRange;
    
    if (minX < m_points.first().x) {
        minX = m_points.first().x;
    }
    
    qreal minY = std::numeric_limits<qreal>::max();
    qreal maxY = std::numeric_limits<qreal>::min();
    bool found = false;
    
    for (const auto &p : m_points) {
        if (p.x >= minX && p.x <= maxX) {
            found = true;
            minY = qMin(minY, p.y);
            maxY = qMax(maxY, p.y);
        }
    }
    
    if (!found) {
        minY = m_points.first().y;
        maxY = m_points.first().y;
    }

    qreal yPad = (maxY - minY) * 0.1;
    if (yPad == 0) yPad = 1.0;

    result["minX"] = minX;
    result["maxX"] = maxX;
    result["minY"] = minY - yPad;
    result["maxY"] = maxY + yPad;

    return result;
}

void ChartModel::loadChartPlugins()
{
    emit availableChartTypesChanged();
}

void ChartModel::setChartTypeByName(const QString &name)
{
    int idx = m_pluginManager->indexOfPlugin(name);
    if (idx >= 0) {
        setCurrentChartType(idx);
    }
}

QString ChartModel::currentChartTypeName() const
{
    auto plugin = m_pluginManager->plugin(m_currentChartType);
    return plugin ? plugin->name() : QString();
}

QList<ChartDataPoint> ChartModel::dataPoints() const
{
    QMutexLocker locker(&m_mutex);
    return m_points;
}

void ChartModel::processPendingData()
{
    QMutexLocker locker(&m_mutex);
    
    if (m_pendingData.isEmpty()) {
        m_processTimer->stop();
        return;
    }

    int processedCount = 0;
    int droppedCount = 0;
    int batchSize = qMin(m_pendingData.size(), 100);
    
    int startIdx = m_points.size();
    
    for (int i = 0; i < batchSize && !m_pendingData.isEmpty(); ++i) {
        auto pair = m_pendingData.dequeue();
        
        if (m_useRollingBuffer && m_points.size() >= m_maxBufferSize) {
            beginRemoveRows(QModelIndex(), 0, 0);
            m_points.removeFirst();
            endRemoveRows();
            startIdx--;
            droppedCount++;
        }
        
        m_points.append(ChartDataPoint(pair.first, pair.second));
        processedCount++;
        m_pointsSinceLastRate++;
    }
    
    if (processedCount > 0) {
        int endIdx = startIdx + processedCount - 1;
        beginInsertRows(QModelIndex(), startIdx, endIdx);
        endInsertRows();
        
        emit pointCountChanged();
        emit newPointsAdded(processedCount);
    }
    
    if (droppedCount > 0) {
        emit bufferOverflow(droppedCount);
    }
    
    if (m_pendingData.isEmpty()) {
        m_processTimer->stop();
    }
}

void ChartModel::updateDataRate()
{
    qint64 currentTime = QDateTime::currentMSecsSinceEpoch();
    qreal elapsed = (currentTime - m_lastRateTime) / 1000.0;
    
    if (elapsed > 0) {
        m_dataRate = static_cast<qreal>(m_pointsSinceLastRate) / elapsed;
        emit dataRateChanged();
    }
    
    m_lastRateTime = currentTime;
    m_pointsSinceLastRate = 0;
}

void ChartModel::trimBuffer()
{
    QMutexLocker locker(&m_mutex);
    
    if (m_useRollingBuffer && m_points.size() > m_maxBufferSize) {
        int excess = m_points.size() - m_maxBufferSize;
        beginRemoveRows(QModelIndex(), 0, excess - 1);
        for (int i = 0; i < excess; ++i) {
            m_points.removeFirst();
        }
        endRemoveRows();
        emit pointCountChanged();
        emit bufferOverflow(excess);
    }
}
