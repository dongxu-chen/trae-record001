#include "ui_control.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QGroupBox>
#include <QSlider>
#include <QDoubleSpinBox>
#include <QPushButton>
#include <QProgressBar>
#include <QGridLayout>
#include <qmath.h>

UIControl::UIControl(int numJoints, QWidget* parent)
    : QWidget(parent)
    , m_numJoints(numJoints)
    , m_jointValues(numJoints, 0.0)
{
    QVBoxLayout* mainLayout = new QVBoxLayout(this);
    mainLayout->setContentsMargins(8, 8, 8, 8);
    mainLayout->setSpacing(8);

    createJointControls(mainLayout);
    createTargetPoseControls(mainLayout);
    createTrajectoryControls(mainLayout);

    mainLayout->addStretch();
}

void UIControl::createJointControls(QVBoxLayout* mainLayout)
{
    QGroupBox* jointGroup = new QGroupBox(tr("Joint Control"));
    QVBoxLayout* jointLayout = new QVBoxLayout(jointGroup);
    jointLayout->setSpacing(6);

    for (int i = 0; i < m_numJoints; ++i) {
        QHBoxLayout* rowLayout = new QHBoxLayout();

        QLabel* label = new QLabel(tr("J%1:").arg(i + 1));
        label->setMinimumWidth(30);

        QSlider* slider = new QSlider(Qt::Horizontal);
        slider->setRange(-18000, 18000);
        slider->setValue(0);
        slider->setMinimumWidth(120);

        QDoubleSpinBox* spinBox = new QDoubleSpinBox();
        spinBox->setRange(-180.0, 180.0);
        spinBox->setSingleStep(1.0);
        spinBox->setDecimals(1);
        spinBox->setSuffix("°");
        spinBox->setMaximumWidth(80);

        int idx = i;
        connect(slider, &QSlider::valueChanged, this, [this, idx](int value) {
            onJointSliderChanged(idx, value);
        });
        connect(spinBox, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
                this, [this, idx](double value) {
            onJointSpinBoxChanged(idx, value);
        });

        m_jointSliders.append(slider);
        m_jointSpinBoxes.append(spinBox);
        m_jointLabels.append(label);

        rowLayout->addWidget(label);
        rowLayout->addWidget(slider, 1);
        rowLayout->addWidget(spinBox);
        jointLayout->addLayout(rowLayout);
    }

    mainLayout->addWidget(jointGroup);
}

void UIControl::createTargetPoseControls(QVBoxLayout* mainLayout)
{
    QGroupBox* targetGroup = new QGroupBox(tr("Target Pose"));
    QGridLayout* targetLayout = new QGridLayout(targetGroup);

    QStringList labels = {"X:", "Y:", "Z:", "Roll:", "Pitch:", "Yaw:"};

    for (int i = 0; i < 6; ++i) {
        QDoubleSpinBox* spinBox = new QDoubleSpinBox();

        if (i < 3) {
            spinBox->setRange(-10.0, 10.0);
            spinBox->setSingleStep(0.1);
            spinBox->setDecimals(2);
            spinBox->setSuffix(" m");
            spinBox->setValue(i == 1 ? 3.0 : 0.0);
        } else {
            spinBox->setRange(-180.0, 180.0);
            spinBox->setSingleStep(1.0);
            spinBox->setDecimals(1);
            spinBox->setSuffix("°");
            spinBox->setValue(0.0);
        }

        connect(spinBox, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
                this, &UIControl::onTargetPoseChanged);

        m_targetPoseInputs.append(spinBox);

        int row = i / 3;
        int col = (i % 3) * 2;

        targetLayout->addWidget(new QLabel(labels[i]), row, col);
        targetLayout->addWidget(spinBox, row, col + 1);
    }

    mainLayout->addWidget(targetGroup);
}

void UIControl::createTrajectoryControls(QVBoxLayout* mainLayout)
{
    QGroupBox* trajectoryGroup = new QGroupBox(tr("Trajectory & Planning"));
    QVBoxLayout* trajectoryLayout = new QVBoxLayout(trajectoryGroup);

    QHBoxLayout* buttonLayout1 = new QHBoxLayout();
    m_playBtn = new QPushButton(tr("Play"));
    m_stopBtn = new QPushButton(tr("Stop"));
    m_resetBtn = new QPushButton(tr("Reset"));

    buttonLayout1->addWidget(m_playBtn);
    buttonLayout1->addWidget(m_stopBtn);
    buttonLayout1->addWidget(m_resetBtn);

    trajectoryLayout->addLayout(buttonLayout1);

    QHBoxLayout* buttonLayout2 = new QHBoxLayout();
    m_planBtn = new QPushButton(tr("Plan & Play"));
    buttonLayout2->addWidget(m_planBtn);
    trajectoryLayout->addLayout(buttonLayout2);

    m_progressBar = new QProgressBar();
    m_progressBar->setRange(0, 100);
    m_progressBar->setValue(0);
    trajectoryLayout->addWidget(m_progressBar);

    connect(m_playBtn, &QPushButton::clicked, this, &UIControl::playClicked);
    connect(m_stopBtn, &QPushButton::clicked, this, &UIControl::stopClicked);
    connect(m_resetBtn, &QPushButton::clicked, this, &UIControl::resetClicked);
    connect(m_planBtn, &QPushButton::clicked, this, &UIControl::planAndPlayClicked);

    m_playBtn->setEnabled(true);
    m_stopBtn->setEnabled(false);
    m_resetBtn->setEnabled(true);
    m_planBtn->setEnabled(true);

    mainLayout->addWidget(trajectoryGroup);
}

void UIControl::setJointValues(const QVector<double>& values)
{
    int n = qMin(m_numJoints, values.size());

    for (int i = 0; i < n; ++i) {
        m_jointValues[i] = values[i];
        updateJointDisplay(i);
    }
}

void UIControl::setTargetPose(const QVector3D& pos, const QQuaternion& orient)
{
    if (m_targetPoseInputs.size() < 6) {
        return;
    }

    for (int i = 0; i < 6; ++i) {
        m_targetPoseInputs[i]->blockSignals(true);
    }

    m_targetPoseInputs[0]->setValue(pos.x());
    m_targetPoseInputs[1]->setValue(pos.y());
    m_targetPoseInputs[2]->setValue(pos.z());

    float roll, pitch, yaw;
    orient.getEulerAngles(&roll, &pitch, &yaw);
    m_targetPoseInputs[3]->setValue((double)roll);
    m_targetPoseInputs[4]->setValue((double)pitch);
    m_targetPoseInputs[5]->setValue((double)yaw);

    for (int i = 0; i < 6; ++i) {
        m_targetPoseInputs[i]->blockSignals(false);
    }
}

QVector3D UIControl::targetPosition() const
{
    if (m_targetPoseInputs.size() < 3) {
        return QVector3D(0, 0, 0);
    }
    return QVector3D(
        m_targetPoseInputs[0]->value(),
        m_targetPoseInputs[1]->value(),
        m_targetPoseInputs[2]->value());
}

QQuaternion UIControl::targetOrientation() const
{
    if (m_targetPoseInputs.size() < 6) {
        return QQuaternion();
    }

    double roll = m_targetPoseInputs[3]->value() * M_PI / 180.0;
    double pitch = m_targetPoseInputs[4]->value() * M_PI / 180.0;
    double yaw = m_targetPoseInputs[5]->value() * M_PI / 180.0;

    QQuaternion qRoll = QQuaternion::fromAxisAndAngle(QVector3D(1, 0, 0), roll * 180.0 / M_PI);
    QQuaternion qPitch = QQuaternion::fromAxisAndAngle(QVector3D(0, 1, 0), pitch * 180.0 / M_PI);
    QQuaternion qYaw = QQuaternion::fromAxisAndAngle(QVector3D(0, 0, 1), yaw * 180.0 / M_PI);

    return (qYaw * qPitch * qRoll).normalized();
}

void UIControl::onJointSliderChanged(int index, int value)
{
    double degValue = value / 100.0;
    m_jointValues[index] = degValue;

    m_jointSpinBoxes[index]->blockSignals(true);
    m_jointSpinBoxes[index]->setValue(degValue);
    m_jointSpinBoxes[index]->blockSignals(false);

    emit jointValueChanged(index, degValue);
}

void UIControl::onJointSpinBoxChanged(int index, double value)
{
    m_jointValues[index] = value;

    int sliderValue = static_cast<int>(value * 100.0);
    m_jointSliders[index]->blockSignals(true);
    m_jointSliders[index]->setValue(sliderValue);
    m_jointSliders[index]->blockSignals(false);

    emit jointValueChanged(index, value);
}

void UIControl::onTargetPoseChanged()
{
    emit targetPoseChanged(targetPosition(), targetOrientation());
}

void UIControl::updateJointDisplay(int index)
{
    if (index < 0 || index >= m_numJoints) {
        return;
    }

    double value = m_jointValues[index];
    int sliderValue = static_cast<int>(value * 100.0);

    m_jointSliders[index]->blockSignals(true);
    m_jointSpinBoxes[index]->blockSignals(true);

    m_jointSliders[index]->setValue(sliderValue);
    m_jointSpinBoxes[index]->setValue(value);

    m_jointSliders[index]->blockSignals(false);
    m_jointSpinBoxes[index]->blockSignals(false);
}
