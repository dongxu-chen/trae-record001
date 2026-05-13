#include "robot_widget.h"
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
#include <QSurfaceFormat>
#include <QGridLayout>
#include <qmath.h>
#include <QMessageBox>
#include <Qt3DExtras/QConeMesh>

RobotWidget::RobotWidget(QWidget* parent)
    : QWidget(parent)
    , m_kinematics(nullptr)
    , m_trajectory(nullptr)
    , m_collisionChecker(nullptr)
    , m_planner(nullptr)
    , m_uiControl(nullptr)
    , m_currentPathIndex(0)
    , m_pathExecutionTimer(nullptr)
    , m_eePosLabel(nullptr)
    , m_eeOrientLabel(nullptr)
    , m_collisionStatusLabel(nullptr)
    , m_defaultLinkMaterial(nullptr)
    , m_collisionMaterial(nullptr)
{
    setupScene();
    createUI();

    m_collisionChecker = new CollisionChecker();
    m_planner = new RRTPlanner(this);

    m_trajectory = new Trajectory(this);
    connect(m_trajectory, &Trajectory::jointValuesChanged,
            this, &RobotWidget::onTrajectoryUpdated);
    connect(m_trajectory, &Trajectory::progressChanged,
            m_uiControl, &UIControl::setProgress);
    connect(m_trajectory, &Trajectory::trajectoryFinished,
            this, &RobotWidget::onTrajectoryFinished);

    m_pathExecutionTimer = new QTimer(this);
    connect(m_pathExecutionTimer, &QTimer::timeout,
            this, &RobotWidget::executePlannedPath);

    createDefaultObstacles();
}

RobotWidget::~RobotWidget()
{
}

void RobotWidget::setupScene()
{
    QSurfaceFormat format;
    format.setVersion(3, 3);
    format.setProfile(QSurfaceFormat::CoreProfile);
    format.setDepthBufferSize(24);
    format.setSamples(4);
    QSurfaceFormat::setDefaultFormat(format);

    m_view = new Qt3DExtras::Qt3DWindow();
    m_view->setFormat(format);
    m_view->defaultFrameGraph()->setClearColor(QColor(QRgb(0x4d4d4f)));

    m_container = QWidget::createWindowContainer(m_view, this);

    m_rootEntity = new Qt3DCore::QEntity();
    m_view->setRootEntity(m_rootEntity);

    m_camera = m_view->camera();
    m_camera->lens()->setPerspectiveProjection(45.0f, 16.0f/9.0f, 0.1f, 1000.0f);
    m_camera->setPosition(QVector3D(8.0f, 6.0f, 8.0f));
    m_camera->setViewCenter(QVector3D(0, 2, 0));

    m_camController = new Qt3DExtras::QOrbitCameraController(m_rootEntity);
    m_camController->setLinearSpeed(50.0f);
    m_camController->setLookSpeed(180.0f);
    m_camController->setCamera(m_camera);

    Qt3DCore::QEntity* lightEntity = new Qt3DCore::QEntity(m_rootEntity);
    Qt3DRender::QDirectionalLight* light = new Qt3DRender::QDirectionalLight(lightEntity);
    light->setColor("white");
    light->setIntensity(0.8f);
    light->setWorldDirection(QVector3D(-1.0f, -1.0f, -1.0f));
    lightEntity->addComponent(light);

    Qt3DCore::QEntity* lightEntity2 = new Qt3DCore::QEntity(m_rootEntity);
    Qt3DRender::QPointLight* pointLight = new Qt3DRender::QPointLight(lightEntity2);
    pointLight->setColor("white");
    pointLight->setIntensity(0.6f);
    Qt3DCore::QTransform* lightTransform = new Qt3DCore::QTransform();
    lightTransform->setTranslation(QVector3D(5.0f, 10.0f, 5.0f));
    lightEntity2->addComponent(pointLight);
    lightEntity2->addComponent(lightTransform);

    createGround();
    createRobot();
}

void RobotWidget::createGround()
{
    m_groundEntity = new Qt3DCore::QEntity(m_rootEntity);

    Qt3DExtras::QCuboidMesh* groundMesh = new Qt3DExtras::QCuboidMesh();
    groundMesh->setXExtent(20.0f);
    groundMesh->setYExtent(0.1f);
    groundMesh->setZExtent(20.0f);

    Qt3DExtras::QPhongMaterial* groundMaterial = new Qt3DExtras::QPhongMaterial();
    groundMaterial->setDiffuse(QColor(QRgb(0x808080)));
    groundMaterial->setAmbient(QColor(QRgb(0x606060)));

    Qt3DCore::QTransform* groundTransform = new Qt3DCore::QTransform();
    groundTransform->setTranslation(QVector3D(0.0f, -0.05f, 0.0f));

    m_groundEntity->addComponent(groundMesh);
    m_groundEntity->addComponent(groundMaterial);
    m_groundEntity->addComponent(groundTransform);

    for (int i = -10; i <= 10; i += 2) {
        Qt3DCore::QEntity* lineXEntity = new Qt3DCore::QEntity(m_rootEntity);
        Qt3DExtras::QCylinderMesh* lineMesh = new Qt3DExtras::QCylinderMesh();
        lineMesh->setRadius(0.01f);
        lineMesh->setLength(20.0f);
        lineMesh->setRings(1);
        lineMesh->setSlices(6);

        Qt3DExtras::QPhongMaterial* lineMaterial = new Qt3DExtras::QPhongMaterial();
        lineMaterial->setDiffuse(QColor(QRgb(0x404040)));

        Qt3DCore::QTransform* lineTransform = new Qt3DCore::QTransform();
        lineTransform->setTranslation(QVector3D(0.0f, 0.01f, (float)i));
        lineTransform->setRotation(QQuaternion::fromAxisAndAngle(QVector3D(0, 0, 1), 90.0f));

        lineXEntity->addComponent(lineMesh);
        lineXEntity->addComponent(lineMaterial);
        lineXEntity->addComponent(lineTransform);

        Qt3DCore::QEntity* lineZEntity = new Qt3DCore::QEntity(m_rootEntity);
        Qt3DExtras::QCylinderMesh* lineMesh2 = new Qt3DExtras::QCylinderMesh();
        lineMesh2->setRadius(0.01f);
        lineMesh2->setLength(20.0f);
        lineMesh2->setRings(1);
        lineMesh2->setSlices(6);

        Qt3DCore::QTransform* lineTransform2 = new Qt3DCore::QTransform();
        lineTransform2->setTranslation(QVector3D((float)i, 0.01f, 0.0f));

        lineZEntity->addComponent(lineMesh2);
        lineZEntity->addComponent(lineMaterial);
        lineZEntity->addComponent(lineTransform2);
    }
}

void RobotWidget::createRobot()
{
    m_defaultLinkMaterial = new Qt3DExtras::QPhongMaterial();
    m_defaultLinkMaterial->setDiffuse(QColor(QRgb(0x3498db)));
    m_defaultLinkMaterial->setSpecular(QColor(255, 255, 255));
    m_defaultLinkMaterial->setShininess(50.0f);

    m_collisionMaterial = new Qt3DExtras::QPhongMaterial();
    m_collisionMaterial->setDiffuse(QColor(QRgb(0xe74c3c)));
    m_collisionMaterial->setSpecular(QColor(255, 255, 255));
    m_collisionMaterial->setShininess(80.0f);

    QVector<QColor> linkColors = {
        QColor(QRgb(0x3498db)),
        QColor(QRgb(0xe74c3c)),
        QColor(QRgb(0x2ecc71)),
        QColor(QRgb(0x9b59b6)),
        QColor(QRgb(0xe67e22)),
        QColor(QRgb(0x1abc9c))
    };

    for (int i = 0; i < 6; ++i) {
        Qt3DCore::QEntity* linkEntity = new Qt3DCore::QEntity(m_rootEntity);

        Qt3DExtras::QCylinderMesh* linkMesh = new Qt3DExtras::QCylinderMesh();
        linkMesh->setRadius(0.15f);
        linkMesh->setLength(1.0f);
        linkMesh->setRings(10);
        linkMesh->setSlices(20);

        Qt3DExtras::QPhongMaterial* linkMaterial = new Qt3DExtras::QPhongMaterial();
        linkMaterial->setDiffuse(linkColors[i % linkColors.size()]);
        linkMaterial->setSpecular(QColor(255, 255, 255));
        linkMaterial->setShininess(50.0f);

        Qt3DCore::QTransform* linkTransform = new Qt3DCore::QTransform();
        linkEntity->addComponent(linkMesh);
        linkEntity->addComponent(linkMaterial);
        linkEntity->addComponent(linkTransform);

        m_linkEntities.append(linkEntity);
        m_linkTransforms.append(linkTransform);

        Qt3DCore::QEntity* jointEntity = new Qt3DCore::QEntity(m_rootEntity);
        Qt3DExtras::QSphereMesh* jointMesh = new Qt3DExtras::QSphereMesh();
        jointMesh->setRadius(0.2f);
        jointMesh->setRings(15);
        jointMesh->setSlices(15);

        Qt3DExtras::QPhongMaterial* jointMaterial = new Qt3DExtras::QPhongMaterial();
        jointMaterial->setDiffuse(QColor(QRgb(0xf1c40f)));
        jointMaterial->setSpecular(QColor(255, 255, 255));
        jointMaterial->setShininess(80.0f);

        Qt3DCore::QTransform* jointTransform = new Qt3DCore::QTransform();
        jointEntity->addComponent(jointMesh);
        jointEntity->addComponent(jointMaterial);
        jointEntity->addComponent(jointTransform);

        m_jointEntities.append(jointEntity);
        m_jointTransforms.append(jointTransform);
    }

    m_endEffectorEntity = new Qt3DCore::QEntity(m_rootEntity);
    Qt3DExtras::QCuboidMesh* eeMesh = new Qt3DExtras::QCuboidMesh();
    eeMesh->setXExtent(0.3f);
    eeMesh->setYExtent(0.15f);
    eeMesh->setZExtent(0.3f);

    Qt3DExtras::QPhongMaterial* eeMaterial = new Qt3DExtras::QPhongMaterial();
    eeMaterial->setDiffuse(QColor(QRgb(0xecf0f1)));
    eeMaterial->setSpecular(QColor(255, 255, 255));
    eeMaterial->setShininess(100.0f);

    m_endEffectorTransform = new Qt3DCore::QTransform();
    m_endEffectorEntity->addComponent(eeMesh);
    m_endEffectorEntity->addComponent(eeMaterial);
    m_endEffectorEntity->addComponent(m_endEffectorTransform);
}

void RobotWidget::createUI()
{
    QVBoxLayout* mainLayout = new QVBoxLayout(this);
    QHBoxLayout* contentLayout = new QHBoxLayout();

    m_container->setMinimumSize(600, 500);
    contentLayout->addWidget(m_container, 2);

    QWidget* rightPanel = new QWidget();
    QVBoxLayout* rightLayout = new QVBoxLayout(rightPanel);
    rightPanel->setMinimumWidth(350);

    m_uiControl = new UIControl(6, rightPanel);
    rightLayout->addWidget(m_uiControl);

    connect(m_uiControl, &UIControl::jointValueChanged,
            this, &RobotWidget::onJointSliderChanged);
    connect(m_uiControl, &UIControl::playClicked,
            this, &RobotWidget::onPlayTrajectory);
    connect(m_uiControl, &UIControl::stopClicked,
            this, &RobotWidget::onStopTrajectory);
    connect(m_uiControl, &UIControl::resetClicked,
            this, &RobotWidget::onResetTrajectory);
    connect(m_uiControl, &UIControl::planAndPlayClicked,
            this, &RobotWidget::onPlanAndPlay);

    QGroupBox* infoGroup = new QGroupBox(tr("Status"));
    QVBoxLayout* infoLayout = new QVBoxLayout(infoGroup);
    m_eePosLabel = new QLabel(tr("Position: (0.00, 0.00, 0.00)"));
    m_eeOrientLabel = new QLabel(tr("Orientation: (0.00, 0.00, 0.00) deg"));
    m_collisionStatusLabel = new QLabel(tr("Collision: None"));
    m_collisionStatusLabel->setStyleSheet("color: green; font-weight: bold;");
    infoLayout->addWidget(m_eePosLabel);
    infoLayout->addWidget(m_eeOrientLabel);
    infoLayout->addWidget(m_collisionStatusLabel);
    rightLayout->addWidget(infoGroup);

    rightLayout->addStretch();
    contentLayout->addWidget(rightPanel, 1);
    mainLayout->addLayout(contentLayout);
}

void RobotWidget::createDefaultObstacles()
{
    CollisionGeometry obs1;
    obs1.type = CollisionGeometry::Type::Box;
    obs1.position = QVector3D(1.5, 1.0, 0);
    obs1.orientation = QQuaternion();
    obs1.size = QVector3D(0.8, 2.0, 0.8);
    addObstacle(obs1);

    CollisionGeometry obs2;
    obs2.type = CollisionGeometry::Type::Sphere;
    obs2.position = QVector3D(-1.2, 1.5, 1.0);
    obs2.radius = 0.35;
    addObstacle(obs2);
}

void RobotWidget::addObstacle(const CollisionGeometry& obstacle)
{
    if (!m_collisionChecker) {
        return;
    }

    m_collisionChecker->addObstacle(obstacle);

    Qt3DCore::QEntity* entity = new Qt3DCore::QEntity(m_rootEntity);
    Qt3DCore::QTransform* transform = new Qt3DCore::QTransform();
    transform->setTranslation(obstacle.position);
    transform->setRotation(obstacle.orientation);

    Qt3DExtras::QPhongMaterial* material = new Qt3DExtras::QPhongMaterial();
    material->setDiffuse(QColor(QRgb(0x95a5a6)));
    material->setAmbient(QColor(QRgb(0x7f8c8d)));
    material->setShininess(30.0f);

    if (obstacle.type == CollisionGeometry::Type::Box) {
        Qt3DExtras::QCuboidMesh* mesh = new Qt3DExtras::QCuboidMesh();
        mesh->setXExtent(obstacle.size.x());
        mesh->setYExtent(obstacle.size.y());
        mesh->setZExtent(obstacle.size.z());
        entity->addComponent(mesh);
    } else if (obstacle.type == CollisionGeometry::Type::Sphere) {
        Qt3DExtras::QSphereMesh* mesh = new Qt3DExtras::QSphereMesh();
        mesh->setRadius((float)obstacle.radius);
        mesh->setRings(15);
        mesh->setSlices(15);
        entity->addComponent(mesh);
    } else if (obstacle.type == CollisionGeometry::Type::Cylinder ||
               obstacle.type == CollisionGeometry::Type::Capsule) {
        Qt3DExtras::QCylinderMesh* mesh = new Qt3DExtras::QCylinderMesh();
        mesh->setRadius((float)obstacle.radius);
        mesh->setLength((float)obstacle.height);
        mesh->setRings(10);
        mesh->setSlices(15);
        entity->addComponent(mesh);
    }

    entity->addComponent(material);
    entity->addComponent(transform);

    m_obstacleEntities.append(entity);
}

void RobotWidget::clearObstacles()
{
    if (m_collisionChecker) {
        m_collisionChecker->clearObstacles();
    }

    for (Qt3DCore::QEntity* entity : m_obstacleEntities) {
        if (entity) {
            entity->setParent((Qt3DCore::QNode*)nullptr);
        }
    }
    m_obstacleEntities.clear();
}

void RobotWidget::setJointValues(const QVector<double>& values)
{
    m_jointValues = values;
    m_uiControl->setJointValues(values);

    updateRobotPoses();
    updateEndEffectorInfo();
    updateCollisionStatus();
}

void RobotWidget::setKinematics(Kinematics* kinematics)
{
    m_kinematics = kinematics;

    if (m_kinematics && m_jointValues.isEmpty()) {
        int n = m_kinematics->numJoints();
        m_jointValues.fill(0.0, n);
    }

    if (m_collisionChecker && m_kinematics) {
        QVector<double> linkLengths = {0.5, 0.8, 0.6, 0.2, 0.15, 0.15};
        m_collisionChecker->setRobotLinks(m_kinematics->joints(), linkLengths);
    }

    if (m_planner) {
        m_planner->setKinematics(m_kinematics);
        m_planner->setCollisionChecker(m_collisionChecker);
    }

    updateRobotPoses();
    updateEndEffectorInfo();
}

void RobotWidget::onJointSliderChanged(int index, double value)
{
    if (index < m_jointValues.size()) {
        m_jointValues[index] = value;
    } else {
        m_jointValues.append(value);
    }

    updateRobotPoses();
    updateEndEffectorInfo();
    updateCollisionStatus();
}

void RobotWidget::onPlayTrajectory()
{
    if (!m_kinematics || m_trajectory->isRunning()) {
        return;
    }

    Pose startPose = m_kinematics->computeEndEffectorPose(m_jointValues);
    Pose endPose(m_uiControl->targetPosition(), m_uiControl->targetOrientation());

    m_trajectory->setCartesianTrajectory(
        startPose, endPose, m_jointValues, 3.0, m_kinematics);
    m_trajectory->setInterpolationMethod(Trajectory::InterpolationMethod::Quintic);
    m_trajectory->start();

    m_uiControl->setPlayEnabled(false);
    m_uiControl->setStopEnabled(true);
}

void RobotWidget::onStopTrajectory()
{
    m_trajectory->stop();
    if (m_pathExecutionTimer && m_pathExecutionTimer->isActive()) {
        m_pathExecutionTimer->stop();
    }
    m_uiControl->setPlayEnabled(true);
    m_uiControl->setStopEnabled(false);
}

void RobotWidget::onResetTrajectory()
{
    m_trajectory->reset();
    m_uiControl->setProgress(0);
    m_uiControl->setPlayEnabled(true);
    m_uiControl->setStopEnabled(false);

    if (m_pathExecutionTimer) {
        m_pathExecutionTimer->stop();
    }
    m_plannedPath.clear();
    m_currentPathIndex = 0;

    QVector<double> zeros(m_jointValues.size(), 0.0);
    setJointValues(zeros);
}

void RobotWidget::onPlanAndPlay()
{
    if (!m_kinematics || !m_planner) {
        QMessageBox::warning(this, tr("Error"), tr("Planner not initialized"));
        return;
    }

    Pose targetPose(m_uiControl->targetPosition(), m_uiControl->targetOrientation());

    m_plannedPath = m_planner->planToPose(m_jointValues, targetPose);

    if (m_plannedPath.isEmpty()) {
        QMessageBox::information(this, tr("Planning"),
            tr("Path planning failed (no valid path found in %1 iterations).\n"
               "Try adjusting the target position or obstacles.")
                .arg(m_planner->config().maxIterations));
        return;
    }

    m_plannedPath = m_planner->smoothPath(m_plannedPath);
    m_currentPathIndex = 0;

    QMessageBox::information(this, tr("Planning"),
        tr("Path planned successfully!\n"
           "Path points: %1\n"
           "Iterations: %2")
            .arg(m_plannedPath.size())
            .arg(m_planner->lastIterationCount()));

    m_pathExecutionTimer->start(100);
}

void RobotWidget::executePlannedPath()
{
    if (m_currentPathIndex >= m_plannedPath.size()) {
        m_pathExecutionTimer->stop();
        onTrajectoryFinished();
        return;
    }

    setJointValues(m_plannedPath[m_currentPathIndex]);
    m_currentPathIndex++;

    int progress = (m_currentPathIndex * 100) / m_plannedPath.size();
    m_uiControl->setProgress(progress);
}

void RobotWidget::onTrajectoryUpdated(const QVector<double>& values)
{
    setJointValues(values);
}

void RobotWidget::onTrajectoryFinished()
{
    m_uiControl->setPlayEnabled(true);
    m_uiControl->setStopEnabled(false);
}

void RobotWidget::onTargetPoseChanged(const QVector3D& pos, const QQuaternion& orient)
{
    Q_UNUSED(pos);
    Q_UNUSED(orient);
}

void RobotWidget::updateRobotPoses()
{
    if (!m_kinematics) {
        return;
    }

    QVector<Pose> poses = m_kinematics->getAllLinkPoses(m_jointValues);
    if (poses.isEmpty()) {
        return;
    }

    for (int i = 0; i < qMin(m_jointEntities.size(), poses.size() - 1); ++i) {
        const Pose& startPose = poses[i];
        const Pose& endPose = poses[i + 1];

        m_jointTransforms[i]->setTranslation(endPose.position);
        m_jointTransforms[i]->setRotation(endPose.orientation);

        if (i < m_linkTransforms.size()) {
            QVector3D linkPos = (startPose.position + endPose.position) * 0.5f;
            m_linkTransforms[i]->setTranslation(linkPos);

            QVector3D linkAxis = endPose.position - startPose.position;
            if (linkAxis.length() > 1e-6) {
                linkAxis.normalize();

                QVector3D cylinderAxis(0.0f, 1.0f, 0.0f);
                double dot = QVector3D::dotProduct(cylinderAxis, linkAxis);
                dot = std::max(-1.0, std::min(1.0, dot));

                if (qAbs(1.0 - dot) < 1e-6) {
                    m_linkTransforms[i]->setRotation(QQuaternion());
                } else if (qAbs(-1.0 - dot) < 1e-6) {
                    m_linkTransforms[i]->setRotation(QQuaternion::fromAxisAndAngle(
                        QVector3D(1.0f, 0.0f, 0.0f), 180.0f));
                } else {
                    QVector3D axis = QVector3D::crossProduct(cylinderAxis, linkAxis);
                    axis.normalize();
                    double angle = qRadiansToDegrees(qAcos(dot));
                    m_linkTransforms[i]->setRotation(QQuaternion::fromAxisAndAngle(axis, angle));
                }
            }
        }
    }

    if (!poses.isEmpty()) {
        m_endEffectorTransform->setTranslation(poses.last().position);
        m_endEffectorTransform->setRotation(poses.last().orientation);
    }
}

void RobotWidget::updateEndEffectorInfo()
{
    if (!m_kinematics || !m_eePosLabel || !m_eeOrientLabel) {
        return;
    }

    Pose pose = m_kinematics->computeEndEffectorPose(m_jointValues);
    m_eePosLabel->setText(tr("Position: (%1, %2, %3)")
        .arg(pose.position.x(), 0, 'f', 2)
        .arg(pose.position.y(), 0, 'f', 2)
        .arg(pose.position.z(), 0, 'f', 2));

    float roll, pitch, yaw;
    pose.orientation.getEulerAngles(&roll, &pitch, &yaw);
    m_eeOrientLabel->setText(tr("Orientation: (%1, %2, %3) deg")
        .arg(roll, 0, 'f', 1)
        .arg(pitch, 0, 'f', 1)
        .arg(yaw, 0, 'f', 1));
}

void RobotWidget::updateCollisionStatus()
{
    if (!m_collisionChecker || !m_kinematics || !m_collisionStatusLabel) {
        return;
    }

    bool envCollision = m_collisionChecker->checkEnvironmentCollision(m_jointValues, m_kinematics);

    if (envCollision) {
        m_collisionStatusLabel->setText(tr("Collision: DETECTED!"));
        m_collisionStatusLabel->setStyleSheet("color: red; font-weight: bold;");
    } else {
        m_collisionStatusLabel->setText(tr("Collision: None"));
        m_collisionStatusLabel->setStyleSheet("color: green; font-weight: bold;");
    }
}
