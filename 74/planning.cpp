#include "planning.h"
#include <qmath.h>
#include <QRandomGenerator>
#include <algorithm>

RRTPlanner::RRTPlanner()
    : m_kinematics(nullptr)
    , m_collisionChecker(nullptr)
    , m_lastIterations(0)
{
}

void RRTPlanner::setKinematics(Kinematics* kinematics)
{
    m_kinematics = kinematics;
}

void RRTPlanner::setCollisionChecker(CollisionChecker* checker)
{
    m_collisionChecker = checker;
}

void RRTPlanner::setConfig(const PlannerConfig& config)
{
    m_config = config;
}

QVector<QVector<double>> RRTPlanner::plan(const QVector<double>& start,
                                           const QVector<double>& goal)
{
    QVector<QVector<double>> result;

    if (!m_kinematics || start.size() != goal.size()) {
        return result;
    }

    if (m_collisionChecker) {
        if (m_collisionChecker->isColliding(start, m_kinematics)) {
            return result;
        }
        if (m_collisionChecker->isColliding(goal, m_kinematics)) {
            return result;
        }
    }

    m_tree.clear();
    m_goalConfig = goal;
    m_lastIterations = 0;

    m_tree.append(RRTNode(start, -1));

    for (int iter = 0; iter < m_config.maxIterations; ++iter) {
        m_lastIterations = iter;

        QVector<double> randConfig;
        double r = QRandomGenerator::global()->generateDouble();
        if (r < m_config.goalBias) {
            randConfig = goal;
        } else {
            randConfig = randomConfig(start.size());
        }

        int nearestIdx = nearestNeighbor(randConfig);
        if (nearestIdx < 0) {
            continue;
        }

        const RRTNode& nearestNode = m_tree[nearestIdx];
        QVector<double> newConfig = steer(nearestNode.config, randConfig);

        if (m_collisionChecker) {
            if (m_collisionChecker->checkMotionCollision(
                    nearestNode.config, newConfig, m_kinematics,
                    m_config.collisionCheckSteps)) {
                continue;
            }
        }

        double newCost = nearestNode.cost + configDistance(nearestNode.config, newConfig);
        RRTNode newNode(newConfig, nearestIdx);
        newNode.cost = newCost;
        m_tree.append(newNode);

        if (configDistance(newConfig, goal) < m_config.goalTolerance) {
            if (m_collisionChecker) {
                if (!m_collisionChecker->checkMotionCollision(
                        newConfig, goal, m_kinematics, m_config.collisionCheckSteps)) {
                    m_tree.append(RRTNode(goal, m_tree.size() - 1));
                    result = extractPath(m_tree.size() - 1);
                    emit pathFound(result);
                    return result;
                }
            } else {
                m_tree.append(RRTNode(goal, m_tree.size() - 1));
                result = extractPath(m_tree.size() - 1);
                emit pathFound(result);
                return result;
            }
        }
    }

    emit planningFailed();
    return result;
}

QVector<QVector<double>> RRTPlanner::planToPose(const QVector<double>& start,
                                                 const Pose& targetPose)
{
    if (!m_kinematics) {
        return {};
    }

    QVector<double> goalConfig = m_kinematics->inverseKinematics(
        targetPose, start, 1e-3, 200);

    return plan(start, goalConfig);
}

QVector<QVector<double>> RRTPlanner::smoothPath(const QVector<QVector<double>>& path)
{
    if (path.size() < 3) {
        return path;
    }

    QVector<QVector<double>> result = path;
    const int maxIterations = 100;

    for (int iter = 0; iter < maxIterations; ++iter) {
        bool changed = false;
        int n = result.size();

        for (int i = 0; i < n - 2; ++i) {
            for (int j = n - 1; j > i + 1; --j) {
                if (m_collisionChecker && m_kinematics) {
                    if (!m_collisionChecker->checkMotionCollision(
                            result[i], result[j], m_kinematics,
                            m_config.collisionCheckSteps)) {
                        result.erase(result.begin() + i + 1, result.begin() + j);
                        changed = true;
                        break;
                    }
                } else {
                    result.erase(result.begin() + i + 1, result.begin() + j);
                    changed = true;
                    break;
                }
            }
            if (changed) break;
        }

        if (!changed) {
            break;
        }
    }

    return result;
}

bool RRTPlanner::isPathValid(const QVector<QVector<double>>& path) const
{
    if (!m_collisionChecker || !m_kinematics) {
        return true;
    }

    for (int i = 0; i < path.size() - 1; ++i) {
        if (m_collisionChecker->checkMotionCollision(
                path[i], path[i + 1], m_kinematics,
                m_config.collisionCheckSteps)) {
            return false;
        }
    }

    return true;
}

QVector<double> RRTPlanner::randomConfig(int n) const
{
    QVector<double> config(n);

    for (int i = 0; i < n; ++i) {
        double lower = -180.0;
        double upper = 180.0;

        if (m_kinematics && i < m_kinematics->joints().size()) {
            lower = m_kinematics->joints()[i].lowerLimit();
            upper = m_kinematics->joints()[i].upperLimit();
        }

        double r = QRandomGenerator::global()->generateDouble();
        config[i] = lower + r * (upper - lower);
    }

    return config;
}

int RRTPlanner::nearestNeighbor(const QVector<double>& config) const
{
    if (m_tree.isEmpty()) {
        return -1;
    }

    int nearestIdx = 0;
    double nearestDist = configDistance(m_tree[0].config, config);

    for (int i = 1; i < m_tree.size(); ++i) {
        double dist = configDistance(m_tree[i].config, config);
        if (dist < nearestDist) {
            nearestDist = dist;
            nearestIdx = i;
        }
    }

    return nearestIdx;
}

double RRTPlanner::configDistance(const QVector<double>& a, const QVector<double>& b) const
{
    int n = qMin(a.size(), b.size());
    double sum = 0.0;

    for (int i = 0; i < n; ++i) {
        double diff = a[i] - b[i];
        sum += diff * diff;
    }

    return qSqrt(sum);
}

QVector<double> RRTPlanner::steer(const QVector<double>& from,
                                   const QVector<double>& to) const
{
    int n = qMin(from.size(), to.size());
    QVector<double> result(n);

    double dist = configDistance(from, to);

    if (dist <= m_config.stepSize) {
        return to;
    }

    double t = m_config.stepSize / dist;
    for (int i = 0; i < n; ++i) {
        result[i] = from[i] + t * (to[i] - from[i]);
    }

    return result;
}

QVector<QVector<double>> RRTPlanner::extractPath(int goalIndex) const
{
    QVector<QVector<double>> path;

    int current = goalIndex;
    while (current >= 0 && current < m_tree.size()) {
        path.prepend(m_tree[current].config);
        current = m_tree[current].parentIndex;
    }

    return path;
}
