#ifndef JOINT_H
#define JOINT_H

#include <QVector3D>
#include <QMatrix4x4>
#include <QQuaternion>

class Joint {
public:
    enum class Type { Revolute, Prismatic };

    Joint(double a, double alpha, double d, double theta,
          Type type = Type::Revolute,
          double lowerLimit = -180.0,
          double upperLimit = 180.0);

    double a() const { return m_a; }
    double alpha() const { return m_alpha; }
    double d() const { return m_d; }
    double theta() const { return m_theta; }

    void setA(double a) { m_a = a; }
    void setAlpha(double alpha) { m_alpha = alpha; }
    void setD(double d) { m_d = d; }
    void setTheta(double theta) { m_theta = theta; }

    Type type() const { return m_type; }
    void setType(Type type) { m_type = type; }

    double jointValue() const;
    void setJointValue(double value);

    double lowerLimit() const { return m_lowerLimit; }
    double upperLimit() const { return m_upperLimit; }
    void setLimits(double lower, double upper);

    QMatrix4x4 dhMatrix() const;
    QMatrix4x4 transformMatrix(double jointValue) const;

    double clampValue(double value) const;
    bool isWithinLimits(double value) const;

private:
    double m_a;
    double m_alpha;
    double m_d;
    double m_theta;
    Type m_type;
    double m_lowerLimit;
    double m_upperLimit;

    double degToRad(double deg) const;
    double radToDeg(double rad) const;
};

#endif
