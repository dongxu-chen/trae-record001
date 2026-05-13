#include "kinematics.h"
#include <qmath.h>
#include <algorithm>
#include <limits>

namespace {

bool choleskyDecompose(QVector<QVector<double>>& A, int n)
{
    for (int j = 0; j < n; ++j) {
        double d = 0.0;
        for (int k = 0; k < j; ++k) {
            double s = 0.0;
            for (int i = 0; i < k; ++i) {
                s += A[k][i] * A[j][i];
            }
            A[j][k] = (A[j][k] - s) / A[k][k];
            d += A[j][k] * A[j][k];
        }
        d = A[j][j] - d;
        if (d <= 0.0) {
            return false;
        }
        A[j][j] = qSqrt(d);
    }
    return true;
}

QVector<double> choleskySolve(QVector<QVector<double>>& L, const QVector<double>& b, int n)
{
    QVector<double> y(n);
    for (int i = 0; i < n; ++i) {
        double sum = b[i];
        for (int k = 0; k < i; ++k) {
            sum -= L[i][k] * y[k];
        }
        y[i] = sum / L[i][i];
    }

    QVector<double> x(n);
    for (int i = n - 1; i >= 0; --i) {
        double sum = y[i];
        for (int k = i + 1; k < n; ++k) {
            sum -= L[k][i] * x[k];
        }
        x[i] = sum / L[i][i];
    }

    return x;
}

}

Kinematics::Kinematics(const QVector<Joint>& joints)
    : m_joints(joints)
{
    m_baseTransform.setToIdentity();
}

void Kinematics::setJoints(const QVector<Joint>& joints)
{
    m_joints = joints;
}

QVector<QMatrix4x4> Kinematics::forwardKinematics(const QVector<double>& jointValues)
{
    QVector<QMatrix4x4> transforms;
    QMatrix4x4 currentTransform = m_baseTransform;
    transforms.append(currentTransform);

    int n = qMin(m_joints.size(), jointValues.size());
    for (int i = 0; i < n; ++i) {
        QMatrix4x4 T = m_joints[i].transformMatrix(jointValues[i]);
        currentTransform = currentTransform * T;
        transforms.append(currentTransform);
    }

    return transforms;
}

Pose Kinematics::computeEndEffectorPose(const QVector<double>& jointValues)
{
    QVector<QMatrix4x4> transforms = forwardKinematics(jointValues);
    if (transforms.isEmpty()) {
        return Pose();
    }

    QMatrix4x4 T = transforms.last();
    QVector3D position(T(0, 3), T(1, 3), T(2, 3));

    QVector3D xAxis(T(0, 0), T(1, 0), T(2, 0));
    QVector3D yAxis(T(0, 1), T(1, 1), T(2, 1));
    QVector3D zAxis(T(0, 2), T(1, 2), T(2, 2));

    QMatrix3x3 rotMatrix;
    rotMatrix(0, 0) = xAxis.x(); rotMatrix(0, 1) = yAxis.x(); rotMatrix(0, 2) = zAxis.x();
    rotMatrix(1, 0) = xAxis.y(); rotMatrix(1, 1) = yAxis.y(); rotMatrix(1, 2) = zAxis.y();
    rotMatrix(2, 0) = xAxis.z(); rotMatrix(2, 1) = yAxis.z(); rotMatrix(2, 2) = zAxis.z();

    QQuaternion orientation = QQuaternion::fromRotationMatrix(rotMatrix);

    return Pose(position, orientation.normalized());
}

QVector3D Kinematics::getJointPosition(const QVector<double>& jointValues, int jointIndex)
{
    QVector<QMatrix4x4> transforms = forwardKinematics(jointValues);
    if (jointIndex < 0 || jointIndex >= transforms.size()) {
        return QVector3D(0, 0, 0);
    }

    QMatrix4x4 T = transforms[jointIndex];
    return QVector3D(T(0, 3), T(1, 3), T(2, 3));
}

QVector<Pose> Kinematics::getAllLinkPoses(const QVector<double>& jointValues)
{
    QVector<Pose> poses;
    QVector<QMatrix4x4> transforms = forwardKinematics(jointValues);

    for (const QMatrix4x4& T : transforms) {
        QVector3D position(T(0, 3), T(1, 3), T(2, 3));

        QMatrix3x3 rotMatrix;
        rotMatrix(0, 0) = T(0, 0); rotMatrix(0, 1) = T(0, 1); rotMatrix(0, 2) = T(0, 2);
        rotMatrix(1, 0) = T(1, 0); rotMatrix(1, 1) = T(1, 1); rotMatrix(1, 2) = T(1, 2);
        rotMatrix(2, 0) = T(2, 0); rotMatrix(2, 1) = T(2, 1); rotMatrix(2, 2) = T(2, 2);

        QQuaternion orientation = QQuaternion::fromRotationMatrix(rotMatrix);
        poses.append(Pose(position, orientation.normalized()));
    }

    return poses;
}

QVector<double> Kinematics::inverseKinematics(const Pose& targetPose,
                                              const QVector<double>& initialGuess,
                                              double tolerance,
                                              int maxIterations)
{
    QVector<double> currentQ = clampJointValues(initialGuess);
    int n = qMin(m_joints.size(), currentQ.size());
    if (n <= 0) {
        return currentQ;
    }

    double prevErrorNorm = std::numeric_limits<double>::max();
    double lambda = 1e-3;
    const double alpha = 1.0;
    const double beta = 0.5;

    for (int iter = 0; iter < maxIterations; ++iter) {
        Pose currentPose = computeEndEffectorPose(currentQ);
        QVector<double> error = poseError(currentPose, targetPose);
        double errorNorm = norm(error);

        if (errorNorm < tolerance) {
            break;
        }

        if (errorNorm >= prevErrorNorm) {
            lambda = qMin(lambda * 10.0, 1e3);
        } else {
            lambda = qMax(lambda * 0.5, 1e-6);
        }
        prevErrorNorm = errorNorm;

        QVector<QVector<double>> J = jacobian(currentQ);
        if (J.isEmpty() || J[0].isEmpty()) {
            break;
        }

        int rows = J.size();
        int cols = J[0].size();
        cols = qMin(cols, n);

        QVector<QVector<double>> Jt(cols, QVector<double>(rows, 0.0));
        for (int i = 0; i < rows; ++i) {
            for (int j = 0; j < cols; ++j) {
                Jt[j][i] = J[i][j];
            }
        }

        QVector<QVector<double>> A(cols, QVector<double>(cols, 0.0));
        for (int i = 0; i < cols; ++i) {
            for (int j = 0; j < cols; ++j) {
                double sum = 0.0;
                for (int k = 0; k < rows; ++k) {
                    sum += Jt[i][k] * J[k][j];
                }
                A[i][j] = sum;
            }
            A[i][i] += lambda;
        }

        QVector<double> g(cols, 0.0);
        for (int i = 0; i < cols; ++i) {
            double sum = 0.0;
            for (int j = 0; j < rows; ++j) {
                sum += Jt[i][j] * error[j];
            }
            g[i] = sum;
        }

        QVector<QVector<double>> L = A;
        bool decomposed = choleskyDecompose(L, cols);
        QVector<double> deltaQ(cols, 0.0);

        if (decomposed) {
            deltaQ = choleskySolve(L, g, cols);
        } else {
            for (int i = 0; i < cols; ++i) {
                deltaQ[i] = g[i] / (A[i][i] + 1e-6);
            }
        }

        double step = alpha;
        int lineSearchIter = 0;
        const int maxLineSearch = 10;

        while (lineSearchIter < maxLineSearch) {
            QVector<double> candidateQ(n);
            for (int i = 0; i < n; ++i) {
                candidateQ[i] = m_joints[i].clampValue(currentQ[i] + step * deltaQ[i]);
            }

            Pose candidatePose = computeEndEffectorPose(candidateQ);
            QVector<double> candidateError = poseError(candidatePose, targetPose);
            double candidateNorm = norm(candidateError);

            double suffDecrease = 0.0;
            for (int i = 0; i < cols; ++i) {
                suffDecrease += g[i] * deltaQ[i];
            }
            suffDecrease = 1e-4 * step * suffDecrease;

            if (candidateNorm <= errorNorm + suffDecrease) {
                currentQ = candidateQ;
                break;
            }

            step *= beta;
            lineSearchIter++;
        }

        if (lineSearchIter >= maxLineSearch) {
            for (int i = 0; i < n; ++i) {
                currentQ[i] = m_joints[i].clampValue(currentQ[i] + step * deltaQ[i]);
            }
        }
    }

    return currentQ;
}

QVector<QVector<double>> Kinematics::jacobian(const QVector<double>& jointValues)
{
    int n = qMin(m_joints.size(), jointValues.size());
    QVector<QVector<double>> J(6, QVector<double>(n, 0.0));

    QVector<QMatrix4x4> transforms = forwardKinematics(jointValues);
    if (transforms.size() < 2) {
        return J;
    }

    QMatrix4x4 Te = transforms.last();
    QVector3D pe(Te(0, 3), Te(1, 3), Te(2, 3));

    for (int i = 0; i < n; ++i) {
        if (i >= transforms.size()) break;

        QMatrix4x4 Ti = transforms[i];
        QVector3D pi(Ti(0, 3), Ti(1, 3), Ti(2, 3));
        QVector3D zi(Ti(0, 2), Ti(1, 2), Ti(2, 2));

        QVector3D r = pe - pi;

        if (m_joints[i].type() == Joint::Type::Revolute) {
            QVector3D v = QVector3D::crossProduct(zi, r);
            J[0][i] = v.x();
            J[1][i] = v.y();
            J[2][i] = v.z();
            J[3][i] = zi.x();
            J[4][i] = zi.y();
            J[5][i] = zi.z();
        } else {
            J[0][i] = zi.x();
            J[1][i] = zi.y();
            J[2][i] = zi.z();
            J[3][i] = 0.0;
            J[4][i] = 0.0;
            J[5][i] = 0.0;
        }
    }

    return J;
}

QVector<double> Kinematics::clampJointValues(const QVector<double>& values) const
{
    QVector<double> result = values;
    int n = qMin(m_joints.size(), result.size());
    for (int i = 0; i < n; ++i) {
        result[i] = m_joints[i].clampValue(result[i]);
    }
    return result;
}

QVector<double> Kinematics::poseError(const Pose& current, const Pose& target)
{
    QVector<double> error(6, 0.0);

    QVector3D posError = target.position - current.position;
    error[0] = posError.x();
    error[1] = posError.y();
    error[2] = posError.z();

    QQuaternion qError = target.orientation * current.orientation.conjugated();
    qError.normalize();

    if (qError.scalar() < 0) {
        qError = QQuaternion(-qError.scalar(), -qError.x(), -qError.y(), -qError.z());
    }

    double sinHalf = qSqrt(qError.x() * qError.x() + qError.y() * qError.y() + qError.z() * qError.z());
    double cosHalf = qError.scalar();
    double halfAngle = qAtan2(sinHalf, cosHalf);

    if (sinHalf > 1e-10) {
        double factor = 2.0 * halfAngle / sinHalf;
        error[3] = factor * qError.x();
        error[4] = factor * qError.y();
        error[5] = factor * qError.z();
    } else {
        error[3] = 2.0 * qError.x();
        error[4] = 2.0 * qError.y();
        error[5] = 2.0 * qError.z();
    }

    return error;
}

double Kinematics::norm(const QVector<double>& v) const
{
    double sum = 0.0;
    for (double d : v) {
        sum += d * d;
    }
    return qSqrt(sum);
}

double Kinematics::degToRad(double deg) const
{
    return deg * M_PI / 180.0;
}

double Kinematics::radToDeg(double rad) const
{
    return rad * 180.0 / M_PI;
}
