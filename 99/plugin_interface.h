#ifndef PLUGIN_INTERFACE_H
#define PLUGIN_INTERFACE_H

#include <QObject>
#include <QString>
#include <QStringList>
#include <QVariant>
#include <QPainter>
#include <QRectF>
#include <QPointF>

struct ChartDataPoint {
    qreal x;
    qreal y;
    Q_GADGET
    Q_PROPERTY(qreal x MEMBER x)
    Q_PROPERTY(qreal y MEMBER y)
public:
    ChartDataPoint() : x(0), y(0) {}
    ChartDataPoint(qreal x_, qreal y_) : x(x_), y(y_) {}
};
Q_DECLARE_METATYPE(ChartDataPoint)

enum class ChartType {
    Line,
    Bar,
    Scatter,
    Area,
    Step,
    Spline
};
Q_ENUMS(ChartType)

class IChartPlugin {
public:
    virtual ~IChartPlugin() = default;

    virtual QString name() const = 0;
    virtual ChartType chartType() const = 0;
    virtual QString description() const = 0;
    virtual QStringList supportedStyles() const = 0;

    virtual void draw(QPainter *painter,
                     const QList<ChartDataPoint> &points,
                     const QRectF &plotArea,
                     const QColor &lineColor,
                     const QVariantMap &options = QVariantMap()) = 0;

    virtual bool supportsAnimation() const { return false; }
    virtual int maxPoints() const { return -1; }
};

#define ChartPluginInterface_iid "com.example.ChartPluginInterface/1.0"
Q_DECLARE_INTERFACE(IChartPlugin, ChartPluginInterface_iid)

#endif // PLUGIN_INTERFACE_H
