#include <QApplication>
#include <QSurfaceFormat>
#include "robot_widget.h"
#include "joint.h"
#include "kinematics.h"

int main(int argc, char* argv[])
{
    QApplication app(argc, argv);

    QSurfaceFormat format;
    format.setVersion(3, 3);
    format.setProfile(QSurfaceFormat::CoreProfile);
    format.setDepthBufferSize(24);
    format.setSamples(4);
    QSurfaceFormat::setDefaultFormat(format);

    QVector<Joint> joints;

    Joint j1(0.0, 90.0, 0.5, 0.0, Joint::Type::Revolute, -180.0, 180.0);
    Joint j2(0.8, 0.0, 0.0, 0.0, Joint::Type::Revolute, -90.0, 90.0);
    Joint j3(0.6, 0.0, 0.0, 0.0, Joint::Type::Revolute, -90.0, 90.0);
    Joint j4(0.0, 90.0, 0.2, 0.0, Joint::Type::Revolute, -180.0, 180.0);
    Joint j5(0.0, -90.0, 0.0, 0.0, Joint::Type::Revolute, -90.0, 90.0);
    Joint j6(0.0, 0.0, 0.15, 0.0, Joint::Type::Revolute, -180.0, 180.0);

    joints.append(j1);
    joints.append(j2);
    joints.append(j3);
    joints.append(j4);
    joints.append(j5);
    joints.append(j6);

    Kinematics* kinematics = new Kinematics(joints);

    RobotWidget widget;
    widget.setKinematics(kinematics);

    QVector<double> initialJoints = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
    widget.setJointValues(initialJoints);

    widget.setWindowTitle(QObject::tr("Robot Kinematics Simulator - Qt3D"));
    widget.resize(1200, 800);
    widget.show();

    int result = app.exec();

    delete kinematics;
    return result;
}
