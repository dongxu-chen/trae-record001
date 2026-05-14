#include "Exporter.h"
#include "ChartModel.h"

#include <QImage>
#include <QSvgGenerator>
#include <QPainter>
#include <QPen>
#include <QFont>
#include <QRectF>
#include <QVariantList>
#include <QMap>
#include <QVector>
#include <QtMath>

Exporter::Exporter(QObject *parent)
    : QObject(parent)
{
}

qreal Exporter::niceTickValue(qreal value, bool round)
{
    qreal exponent = std::floor(std::log10(value));
    qreal fraction = value / std::pow(10.0, exponent);
    qreal niceFraction;

    if (round) {
        if (fraction < 1.5) niceFraction = 1.0;
        else if (fraction < 3.0) niceFraction = 2.0;
        else if (fraction < 7.0) niceFraction = 5.0;
        else niceFraction = 10.0;
    } else {
        if (fraction <= 1.0) niceFraction = 1.0;
        else if (fraction <= 2.0) niceFraction = 2.0;
        else if (fraction <= 5.0) niceFraction = 5.0;
        else niceFraction = 10.0;
    }

    return niceFraction * std::pow(10.0, exponent);
}

void Exporter::calculateAxisTicks(qreal minVal, qreal maxVal, int tickCount,
                                   QVector<qreal> &ticks, qreal &niceMin, qreal &niceMax)
{
    ticks.clear();
    qreal range = niceTickValue(maxVal - minVal, false);
    qreal tickSpacing = niceTickValue(range / (tickCount - 1), true);
    niceMin = std::floor(minVal / tickSpacing) * tickSpacing;
    niceMax = std::ceil(maxVal / tickSpacing) * tickSpacing;

    for (qreal t = niceMin; t <= niceMax + tickSpacing / 100.0; t += tickSpacing) {
        ticks.append(t);
    }
}

bool Exporter::exportToPng(const QString &filePath, ChartModel *model, const QSize &size)
{
    if (!model)
        return false;

    QImage image(size, QImage::Format_RGB32);
    image.fill(Qt::white);
    image.setDevicePixelRatio(1.0);

    QPainter painter(&image);
    painter.setRenderHints(QPainter::Antialiasing | 
                           QPainter::SmoothPixmapTransform | 
                           QPainter::TextAntialiasing);
    
    painter.fillRect(image.rect(), Qt::white);
    
    drawChart(painter, model, size);
    painter.end();

    return image.save(filePath, "PNG");
}

bool Exporter::exportToSvg(const QString &filePath, ChartModel *model, const QSize &size)
{
    if (!model)
        return false;

    QSvgGenerator generator;
    generator.setFileName(filePath);
    generator.setSize(size);
    generator.setViewBox(QRect(0, 0, size.width(), size.height()));
    generator.setTitle(model->title());
    generator.setDescription("Exported chart from ChartEditor");

    QPainter painter(&generator);
    painter.setRenderHints(QPainter::Antialiasing | 
                           QPainter::TextAntialiasing);
    
    painter.fillRect(QRect(0, 0, size.width(), size.height()), Qt::white);
    
    drawChart(painter, model, size);
    painter.end();

    return true;
}

void Exporter::drawChart(QPainter &painter, ChartModel *model, const QSize &size)
{
    const qreal margin = 60.0;
    const qreal titleHeight = 40.0;
    QRectF plotArea(margin, titleHeight + margin, 
                    static_cast<qreal>(size.width()) - 2.0 * margin, 
                    static_cast<qreal>(size.height()) - titleHeight - 2.0 * margin);

    QVariantList points = model->pointsAsVariantList();
    qreal minX = 0.0, maxX = 10.0, minY = 0.0, maxY = 10.0;

    if (!points.isEmpty()) {
        minX = points[0].toMap()["x"].toReal();
        maxX = points[0].toMap()["x"].toReal();
        minY = points[0].toMap()["y"].toReal();
        maxY = points[0].toMap()["y"].toReal();

        for (const QVariant &p : points) {
            QMap<QString, QVariant> point = p.toMap();
            qreal x = point["x"].toReal();
            qreal y = point["y"].toReal();
            minX = qMin(minX, x);
            maxX = qMax(maxX, x);
            minY = qMin(minY, y);
            maxY = qMax(maxY, y);
        }

        qreal xPadding = (maxX - minX) * 0.1;
        qreal yPadding = (maxY - minY) * 0.1;
        if (xPadding == 0) xPadding = 1.0;
        if (yPadding == 0) yPadding = 1.0;
        minX -= xPadding;
        maxX += xPadding;
        minY -= yPadding;
        maxY += yPadding;
    }

    painter.setPen(Qt::NoPen);
    painter.setBrush(Qt::white);
    painter.drawRect(0, 0, static_cast<qreal>(size.width()), static_cast<qreal>(size.height()));

    QFont titleFont("Arial", 16, QFont::Bold);
    painter.setFont(titleFont);
    painter.setPen(QPen(Qt::black));
    painter.drawText(QRectF(0, 0, static_cast<qreal>(size.width()), titleHeight), 
                     Qt::AlignCenter, model->title());

    drawAxes(painter, plotArea, model, minX, maxX, minY, maxY);
    drawPlot(painter, plotArea, model, minX, maxX, minY, maxY);
}

void Exporter::drawAxes(QPainter &painter, const QRectF &plotArea, ChartModel *model,
                        qreal minX, qreal maxX, qreal minY, qreal maxY)
{
    const int targetTickCount = 6;
    QVector<qreal> xTicks, yTicks;
    qreal niceMinX, niceMaxX, niceMinY, niceMaxY;

    calculateAxisTicks(minX, maxX, targetTickCount, xTicks, niceMinX, niceMaxX);
    calculateAxisTicks(minY, maxY, targetTickCount, yTicks, niceMinY, niceMaxY);

    QPen axisPen(Qt::black, 2);
    painter.setPen(axisPen);

    painter.drawLine(plotArea.bottomLeft(), plotArea.bottomRight());
    painter.drawLine(plotArea.bottomLeft(), plotArea.topLeft());

    QPen gridPen(QColor(220, 220, 220), 1, Qt::DashLine);
    painter.setPen(gridPen);

    QFont labelFont("Arial", 10);
    painter.setFont(labelFont);

    for (int i = 0; i < xTicks.size(); ++i) {
        qreal t = (xTicks[i] - niceMinX) / (niceMaxX - niceMinX);
        qreal x = plotArea.left() + t * plotArea.width();
        
        painter.setPen(gridPen);
        painter.drawLine(QPointF(x, plotArea.bottom()), QPointF(x, plotArea.top()));

        qreal value = xTicks[i];
        int decimals = (qAbs(value) >= 1000.0) ? 0 : 
                      (qAbs(value) >= 100.0) ? 1 : 
                      (qAbs(value) >= 1.0) ? 1 : 2;
        QString label = QString::number(value, 'f', decimals);
        
        painter.setPen(Qt::black);
        painter.drawText(QRectF(x - 30.0, plotArea.bottom() + 5.0, 60.0, 20.0),
                         Qt::AlignCenter, label);
    }

    for (int i = 0; i < yTicks.size(); ++i) {
        qreal t = (yTicks[i] - niceMinY) / (niceMaxY - niceMinY);
        qreal y = plotArea.bottom() - t * plotArea.height();
        
        painter.setPen(gridPen);
        painter.drawLine(QPointF(plotArea.left(), y), QPointF(plotArea.right(), y));

        qreal value = yTicks[i];
        int decimals = (qAbs(value) >= 1000.0) ? 0 : 
                      (qAbs(value) >= 100.0) ? 1 : 
                      (qAbs(value) >= 1.0) ? 1 : 2;
        QString label = QString::number(value, 'f', decimals);
        
        painter.setPen(Qt::black);
        painter.drawText(QRectF(plotArea.left() - 60.0, y - 10.0, 55.0, 20.0),
                         Qt::AlignRight | Qt::AlignVCenter, label);
    }

    QFont axisLabelFont("Arial", 11, QFont::Bold);
    painter.setFont(axisLabelFont);
    painter.setPen(Qt::black);
    
    QRectF xLabelRect(0, plotArea.bottom() + 25.0, 
                      plotArea.width() + 2.0 * 60.0, 20.0);
    painter.drawText(xLabelRect, Qt::AlignCenter, model->xAxisLabel());

    painter.save();
    painter.translate(15.0, plotArea.center().y());
    painter.rotate(-90.0);
    QRectF yLabelRect(-plotArea.height() / 2.0, -15.0, plotArea.height(), 20.0);
    painter.drawText(yLabelRect, Qt::AlignCenter, model->yAxisLabel());
    painter.restore();
}

void Exporter::drawPlot(QPainter &painter, const QRectF &plotArea, ChartModel *model,
                        qreal minX, qreal maxX, qreal minY, qreal maxY)
{
    QVariantList points = model->pointsAsVariantList();
    if (points.size() < 2)
        return;

    const int maxDrawPoints = 2000;
    QList<QPointF> scenePoints;
    
    if (points.size() <= maxDrawPoints) {
        for (const QVariant &p : points) {
            QMap<QString, QVariant> point = p.toMap();
            scenePoints.append(mapToScene(point["x"].toReal(), point["y"].toReal(),
                                           plotArea, minX, maxX, minY, maxY));
        }
    } else {
        double step = static_cast<double>(points.size() - 1) / (maxDrawPoints - 1);
        for (int i = 0; i < maxDrawPoints; ++i) {
            int idx = qMin(static_cast<int>(i * step), points.size() - 1);
            QMap<QString, QVariant> point = points[idx].toMap();
            scenePoints.append(mapToScene(point["x"].toReal(), point["y"].toReal(),
                                           plotArea, minX, maxX, minY, maxY));
        }
    }

    QPen linePen(model->lineColor(), 3);
    linePen.setJoinStyle(Qt::RoundJoin);
    linePen.setCapStyle(Qt::RoundCap);
    painter.setPen(linePen);
    painter.setBrush(Qt::NoBrush);
    
    for (int i = 1; i < scenePoints.size(); ++i) {
        painter.drawLine(scenePoints[i - 1], scenePoints[i]);
    }

    if (scenePoints.size() <= 200) {
        QBrush pointBrush(model->lineColor());
        QPen pointPen(Qt::white, 2);
        painter.setBrush(pointBrush);
        painter.setPen(pointPen);
        
        for (const QPointF &p : scenePoints) {
            painter.drawEllipse(p, 5.0, 5.0);
        }
    }
}

QPointF Exporter::mapToScene(qreal x, qreal y, const QRectF &plotArea,
                             qreal minX, qreal maxX, qreal minY, qreal maxY)
{
    qreal tX = (x - minX) / (maxX - minX);
    qreal tY = (y - minY) / (maxY - minY);
    return QPointF(
        plotArea.left() + tX * plotArea.width(),
        plotArea.bottom() - tY * plotArea.height()
    );
}
