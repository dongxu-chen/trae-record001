#ifndef PLANNING_H
#define PLANNING_H

#include <QObject>
#include "joint.h"
#include "kinematics.h"
#include "collision_checker.h"
#include <QVector>
#include <QPair>
#include <QList>
#include <QtGlobal>

struct RRTNode {
    QVector<double> config;
    int parentIndex;
    double cost;

    RRTNode()
        : parentIndex(-1)
        , cost(0.0)
    {}

    RRTNode(const QVector<double>& cfg, int parent = -1)
        : config(cfg)
        , parentIndex(parent)
        , cost(0.0)
    {}
};

struct PlannerConfig {
    double goalBias;
    double stepSize;
    int maxIterations;
    double goalTolerance;
    int collisionCheckSteps;

    PlannerConfig()
        : goalBias(0.1)
        , stepSize(0.5)
        , maxIterations(1000)
        , goalTolerance(0.1)
        , collisionCheckSteps(5)
    {}
};

class RRTPlanner : public QObject {
    Q_OBJECT
public:
    explicit RRTPlanner();

    void setKinematics(Kinematics* kinematics);
    void setCollisionChecker(CollisionChecker* checker);
    void setConfig(const PlannerConfig& config);

    PlannerConfig config() const { return m_config; }

    QVector<QVector<double>> plan(const QVector<double>& start,
                                  const QVector<double>& goal);

    QVector<QVector<double>> planToPose(const QVector<double>& start,
                                        const Pose& targetPose);

    QVector<QVector<double>> smoothPath(const QVector<QVector<double>>& path);

    bool isPathValid(const QVector<QVector<double>>& path) const;

    const QList<RRTNode>& tree() const { return m_tree; }
    const QVector<double>& goalConfig() const { return m_goalConfig; }
    int lastIterationCount() const { return m_lastIterations; }

signals:
    void pathFound(const QVector<QVector<double>>& path);
    void planningFailed();

private:
    Kinematics* m_kinematics;
    CollisionChecker* m_collisionChecker;
    PlannerConfig m_config;

    QList<RRTNode> m_tree;
    QVector<double> m_goalConfig;
    int m_lastIterations;

    QVector<double> randomConfig(int n) const;
    int nearestNeighbor(const QVector<double>& config) const;
    double configDistance(const QVector<double>& a, const QVector<double>& b) const;
    QVector<double> steer(const QVector<double>& from,
                           const QVector<double>& to) const;

    QVector<QVector<double>> extractPath(int goalIndex) const;
};

#endif
