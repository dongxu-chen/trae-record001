#ifndef EXPORTER_H
#define EXPORTER_H

#include <QObject>
#include <QString>
#include <QSize>
#include <QPainter>
#include <QRectF>
#include <QPointF>

class ChartModel;

class Exporter : public QObject
{
    Q_OBJECT
public:
    explicit Exporter(QObject *parent = nullptr);

    Q_INVOKABLE bool exportToPng(const QString &filePath, ChartModel *model, const QSize &size = QSize(800, 600));
    Q_INVOKABLE bool exportToSvg(const QString &filePath, ChartModel *model, const QSize &size = QSize(800, 600));

private:
    void drawChart(QPainter &painter, ChartModel *model, const QSize &size);
    void drawAxes(QPainter &painter, const QRectF &plotArea, ChartModel *model, 
                  qreal minX, qreal maxX, qreal minY, qreal maxY);
    void drawPlot(QPainter &painter, const QRectF &plotArea, ChartModel *model,
                  qreal minX, qreal maxX, qreal minY, qreal maxY);
    QPointF mapToScene(qreal x, qreal y, const QRectF &plotArea,
                       qreal minX, qreal maxX, qreal minY, qreal maxY);
    
    qreal niceTickValue(qreal value, bool round);
    void calculateAxisTicks(qreal minVal, qreal maxVal, int tickCount,
                            QVector<qreal> &ticks, qreal &niceMin, qreal &niceMax);
};

#endif // EXPORTER_H
