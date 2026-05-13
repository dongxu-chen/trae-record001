#ifndef KINEMATICS_H
#define KINEMATICS_H

#include "joint.h"
#include <QVector>
#include <QMatrix4x4>
#include <QVector3D>
#include <QQuaternion>

struct Pose {
    QVector3D position;
    QQuaternion orientation;

    Pose()
        : position(0.0, 0.0, 0.0)
        , orientation(QQuaternion::fromAxisAndAngle(0.0, 0.0, 1.0, 0.0))
    {}

    Pose(const QVector3D& pos, const QQuaternion& orient)
        : position(pos)
        , orientation(orient)
    {}
};

class Kinematics {
public:
    explicit Kinematics(const QVector<Joint>& joints = {});

    void setJoints(const QVector<Joint>& joints);
    const QVector<Joint>& joints() const { return m_joints; }
    int numJoints() const { return m_joints.size(); }

    QVector<QMatrix4x4> forwardKinematics(const QVector<double>& jointValues);
    Pose computeEndEffectorPose(const QVector<double>& jointValues);
    QVector3D getJointPosition(const QVector<double>& jointValues, int jointIndex);
    QVector<Pose> getAllLinkPoses(const QVector<double>& jointValues);

    QVector<double> inverseKinematics(const Pose& targetPose,
                                      const QVector<double>& initialGuess,
                                      double tolerance = 1e-3,
                                      int maxIterations = 100);

    QVector<QVector<double>> jacobian(const QVector<double>& jointValues);

    QVector<double> clampJointValues(const QVector<double>& values) const;

    void setBaseTransform(const QMatrix4x4& transform) { m_baseTransform = transform; }
    QMatrix4x4 baseTransform() const { return m_baseTransform; }

private:
    QVector<Joint> m_joints;
    QMatrix4x4 m_baseTransform;

    double degToRad(double deg) const;
    double radToDeg(double rad) const;

    QVector<double> poseError(const Pose& current, const Pose& target);
    double norm(const QVector<double>& v) const;
};

#endif
