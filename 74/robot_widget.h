#ifndef ROBOT_WIDGET_H
#define ROBOT_WIDGET_H

#include <Qt3DExtras/Qt3DWindow>
#include <Qt3DCore/QEntity>
#include <Qt3DCore/QTransform>
#include <Qt3DRender/QCamera>
#include <Qt3DRender/QPointLight>
#include <Qt3DExtras/QOrbitCameraController>
#include <Qt3DExtras/QPhongMaterial>
#include <Qt3DExtras/QCylinderMesh>
#include <Qt3DExtras/QSphereMesh>
#include <Qt3DExtras/QCuboidMesh>
#include <Qt3DRender/QDirectionalLight>

#include "joint.h"
#include "kinematics.h"
#include "trajectory.h"
#include "collision_checker.h"
#include "planning.h"
#include "ui_control.h"

#include <QWidget>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QSlider>
#include <QLabel>
#include <QPushButton>
#include <QGroupBox>
#include <QDoubleSpinBox>
#include <QProgressBar>
#include <QTimer>

class RobotWidget : public QWidget {
    Q_OBJECT
public:
    explicit RobotWidget(QWidget* parent = nullptr);
    ~RobotWidget() override;

    void setJointValues(const QVector<double>& values);
    QVector<double> jointValues() const { return m_jointValues; }

    void setKinematics(Kinematics* kinematics);
    Kinematics* kinematics() const { return m_kinematics; }

    CollisionChecker* collisionChecker() const { return m_collisionChecker; }
    RRTPlanner* planner() const { return m_planner; }

    void addObstacle(const CollisionGeometry& obstacle);
    void clearObstacles();

private slots:
    void onJointSliderChanged(int index, double value);
    void onPlayTrajectory();
    void onStopTrajectory();
    void onResetTrajectory();
    void onPlanAndPlay();
    void onTrajectoryUpdated(const QVector<double>& values);
    void onTrajectoryFinished();
    void onTargetPoseChanged(const QVector3D& pos, const QQuaternion& orient);
    void executePlannedPath();

private:
    void setupScene();
    void createRobot();
    void createUI();
    void createGround();
    void createDefaultObstacles();
    void updateRobotPoses();
    void updateEndEffectorInfo();
    void updateCollisionStatus();

    Qt3DExtras::Qt3DWindow* m_view;
    QWidget* m_container;

    Qt3DCore::QEntity* m_rootEntity;
    Qt3DCore::QEntity* m_groundEntity;
    QVector<Qt3DCore::QEntity*> m_linkEntities;
    QVector<Qt3DCore::QEntity*> m_jointEntities;
    QVector<Qt3DCore::QTransform*> m_linkTransforms;
    QVector<Qt3DCore::QTransform*> m_jointTransforms;
    Qt3DCore::QEntity* m_endEffectorEntity;
    Qt3DCore::QTransform* m_endEffectorTransform;
    QVector<Qt3DCore::QEntity*> m_obstacleEntities;

    Qt3DRender::QCamera* m_camera;
    Qt3DExtras::QOrbitCameraController* m_camController;

    Kinematics* m_kinematics;
    Trajectory* m_trajectory;
    CollisionChecker* m_collisionChecker;
    RRTPlanner* m_planner;

    UIControl* m_uiControl;

    QVector<double> m_jointValues;
    QVector<QVector<double>> m_plannedPath;
    int m_currentPathIndex;
    QTimer* m_pathExecutionTimer;

    QLabel* m_eePosLabel;
    QLabel* m_eeOrientLabel;
    QLabel* m_collisionStatusLabel;

    Qt3DExtras::QPhongMaterial* m_defaultLinkMaterial;
    Qt3DExtras::QPhongMaterial* m_collisionMaterial;
};

#endif
