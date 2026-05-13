#include "joint.h"
#include <qmath.h>
#include <algorithm>

Joint::Joint(double a, double alpha, double d, double theta,
             Type type, double lowerLimit, double upperLimit)
    : m_a(a)
    , m_alpha(alpha)
    , m_d(d)
    , m_theta(theta)
    , m_type(type)
    , m_lowerLimit(lowerLimit)
    , m_upperLimit(upperLimit)
{
}

double Joint::jointValue() const
{
    if (m_type == Type::Revolute) {
        return m_theta;
    } else {
        return m_d;
    }
}

void Joint::setJointValue(double value)
{
    if (m_type == Type::Revolute) {
        m_theta = clampValue(value);
    } else {
        m_d = clampValue(value);
    }
}

void Joint::setLimits(double lower, double upper)
{
    m_lowerLimit = lower;
    m_upperLimit = upper;
}

QMatrix4x4 Joint::dhMatrix() const
{
    double thetaRad = degToRad(m_theta);
    double alphaRad = degToRad(m_alpha);
    double ct = qCos(thetaRad);
    double st = qSin(thetaRad);
    double ca = qCos(alphaRad);
    double sa = qSin(alphaRad);

    QMatrix4x4 matrix;
    matrix.setToIdentity();
    matrix(0, 0) = ct;
    matrix(0, 1) = -st * ca;
    matrix(0, 2) = st * sa;
    matrix(0, 3) = m_a * ct;
    matrix(1, 0) = st;
    matrix(1, 1) = ct * ca;
    matrix(1, 2) = -ct * sa;
    matrix(1, 3) = m_a * st;
    matrix(2, 0) = 0.0;
    matrix(2, 1) = sa;
    matrix(2, 2) = ca;
    matrix(2, 3) = m_d;
    matrix(3, 0) = 0.0;
    matrix(3, 1) = 0.0;
    matrix(3, 2) = 0.0;
    matrix(3, 3) = 1.0;

    return matrix;
}

QMatrix4x4 Joint::transformMatrix(double jointValue) const
{
    double theta = m_theta;
    double d = m_d;

    if (m_type == Type::Revolute) {
        theta = clampValue(jointValue);
    } else {
        d = clampValue(jointValue);
    }

    double thetaRad = degToRad(theta);
    double alphaRad = degToRad(m_alpha);
    double ct = qCos(thetaRad);
    double st = qSin(thetaRad);
    double ca = qCos(alphaRad);
    double sa = qSin(alphaRad);

    QMatrix4x4 matrix;
    matrix.setToIdentity();
    matrix(0, 0) = ct;
    matrix(0, 1) = -st * ca;
    matrix(0, 2) = st * sa;
    matrix(0, 3) = m_a * ct;
    matrix(1, 0) = st;
    matrix(1, 1) = ct * ca;
    matrix(1, 2) = -ct * sa;
    matrix(1, 3) = m_a * st;
    matrix(2, 0) = 0.0;
    matrix(2, 1) = sa;
    matrix(2, 2) = ca;
    matrix(2, 3) = d;
    matrix(3, 0) = 0.0;
    matrix(3, 1) = 0.0;
    matrix(3, 2) = 0.0;
    matrix(3, 3) = 1.0;

    return matrix;
}

double Joint::clampValue(double value) const
{
    return std::max(m_lowerLimit, std::min(m_upperLimit, value));
}

bool Joint::isWithinLimits(double value) const
{
    return value >= m_lowerLimit && value <= m_upperLimit;
}

double Joint::degToRad(double deg) const
{
    return deg * M_PI / 180.0;
}

double Joint::radToDeg(double rad) const
{
    return rad * 180.0 / M_PI;
}
