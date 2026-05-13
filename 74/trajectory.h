#ifndef TRAJECTORY_H
#define TRAJECTORY_H

#include "kinematics.h"
#include <QObject>
#include <QTimer>
#include <QVector>
#include <QTimer>
#include <QElapsedTimer>
#include <QTimer>

class Trajectory : public QObject {
    Q_OBJECT
public:
    enum class InterpolationMethod { Linear, Cubic, Quintic };

    explicit Trajectory(QObject* parent = nullptr);

    void setJointSpaceTrajectory(const QVector<double>& start,
                                 const QVector<double>& end,
                                 double duration);

    void setCartesianTrajectory(const Pose& startPose,
                               const Pose& endPose,
                               const QVector<double>& startJointValues,
                               double duration,
                               Kinematics* kinematics);

    void start();
    void stop();
    void reset();

    void setDuration(double seconds) { m_duration = seconds; }
    double duration() const { return m_duration; }

    void setInterpolationMethod(InterpolationMethod method) { m_method = method; }
    InterpolationMethod interpolationMethod() const { return m_method; }

    void setUpdateInterval(int ms) { m_updateInterval = ms; }
    int updateInterval() const { return m_updateInterval; }

    bool isRunning() const { return m_isRunning; }

    QVector<double> currentJointValues() const { return m_currentJointValues; }
    double progress() const { return m_currentTime / m_duration; }

signals:
    void jointValuesChanged(const QVector<double>& jointValues);
    void progressChanged(int progress);
    void trajectoryFinished();

private slots:
    void update();

private:
    QVector<double> m_startJointValues;
    QVector<double> m_endJointValues;
    QVector<double> m_currentJointValues;

    Pose m_startPose;
    Pose m_endPose;

    double m_duration;
    double m_currentTime;
    int m_updateInterval;
    InterpolationMethod m_method;

    QTimer* m_timer;
    QElapsedTimer m_elapsedTimer;
    bool m_isRunning;
    bool m_isJointSpace;

    Kinematics* m_kinematics;

    double interpolateLinear(double t);
    double interpolateCubic(double t);
    double interpolateQuintic(double t);

    QVector<double> interpolateJointValues(double t);
    Pose interpolatePose(double t);

    QVector3D slerpPosition(const QVector3D& start, const QVector3D& end, double t);
    QQuaternion slerpQuaternion(const QQuaternion& q1, const QQuaternion& q2, double t);
};

#endif
