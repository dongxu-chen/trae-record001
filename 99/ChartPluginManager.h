#ifndef CHARTPLUGINMANAGER_H
#define CHARTPLUGINMANAGER_H

#include <QObject>
#include <QList>
#include <QStringList>
#include <QMap>
#include <QPainter>
#include <QRectF>
#include <QColor>
#include "plugin_interface.h"

class LineChartPlugin : public QObject, public IChartPlugin {
    Q_OBJECT
    Q_INTERFACES(IChartPlugin)
public:
    QString name() const override { return "Line Chart"; }
    ChartType chartType() const override { return ChartType::Line; }
    QString description() const override { return "Basic line chart connecting data points"; }
    QStringList supportedStyles() const override { return {"Solid", "Dashed", "Dotted"}; }
    
    void draw(QPainter *painter,
              const QList<ChartDataPoint> &points,
              const QRectF &plotArea,
              const QColor &lineColor,
              const QVariantMap &options = QVariantMap()) override;
};

class BarChartPlugin : public QObject, public IChartPlugin {
    Q_OBJECT
    Q_INTERFACES(IChartPlugin)
public:
    QString name() const override { return "Bar Chart"; }
    ChartType chartType() const override { return ChartType::Bar; }
    QString description() const override { return "Vertical bar chart"; }
    QStringList supportedStyles() const override { return {"Solid", "Gradient"}; }
    
    void draw(QPainter *painter,
              const QList<ChartDataPoint> &points,
              const QRectF &plotArea,
              const QColor &lineColor,
              const QVariantMap &options = QVariantMap()) override;
};

class AreaChartPlugin : public QObject, public IChartPlugin {
    Q_OBJECT
    Q_INTERFACES(IChartPlugin)
public:
    QString name() const override { return "Area Chart"; }
    ChartType chartType() const override { return ChartType::Area; }
    QString description() const override { return "Filled area under the line"; }
    QStringList supportedStyles() const override { return {"Solid", "Gradient"}; }
    
    void draw(QPainter *painter,
              const QList<ChartDataPoint> &points,
              const QRectF &plotArea,
              const QColor &lineColor,
              const QVariantMap &options = QVariantMap()) override;
};

class StepChartPlugin : public QObject, public IChartPlugin {
    Q_OBJECT
    Q_INTERFACES(IChartPlugin)
public:
    QString name() const override { return "Step Chart"; }
    ChartType chartType() const override { return ChartType::Step; }
    QString description() const override { return "Step-wise line chart"; }
    QStringList supportedStyles() const override { return {"Left", "Center", "Right"}; }
    
    void draw(QPainter *painter,
              const QList<ChartDataPoint> &points,
              const QRectF &plotArea,
              const QColor &lineColor,
              const QVariantMap &options = QVariantMap()) override;
};

class ChartPluginManager : public QObject
{
    Q_OBJECT
public:
    explicit ChartPluginManager(QObject *parent = nullptr);
    
    QStringList pluginNames() const;
    IChartPlugin* plugin(int index) const;
    IChartPlugin* pluginByName(const QString &name) const;
    int pluginCount() const;
    int indexOfPlugin(const QString &name) const;
    
    QMap<QString, IChartPlugin*> plugins() const { return m_plugins; }

private:
    void registerBuiltInPlugins();
    
    QMap<QString, IChartPlugin*> m_plugins;
    QStringList m_pluginOrder;
};

#endif // CHARTPLUGINMANAGER_H
