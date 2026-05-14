#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QtQml>

#include "ChartModel.h"
#include "Exporter.h"
#include "LiveDataGenerator.h"
#include "plugin_interface.h"

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);

    qmlRegisterType<ChartModel>("ChartEditor", 1, 0, "ChartModel");
    qmlRegisterType<Exporter>("ChartEditor", 1, 0, "Exporter");
    qmlRegisterType<LiveDataGenerator>("ChartEditor", 1, 0, "LiveDataGenerator");

    qmlRegisterUncreatableMetaObject(
        staticQtMetaObject,
        "ChartEditor", 1, 0,
        "StaticQt",
        "Access to enums and flags"
    );

    QQmlApplicationEngine engine;
    engine.loadFromModule("ChartEditor", "ChartView");

    if (engine.rootObjects().isEmpty())
        return -1;

    return app.exec();
}
