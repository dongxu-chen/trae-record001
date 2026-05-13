#ifndef COLLISION_CHECKER_H
#define COLLISION_CHECKER_H

#include "joint.h"
#include "kinematics.h"
#include <QVector>
#include <QVector3D>
#include <QPair>
#include <QSharedPointer>

struct CollisionGeometry {
    enum class Type { Sphere, Cylinder, Box, Capsule };

    Type type;
    QVector3D position;
    QQuaternion orientation;
    QVector3D size;
    double radius;
    double height;
    int linkIndex;

    CollisionGeometry()
        : type(Type::Sphere)
        , position(0, 0, 0)
        , orientation()
        , size(1, 1, 1)
        , radius(0.2)
        , height(1.0)
        , linkIndex(-1)
    {}
};

class CollisionChecker {
public:
    explicit CollisionChecker();

    void setRobotLinks(const QVector<Joint>& joints,
                      const QVector<double>& linkLengths = {});

    void addObstacle(const CollisionGeometry& obstacle);
    void clearObstacles();
    int obstacleCount() const { return m_obstacles.size(); }

    bool checkSelfCollision(const QVector<double>& jointValues) const;
    bool checkEnvironmentCollision(const QVector<double>& jointValues,
                                    Kinematics* kinematics) const;
    bool isColliding(const QVector<double>& jointValues,
                     Kinematics* kinematics) const;

    double minDistanceToObstacles(const QVector<double>& jointValues,
                                   Kinematics* kinematics) const;

    bool checkMotionCollision(const QVector<double>& start,
                               const QVector<double>& end,
                               Kinematics* kinematics,
                               int steps = 10) const;

    const QVector<CollisionGeometry>& obstacles() const { return m_obstacles; }

    void setSelfCollisionPairs(const QVector<QPair<int, int>>& pairs);
    const QVector<QPair<int, int>>& selfCollisionPairs() const { return m_selfCollisionPairs; }

private:
    QVector<CollisionGeometry> m_linkGeometries;
    QVector<CollisionGeometry> m_obstacles;
    QVector<QPair<int, int>> m_selfCollisionPairs;
    QVector<double> m_linkLengths;

    bool checkSphereSphere(const CollisionGeometry& s1,
                           const CollisionGeometry& s2) const;
    bool checkSphereCylinder(const CollisionGeometry& sphere,
                             const CollisionGeometry& cyl) const;
    bool checkSphereBox(const CollisionGeometry& sphere,
                        const CollisionGeometry& box) const;
    bool checkCylinderCylinder(const CollisionGeometry& c1,
                               const CollisionGeometry& c2) const;

    double distanceSphereSphere(const CollisionGeometry& s1,
                                const CollisionGeometry& s2) const;

    QVector<CollisionGeometry> getLinkGeometriesAtPose(
        const QVector<double>& jointValues,
        Kinematics* kinematics) const;

    QVector3D closestPointOnSegment(const QVector3D& p,
                                    const QVector3D& a,
                                    const QVector3D& b) const;

    void generateDefaultSelfCollisionPairs(int numLinks);
};

#endif
