#include "collision_checker.h"
#include <qmath.h>
#include <algorithm>
#include <limits>

CollisionChecker::CollisionChecker()
{
}

void CollisionChecker::setRobotLinks(const QVector<Joint>& joints,
                                     const QVector<double>& linkLengths)
{
    m_linkGeometries.clear();
    m_linkLengths = linkLengths;

    if (m_linkLengths.isEmpty()) {
        for (int i = 0; i < joints.size(); ++i) {
            m_linkLengths.append(1.0);
        }
    }

    for (int i = 0; i < joints.size(); ++i) {
        CollisionGeometry geom;
        geom.type = CollisionGeometry::Type::Capsule;
        geom.linkIndex = i;
        geom.radius = 0.18;
        geom.height = m_linkLengths[i];
        m_linkGeometries.append(geom);
    }

    generateDefaultSelfCollisionPairs(joints.size());
}

void CollisionChecker::addObstacle(const CollisionGeometry& obstacle)
{
    m_obstacles.append(obstacle);
}

void CollisionChecker::clearObstacles()
{
    m_obstacles.clear();
}

bool CollisionChecker::checkSelfCollision(const QVector<double>& jointValues) const
{
    Q_UNUSED(jointValues);

    for (const auto& pair : m_selfCollisionPairs) {
        int i = pair.first;
        int j = pair.second;

        if (i < 0 || i >= m_linkGeometries.size() ||
            j < 0 || j >= m_linkGeometries.size()) {
            continue;
        }

        const CollisionGeometry& g1 = m_linkGeometries[i];
        const CollisionGeometry& g2 = m_linkGeometries[j];

        bool collision = false;
        if (g1.type == CollisionGeometry::Type::Sphere &&
            g2.type == CollisionGeometry::Type::Sphere) {
            collision = checkSphereSphere(g1, g2);
        } else if (g1.type == CollisionGeometry::Type::Sphere &&
                   g2.type == CollisionGeometry::Type::Capsule) {
            collision = checkSphereCylinder(g1, g2);
        } else if (g1.type == CollisionGeometry::Type::Capsule &&
                   g2.type == CollisionGeometry::Type::Sphere) {
            collision = checkSphereCylinder(g2, g1);
        } else if (g1.type == CollisionGeometry::Type::Capsule &&
                   g2.type == CollisionGeometry::Type::Capsule) {
            collision = checkCylinderCylinder(g1, g2);
        }

        if (collision) {
            return true;
        }
    }

    return false;
}

bool CollisionChecker::checkEnvironmentCollision(const QVector<double>& jointValues,
                                                  Kinematics* kinematics) const
{
    if (!kinematics || m_obstacles.isEmpty()) {
        return false;
    }

    QVector<CollisionGeometry> linkPoses = getLinkGeometriesAtPose(jointValues, kinematics);

    for (const CollisionGeometry& linkGeom : linkPoses) {
        for (const CollisionGeometry& obs : m_obstacles) {
            bool collision = false;

            if (linkGeom.type == CollisionGeometry::Type::Sphere &&
                obs.type == CollisionGeometry::Type::Sphere) {
                collision = checkSphereSphere(linkGeom, obs);
            } else if (linkGeom.type == CollisionGeometry::Type::Sphere &&
                       obs.type == CollisionGeometry::Type::Box) {
                collision = checkSphereBox(linkGeom, obs);
            } else if (linkGeom.type == CollisionGeometry::Type::Capsule &&
                       obs.type == CollisionGeometry::Type::Box) {
                CollisionGeometry midSphere = linkGeom;
                midSphere.type = CollisionGeometry::Type::Sphere;
                midSphere.radius = linkGeom.radius;
                collision = checkSphereBox(midSphere, obs);
            } else if (linkGeom.type == CollisionGeometry::Type::Capsule &&
                       obs.type == CollisionGeometry::Type::Sphere) {
                collision = checkSphereCylinder(obs, linkGeom);
            } else if (linkGeom.type == CollisionGeometry::Type::Sphere &&
                       obs.type == CollisionGeometry::Type::Capsule) {
                collision = checkSphereCylinder(linkGeom, obs);
            }

            if (collision) {
                return true;
            }
        }
    }

    return false;
}

bool CollisionChecker::isColliding(const QVector<double>& jointValues,
                                    Kinematics* kinematics) const
{
    if (checkSelfCollision(jointValues)) {
        return true;
    }
    if (checkEnvironmentCollision(jointValues, kinematics)) {
        return true;
    }
    return false;
}

double CollisionChecker::minDistanceToObstacles(const QVector<double>& jointValues,
                                                 Kinematics* kinematics) const
{
    if (!kinematics || m_obstacles.isEmpty()) {
        return std::numeric_limits<double>::max();
    }

    QVector<CollisionGeometry> linkPoses = getLinkGeometriesAtPose(jointValues, kinematics);
    double minDist = std::numeric_limits<double>::max();

    for (const CollisionGeometry& linkGeom : linkPoses) {
        for (const CollisionGeometry& obs : m_obstacles) {
            double dist = std::numeric_limits<double>::max();

            if (linkGeom.type == CollisionGeometry::Type::Sphere &&
                obs.type == CollisionGeometry::Type::Sphere) {
                dist = distanceSphereSphere(linkGeom, obs);
            }

            if (dist < minDist) {
                minDist = dist;
            }
        }
    }

    return minDist;
}

bool CollisionChecker::checkMotionCollision(const QVector<double>& start,
                                             const QVector<double>& end,
                                             Kinematics* kinematics,
                                             int steps) const
{
    if (start.size() != end.size()) {
        return true;
    }

    for (int step = 0; step <= steps; ++step) {
        double t = static_cast<double>(step) / steps;
        QVector<double> interp(start.size());
        for (int i = 0; i < start.size(); ++i) {
            interp[i] = start[i] + t * (end[i] - start[i]);
        }

        if (isColliding(interp, kinematics)) {
            return true;
        }
    }

    return false;
}

void CollisionChecker::setSelfCollisionPairs(const QVector<QPair<int, int>>& pairs)
{
    m_selfCollisionPairs = pairs;
}

bool CollisionChecker::checkSphereSphere(const CollisionGeometry& s1,
                                          const CollisionGeometry& s2) const
{
    QVector3D diff = s1.position - s2.position;
    double dist = diff.length();
    return dist < (s1.radius + s2.radius) * 0.95;
}

bool CollisionChecker::checkSphereCylinder(const CollisionGeometry& sphere,
                                            const CollisionGeometry& cyl) const
{
    QVector3D cylAxis = cyl.orientation.rotatedVector(QVector3D(0, 1, 0));
    QVector3D top = cyl.position + cylAxis * (cyl.height / 2.0);
    QVector3D bottom = cyl.position - cylAxis * (cyl.height / 2.0);

    QVector3D closest = closestPointOnSegment(sphere.position, bottom, top);
    double dist = (sphere.position - closest).length();

    return dist < (sphere.radius + cyl.radius) * 0.95;
}

bool CollisionChecker::checkSphereBox(const CollisionGeometry& sphere,
                                       const CollisionGeometry& box) const
{
    QVector3D relPos = box.orientation.conjugated().rotatedVector(sphere.position - box.position);

    double halfX = box.size.x() / 2.0;
    double halfY = box.size.y() / 2.0;
    double halfZ = box.size.z() / 2.0;

    QVector3D closest;
    closest.setX(std::max(-halfX, std::min(halfX, relPos.x())));
    closest.setY(std::max(-halfY, std::min(halfY, relPos.y())));
    closest.setZ(std::max(-halfZ, std::min(halfZ, relPos.z())));

    double dist = (relPos - closest).length();
    return dist < sphere.radius * 0.95;
}

bool CollisionChecker::checkCylinderCylinder(const CollisionGeometry& c1,
                                              const CollisionGeometry& c2) const
{
    QVector3D axis1 = c1.orientation.rotatedVector(QVector3D(0, 1, 0));
    QVector3D axis2 = c2.orientation.rotatedVector(QVector3D(0, 1, 0));

    QVector3D p1 = c1.position;
    QVector3D p2 = c2.position;

    QVector3D d = p2 - p1;
    double a = QVector3D::dotProduct(axis1, axis1);
    double b = QVector3D::dotProduct(axis1, axis2);
    double c = QVector3D::dotProduct(axis2, axis2);
    double e = QVector3D::dotProduct(d, axis1);
    double f = QVector3D::dotProduct(d, axis2);

    double denom = a * c - b * b;
    double s, t;

    if (qAbs(denom) > 1e-10) {
        s = (b * f - c * e) / denom;
        t = (a * f - b * e) / denom;
    } else {
        s = 0.0;
        t = 0.0;
    }

    s = std::max(-c1.height / 2.0, std::min(c1.height / 2.0, s));
    t = std::max(-c2.height / 2.0, std::min(c2.height / 2.0, t));

    QVector3D closest1 = p1 + s * axis1;
    QVector3D closest2 = p2 + t * axis2;

    double dist = (closest1 - closest2).length();
    return dist < (c1.radius + c2.radius) * 0.95;
}

double CollisionChecker::distanceSphereSphere(const CollisionGeometry& s1,
                                               const CollisionGeometry& s2) const
{
    QVector3D diff = s1.position - s2.position;
    double centerDist = diff.length();
    return centerDist - s1.radius - s2.radius;
}

QVector<CollisionGeometry> CollisionChecker::getLinkGeometriesAtPose(
    const QVector<double>& jointValues,
    Kinematics* kinematics) const
{
    QVector<CollisionGeometry> result;

    if (!kinematics) {
        return result;
    }

    QVector<Pose> poses = kinematics->getAllLinkPoses(jointValues);

    for (int i = 0; i < m_linkGeometries.size() && i < poses.size() - 1; ++i) {
        const Pose& startPose = poses[i];
        const Pose& endPose = poses[i + 1];

        CollisionGeometry geom = m_linkGeometries[i];
        geom.position = (startPose.position + endPose.position) * 0.5;

        QVector3D linkAxis = endPose.position - startPose.position;
        if (linkAxis.length() > 1e-6) {
            linkAxis.normalize();
            QVector3D up(0, 1, 0);
            double dot = QVector3D::dotProduct(up, linkAxis);
            dot = std::max(-1.0, std::min(1.0, dot));

            if (qAbs(1.0 - dot) < 1e-6) {
                geom.orientation = QQuaternion();
            } else if (qAbs(-1.0 - dot) < 1e-6) {
                geom.orientation = QQuaternion::fromAxisAndAngle(QVector3D(1, 0, 0), 180.0);
            } else {
                QVector3D axis = QVector3D::crossProduct(up, linkAxis);
                axis.normalize();
                double angle = qRadiansToDegrees(qAcos(dot));
                geom.orientation = QQuaternion::fromAxisAndAngle(axis, angle);
            }
        }

        result.append(geom);
    }

    return result;
}

QVector3D CollisionChecker::closestPointOnSegment(const QVector3D& p,
                                                  const QVector3D& a,
                                                  const QVector3D& b) const
{
    QVector3D ab = b - a;
    double t = QVector3D::dotProduct(p - a, ab);

    if (t <= 0.0) {
        return a;
    }

    double abLen2 = ab.lengthSquared();
    if (t >= abLen2) {
        return b;
    }

    t /= abLen2;
    return a + t * ab;
}

void CollisionChecker::generateDefaultSelfCollisionPairs(int numLinks)
{
    m_selfCollisionPairs.clear();

    for (int i = 0; i < numLinks; ++i) {
        for (int j = i + 2; j < numLinks; ++j) {
            m_selfCollisionPairs.append(qMakePair(i, j));
        }
    }
}
