#include "ChartPluginManager.h"
#include <QLinearGradient>
#include <QPen>
#include <QBrush>
#include <QPainterPath>
#include <QtMath>

static QPointF mapToScene(const ChartDataPoint &point,
                          const QRectF &plotArea,
                          qreal minX, qreal maxX,
                          qreal minY, qreal maxY)
{
    qreal tX = (point.x - minX) / (maxX - minX);
    qreal tY = (point.y - minY) / (maxY - minY);
    return QPointF(
        plotArea.left() + tX * plotArea.width(),
        plotArea.bottom() - tY * plotArea.height()
    );
}

static void getMinMax(const QList<ChartDataPoint> &points,
                      qreal &minX, qreal &maxX,
                      qreal &minY, qreal &maxY)
{
    if (points.isEmpty()) {
        minX = 0; maxX = 10; minY = 0; maxY = 10;
        return;
    }
    
    minX = maxX = points[0].x;
    minY = maxY = points[0].y;
    
    for (const auto &p : points) {
        minX = qMin(minX, p.x);
        maxX = qMax(maxX, p.x);
        minY = qMin(minY, p.y);
        maxY = qMax(maxY, p.y);
    }
    
    qreal xPad = (maxX - minX) * 0.1;
    qreal yPad = (maxY - minY) * 0.1;
    if (xPad == 0) xPad = 1;
    if (yPad == 0) yPad = 1;
    minX -= xPad;
    maxX += xPad;
    minY -= yPad;
    maxY += yPad;
}

void LineChartPlugin::draw(QPainter *painter,
                           const QList<ChartDataPoint> &points,
                           const QRectF &plotArea,
                           const QColor &lineColor,
                           const QVariantMap &options)
{
    if (points.size() < 2) return;
    
    qreal minX, maxX, minY, maxY;
    getMinMax(points, minX, maxX, minY, maxY);
    
    QList<QPointF> scenePoints;
    for (const auto &p : points) {
        scenePoints.append(mapToScene(p, plotArea, minX, maxX, minY, maxY));
    }
    
    QString style = options.value("style", "Solid").toString();
    Qt::PenStyle penStyle = Qt::SolidLine;
    if (style == "Dashed") penStyle = Qt::DashLine;
    else if (style == "Dotted") penStyle = Qt::DotLine;
    
    QPen pen(lineColor, 2, penStyle, Qt::RoundCap, Qt::RoundJoin);
    painter->setPen(pen);
    painter->setBrush(Qt::NoBrush);
    
    QPainterPath path;
    path.moveTo(scenePoints[0]);
    for (int i = 1; i < scenePoints.size(); ++i) {
        path.lineTo(scenePoints[i]);
    }
    painter->drawPath(path);
    
    if (points.size() <= 100) {
        painter->setBrush(lineColor);
        painter->setPen(QPen(Qt::white, 2));
        for (const auto &p : scenePoints) {
            painter->drawEllipse(p, 4, 4);
        }
    }
}

void BarChartPlugin::draw(QPainter *painter,
                          const QList<ChartDataPoint> &points,
                          const QRectF &plotArea,
                          const QColor &lineColor,
                          const QVariantMap &options)
{
    if (points.isEmpty()) return;
    
    qreal minX, maxX, minY, maxY;
    getMinMax(points, minX, maxX, minY, maxY);
    
    QString style = options.value("style", "Solid").toString();
    qreal barWidth = plotArea.width() / points.size() * 0.6;
    
    for (const auto &p : points) {
        QPointF pos = mapToScene(p, plotArea, minX, maxX, minY, maxY);
        qreal barX = pos.x() - barWidth / 2;
        qreal barY = pos.y();
        qreal barHeight = plotArea.bottom() - barY;
        
        if (style == "Gradient") {
            QLinearGradient gradient(barX, barY, barX, barY + barHeight);
            QColor c1 = lineColor;
            QColor c2 = lineColor;
            c2.setAlpha(80);
            gradient.setColorAt(0, c1);
            gradient.setColorAt(1, c2);
            painter->fillRect(QRectF(barX, barY, barWidth, barHeight), gradient);
        } else {
            painter->fillRect(QRectF(barX, barY, barWidth, barHeight), lineColor);
        }
        
        painter->setPen(QPen(Qt::white, 1));
        painter->drawRect(QRectF(barX, barY, barWidth, barHeight));
    }
}

void AreaChartPlugin::draw(QPainter *painter,
                           const QList<ChartDataPoint> &points,
                           const QRectF &plotArea,
                           const QColor &lineColor,
                           const QVariantMap &options)
{
    if (points.size() < 2) return;
    
    qreal minX, maxX, minY, maxY;
    getMinMax(points, minX, maxX, minY, maxY);
    
    QList<QPointF> scenePoints;
    for (const auto &p : points) {
        scenePoints.append(mapToScene(p, plotArea, minX, maxX, minY, maxY));
    }
    
    QPainterPath path;
    path.moveTo(scenePoints[0].x(), plotArea.bottom());
    for (const auto &p : scenePoints) {
        path.lineTo(p);
    }
    path.lineTo(scenePoints.last().x(), plotArea.bottom());
    path.closeSubpath();
    
    QString style = options.value("style", "Gradient").toString();
    
    if (style == "Gradient") {
        QLinearGradient gradient(0, plotArea.top(), 0, plotArea.bottom());
        QColor c1 = lineColor;
        c1.setAlpha(180);
        QColor c2 = lineColor;
        c2.setAlpha(30);
        gradient.setColorAt(0, c1);
        gradient.setColorAt(1, c2);
        painter->fillPath(path, gradient);
    } else {
        QColor fillColor = lineColor;
        fillColor.setAlpha(100);
        painter->fillPath(path, fillColor);
    }
    
    QPen pen(lineColor, 2);
    pen.setCapStyle(Qt::RoundCap);
    pen.setJoinStyle(Qt::RoundJoin);
    painter->setPen(pen);
    painter->setBrush(Qt::NoBrush);
    
    QPainterPath linePath;
    linePath.moveTo(scenePoints[0]);
    for (int i = 1; i < scenePoints.size(); ++i) {
        linePath.lineTo(scenePoints[i]);
    }
    painter->drawPath(linePath);
}

void StepChartPlugin::draw(QPainter *painter,
                           const QList<ChartDataPoint> &points,
                           const QRectF &plotArea,
                           const QColor &lineColor,
                           const QVariantMap &options)
{
    if (points.size() < 2) return;
    
    qreal minX, maxX, minY, maxY;
    getMinMax(points, minX, maxX, minY, maxY);
    
    QList<QPointF> scenePoints;
    for (const auto &p : points) {
        scenePoints.append(mapToScene(p, plotArea, minX, maxX, minY, maxY));
    }
    
    QString style = options.value("style", "Left").toString();
    
    QPen pen(lineColor, 2, Qt::SolidLine, Qt::RoundCap, Qt::RoundJoin);
    painter->setPen(pen);
    painter->setBrush(Qt::NoBrush);
    
    QPainterPath path;
    path.moveTo(scenePoints[0]);
    
    if (style == "Center") {
        for (int i = 1; i < scenePoints.size(); ++i) {
            qreal midX = (scenePoints[i-1].x() + scenePoints[i].x()) / 2;
            path.lineTo(midX, scenePoints[i-1].y());
            path.lineTo(midX, scenePoints[i].y());
            path.lineTo(scenePoints[i]);
        }
    } else if (style == "Right") {
        for (int i = 1; i < scenePoints.size(); ++i) {
            path.lineTo(scenePoints[i].x(), scenePoints[i-1].y());
            path.lineTo(scenePoints[i]);
        }
    } else {
        for (int i = 1; i < scenePoints.size(); ++i) {
            path.lineTo(scenePoints[i-1].x(), scenePoints[i].y());
            path.lineTo(scenePoints[i]);
        }
    }
    
    painter->drawPath(path);
    
    if (points.size() <= 100) {
        painter->setBrush(lineColor);
        painter->setPen(QPen(Qt::white, 2));
        for (const auto &p : scenePoints) {
            painter->drawEllipse(p, 4, 4);
        }
    }
}

ChartPluginManager::ChartPluginManager(QObject *parent)
    : QObject(parent)
{
    registerBuiltInPlugins();
}

void ChartPluginManager::registerBuiltInPlugins()
{
    m_plugins["Line Chart"] = new LineChartPlugin();
    m_pluginOrder.append("Line Chart");
    
    m_plugins["Bar Chart"] = new BarChartPlugin();
    m_pluginOrder.append("Bar Chart");
    
    m_plugins["Area Chart"] = new AreaChartPlugin();
    m_pluginOrder.append("Area Chart");
    
    m_plugins["Step Chart"] = new StepChartPlugin();
    m_pluginOrder.append("Step Chart");
}

QStringList ChartPluginManager::pluginNames() const
{
    return m_pluginOrder;
}

IChartPlugin* ChartPluginManager::plugin(int index) const
{
    if (index < 0 || index >= m_pluginOrder.size())
        return nullptr;
    return m_plugins.value(m_pluginOrder[index]);
}

IChartPlugin* ChartPluginManager::pluginByName(const QString &name) const
{
    return m_plugins.value(name);
}

int ChartPluginManager::pluginCount() const
{
    return m_plugins.size();
}

int ChartPluginManager::indexOfPlugin(const QString &name) const
{
    return m_pluginOrder.indexOf(name);
}
