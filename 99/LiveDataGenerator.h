#ifndef LIVEDATAGENERATOR_H
#define LIVEDATAGENERATOR_H

#include <QObject>
#include <QTimer>
#include <QRandomGenerator>
#include <QTime>

enum class SensorType {
    Temperature,
    Pressure,
    Humidity,
    Vibration,
    Custom
};

class LiveDataGenerator : public QObject
{
    Q_OBJECT
    Q_PROPERTY(bool running READ running NOTIFY runningChanged)
    Q_PROPERTY(int intervalMs READ intervalMs WRITE setIntervalMs NOTIFY intervalMsChanged)
    Q_PROPERTY(SensorType sensorType READ sensorType WRITE setSensorType NOTIFY sensorTypeChanged)
    Q_PROPERTY(qreal baseValue READ baseValue WRITE setBaseValue NOTIFY baseValueChanged)
    Q_PROPERTY(qreal amplitude READ amplitude WRITE setAmplitude NOTIFY amplitudeChanged)
    Q_PROPERTY(qreal noiseLevel READ noiseLevel WRITE setNoiseLevel NOTIFY noiseLevelChanged)
    Q_PROPERTY(QString sensorName READ sensorName NOTIFY sensorNameChanged)

public:
    explicit LiveDataGenerator(QObject *parent = nullptr);
    ~LiveDataGenerator();

    bool running() const;
    int intervalMs() const;
    SensorType sensorType() const;
    qreal baseValue() const;
    qreal amplitude() const;
    qreal noiseLevel() const;
    QString sensorName() const;

    Q_INVOKABLE void setIntervalMs(int interval);
    Q_INVOKABLE void setSensorType(SensorType type);
    Q_INVOKABLE void setBaseValue(qreal value);
    Q_INVOKABLE void setAmplitude(qreal value);
    Q_INVOKABLE void setNoiseLevel(qreal value);

    Q_INVOKABLE void start();
    Q_INVOKABLE void stop();
    Q_INVOKABLE void reset();

signals:
    void newData(qreal timestamp, qreal value);
    void runningChanged();
    void intervalMsChanged();
    void sensorTypeChanged();
    void baseValueChanged();
    void amplitudeChanged();
    void noiseLevelChanged();
    void sensorNameChanged();

private slots:
    void generateData();

private:
    QTimer *m_timer;
    bool m_running;
    int m_intervalMs;
    SensorType m_sensorType;
    qreal m_baseValue;
    qreal m_amplitude;
    qreal m_noiseLevel;
    qreal m_startTime;
    int m_sampleCount;

    qreal generateSensorValue(qreal timeElapsed);
    qreal randomNormal(qreal mean, qreal stddev);
    void updateSensorDefaults();
};

#endif // LIVEDATAGENERATOR_H
