#include "trajectory.h"
#include <qmath.h>
#include <algorithm>

Trajectory::Trajectory(QObject* parent)
    : QObject(parent)
    , m_duration(3.0)
    , m_currentTime(0.0)
    , m_updateInterval(16)
    , m_method(InterpolationMethod::Quintic)
    , m_isRunning(false)
    , m_isJointSpace(true)
    , m_kinematics(nullptr)
{
    m_timer = new QTimer(this);
    connect(m_timer, &QTimer::timeout, this, &Trajectory::update);
}

void Trajectory::setJointSpaceTrajectory(const QVector<double>& start,
                                         const QVector<double>& end,
                                         double duration)
{
    m_startJointValues = start;
    m_endJointValues = end;
    m_currentJointValues = start;
    m_duration = qMax(0.01, duration);
    m_isJointSpace = true;
    m_kinematics = nullptr;
    m_currentTime = 0.0;
}

void Trajectory::setCartesianTrajectory(const Pose& startPose,
                                       const Pose& endPose,
                                       const QVector<double>& startJointValues,
                                       double duration,
                                       Kinematics* kinematics)
{
    m_startPose = startPose;
    m_endPose = endPose;
    m_startJointValues = startJointValues;
    m_currentJointValues = startJointValues;
    m_duration = qMax(0.01, duration);
    m_isJointSpace = false;
    m_kinematics = kinematics;
    m_currentTime = 0.0;
}

void Trajectory::start()
{
    if (m_isRunning) {
        return;
    }

    m_elapsedTimer.start();
    m_isRunning = true;
    m_timer->start(m_updateInterval);
}

void Trajectory::stop()
{
    if (m_isRunning) {
        m_isRunning = false;
        m_timer->stop();
    }
}

void Trajectory::reset()
{
    stop();
    m_currentTime = 0.0;
    m_currentJointValues = m_startJointValues;
    emit jointValuesChanged(m_currentJointValues);
    emit progressChanged(0);
}

void Trajectory::update()
{
    qint64 elapsedMs = m_elapsedTimer.restart();
    double deltaTime = elapsedMs / 1000.0;

    m_currentTime += deltaTime;

    if (m_currentTime >= m_duration) {
        m_currentTime = m_duration;
        m_isRunning = false;
        m_timer->stop();

        if (m_isJointSpace) {
            m_currentJointValues = m_endJointValues;
        } else if (m_kinematics) {
            m_currentJointValues = m_kinematics->inverseKinematics(
                m_endPose, m_currentJointValues, 1e-4, 100);
        }

        emit jointValuesChanged(m_currentJointValues);
        emit progressChanged(100);
        emit trajectoryFinished();
        return;
    }

    double t = m_currentTime / m_duration;
    t = std::max(0.0, std::min(1.0, t));

    if (m_isJointSpace) {
        m_currentJointValues = interpolateJointValues(t);
    } else if (m_kinematics) {
        Pose targetPose = interpolatePose(t);
        m_currentJointValues = m_kinematics->inverseKinematics(
            targetPose, m_currentJointValues, 1e-4, 100);
    }

    emit jointValuesChanged(m_currentJointValues);
    emit progressChanged(static_cast<int>(t * 100.0));
}

double Trajectory::interpolateLinear(double t)
{
    return t;
}

double Trajectory::interpolateCubic(double t)
{
    return 3.0 * t * t - 2.0 * t * t * t;
}

double Trajectory::interpolateQuintic(double t)
{
    return 10.0 * t * t * t - 15.0 * t * t * t * t + 6.0 * t * t * t * t * t;
}

QVector<double> Trajectory::interpolateJointValues(double t)
{
    double s;
    switch (m_method) {
    case InterpolationMethod::Linear:
        s = interpolateLinear(t);
        break;
    case InterpolationMethod::Cubic:
        s = interpolateCubic(t);
        break;
    case InterpolationMethod::Quintic:
    default:
        s = interpolateQuintic(t);
        break;
    }

    int n = qMin(m_startJointValues.size(), m_endJointValues.size());
    QVector<double> result(n);
    for (int i = 0; i < n; ++i) {
        result[i] = m_startJointValues[i] + s * (m_endJointValues[i] - m_startJointValues[i]);
    }

    return result;
}

Pose Trajectory::interpolatePose(double t)
{
    double s;
    switch (m_method) {
    case InterpolationMethod::Linear:
        s = interpolateLinear(t);
        break;
    case InterpolationMethod::Cubic:
        s = interpolateCubic(t);
        break;
    case InterpolationMethod::Quintic:
    default:
        s = interpolateQuintic(t);
        break;
    }

    QVector3D pos = slerpPosition(m_startPose.position, m_endPose.position, s);
    QQuaternion orient = slerpQuaternion(m_startPose.orientation, m_endPose.orientation, s);

    return Pose(pos, orient);
}

QVector3D Trajectory::slerpPosition(const QVector3D& start, const QVector3D& end, double t)
{
    return start + t * (end - start);
}

QQuaternion Trajectory::slerpQuaternion(const QQuaternion& q1, const QQuaternion& q2, double t)
{
    QQuaternion qa = q1.normalized();
    QQuaternion qb = q2.normalized();

    double cosHalfTheta = qa.x() * qb.x() + qa.y() * qb.y() + qa.z() * qb.z() + qa.scalar() * qb.scalar();

    if (cosHalfTheta < 0) {
        qb = QQuaternion(-qb.scalar(), -qb.x(), -qb.y(), -qb.z());
        cosHalfTheta = -cosHalfTheta;
    }

    if (cosHalfTheta >= 1.0) {
        return qa;
    }

    double sinHalfTheta = qSqrt(1.0 - cosHalfTheta * cosHalfTheta);

    if (qAbs(sinHalfTheta) < 0.001) {
        double w = 0.5 * (qa.scalar() + qb.scalar());
        double x = 0.5 * (qa.x() + qb.x());
        double y = 0.5 * (qa.y() + qb.y());
        double z = 0.5 * (qa.z() + qb.z());
        return QQuaternion(w, x, y, z);
    }

    double halfTheta = qAtan2(sinHalfTheta, cosHalfTheta);
    double ratioA = qSin((1.0 - t) * halfTheta) / sinHalfTheta;
    double ratioB = qSin(t * halfTheta) / sinHalfTheta;

    double w = qa.scalar() * ratioA + qb.scalar() * ratioB;
    double x = qa.x() * ratioA + qb.x() * ratioB;
    double y = qa.y() * ratioA + qb.y() * ratioB;
    double z = qa.z() * ratioA + qb.z() * ratioB;

    return QQuaternion(w, x, y, z).normalized();
}
