#include "LiveDataGenerator.h"
#include <QDateTime>
#include <QtMath>

LiveDataGenerator::LiveDataGenerator(QObject *parent)
    : QObject(parent)
    , m_timer(new QTimer(this))
    , m_running(false)
    , m_intervalMs(100)
    , m_sensorType(SensorType::Temperature)
    , m_baseValue(25.0)
    , m_amplitude(5.0)
    , m_noiseLevel(0.5)
    , m_startTime(0)
    , m_sampleCount(0)
{
    connect(m_timer, &QTimer::timeout, this, &LiveDataGenerator::generateData);
    updateSensorDefaults();
}

LiveDataGenerator::~LiveDataGenerator()
{
    stop();
}

bool LiveDataGenerator::running() const
{
    return m_running;
}

int LiveDataGenerator::intervalMs() const
{
    return m_intervalMs;
}

SensorType LiveDataGenerator::sensorType() const
{
    return m_sensorType;
}

qreal LiveDataGenerator::baseValue() const
{
    return m_baseValue;
}

qreal LiveDataGenerator::amplitude() const
{
    return m_amplitude;
}

qreal LiveDataGenerator::noiseLevel() const
{
    return m_noiseLevel;
}

QString LiveDataGenerator::sensorName() const
{
    switch (m_sensorType) {
    case SensorType::Temperature:
        return "Temperature (°C)";
    case SensorType::Pressure:
        return "Pressure (kPa)";
    case SensorType::Humidity:
        return "Humidity (%)";
    case SensorType::Vibration:
        return "Vibration (mm/s)";
    case SensorType::Custom:
        return "Custom Sensor";
    default:
        return "Unknown";
    }
}

void LiveDataGenerator::setIntervalMs(int interval)
{
    if (m_intervalMs != interval && interval > 0) {
        m_intervalMs = interval;
        if (m_running) {
            m_timer->setInterval(m_intervalMs);
        }
        emit intervalMsChanged();
    }
}

void LiveDataGenerator::setSensorType(SensorType type)
{
    if (m_sensorType != type) {
        m_sensorType = type;
        updateSensorDefaults();
        emit sensorTypeChanged();
        emit sensorNameChanged();
    }
}

void LiveDataGenerator::setBaseValue(qreal value)
{
    if (!qFuzzyCompare(m_baseValue, value)) {
        m_baseValue = value;
        emit baseValueChanged();
    }
}

void LiveDataGenerator::setAmplitude(qreal value)
{
    if (!qFuzzyCompare(m_amplitude, value)) {
        m_amplitude = value;
        emit amplitudeChanged();
    }
}

void LiveDataGenerator::setNoiseLevel(qreal value)
{
    if (!qFuzzyCompare(m_noiseLevel, value)) {
        m_noiseLevel = qMax(0.0, value);
        emit noiseLevelChanged();
    }
}

void LiveDataGenerator::start()
{
    if (!m_running) {
        m_running = true;
        m_startTime = QDateTime::currentMSecsSinceEpoch();
        m_sampleCount = 0;
        m_timer->start(m_intervalMs);
        emit runningChanged();
    }
}

void LiveDataGenerator::stop()
{
    if (m_running) {
        m_running = false;
        m_timer->stop();
        emit runningChanged();
    }
}

void LiveDataGenerator::reset()
{
    m_sampleCount = 0;
    m_startTime = QDateTime::currentMSecsSinceEpoch();
}

void LiveDataGenerator::generateData()
{
    qreal currentTime = QDateTime::currentMSecsSinceEpoch();
    qreal timeElapsed = (currentTime - m_startTime) / 1000.0;
    
    qreal value = generateSensorValue(timeElapsed);
    qreal timestamp = timeElapsed;
    
    emit newData(timestamp, value);
    m_sampleCount++;
}

qreal LiveDataGenerator::generateSensorValue(qreal timeElapsed)
{
    qreal value = m_baseValue;
    qreal t = timeElapsed;
    
    switch (m_sensorType) {
    case SensorType::Temperature: {
        value += m_amplitude * qSin(2 * M_PI * t / 60.0);
        value += m_amplitude * 0.3 * qSin(2 * M_PI * t / 10.0);
        break;
    }
    case SensorType::Pressure: {
        qreal trend = m_amplitude * 0.01 * t;
        value += m_amplitude * 0.5 * qSin(2 * M_PI * t / 30.0);
        value += trend;
        break;
    }
    case SensorType::Humidity: {
        value += m_amplitude * qCos(2 * M_PI * t / 120.0);
        value += m_amplitude * 0.2 * qSin(2 * M_PI * t / 5.0);
        break;
    }
    case SensorType::Vibration: {
        value += m_amplitude * qSin(2 * M_PI * t / 2.0);
        value += m_amplitude * 0.5 * qSin(2 * M_PI * t / 0.5);
        value += m_amplitude * 0.25 * qSin(2 * M_PI * t / 0.1);
        break;
    }
    case SensorType::Custom: {
        value += m_amplitude * qSin(2 * M_PI * t / 10.0);
        break;
    }
    }
    
    value += randomNormal(0, m_noiseLevel);
    
    return value;
}

qreal LiveDataGenerator::randomNormal(qreal mean, qreal stddev)
{
    qreal u1 = 0, u2 = 0;
    while (u1 <= 0.0) {
        u1 = QRandomGenerator::global()->generateDouble();
        u2 = QRandomGenerator::global()->generateDouble();
    }
    qreal z0 = qSqrt(-2.0 * qLn(u1)) * qCos(2.0 * M_PI * u2);
    return mean + stddev * z0;
}

void LiveDataGenerator::updateSensorDefaults()
{
    switch (m_sensorType) {
    case SensorType::Temperature:
        m_baseValue = 25.0;
        m_amplitude = 5.0;
        m_noiseLevel = 0.3;
        break;
    case SensorType::Pressure:
        m_baseValue = 101.3;
        m_amplitude = 2.0;
        m_noiseLevel = 0.1;
        break;
    case SensorType::Humidity:
        m_baseValue = 50.0;
        m_amplitude = 20.0;
        m_noiseLevel = 1.0;
        break;
    case SensorType::Vibration:
        m_baseValue = 0.0;
        m_amplitude = 2.0;
        m_noiseLevel = 0.5;
        break;
    case SensorType::Custom:
        break;
    }
}
