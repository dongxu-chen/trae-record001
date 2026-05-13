#ifndef UI_CONTROL_H
#define UI_CONTROL_H

#include <QWidget>
#include <QVector>
#include <QSlider>
#include <QLabel>
#include <QGroupBox>
#include <QDoubleSpinBox>
#include <QPushButton>
#include <QProgressBar>

class UIControl : public QWidget {
    Q_OBJECT
public:
    explicit UIControl(int numJoints = 6, QWidget* parent = nullptr);

    void setJointValues(const QVector<double>& values);
    QVector<double> jointValues() const { return m_jointValues; }

    void setTargetPose(const QVector3D& pos, const QQuaternion& orient);
    QVector3D targetPosition() const;
    QQuaternion targetOrientation() const;

    void setProgress(int value) { m_progressBar->setValue(value); }
    void setPlayEnabled(bool enabled) { m_playBtn->setEnabled(enabled); }
    void setStopEnabled(bool enabled) { m_stopBtn->setEnabled(enabled); }
    void setResetEnabled(bool enabled) { m_resetBtn->setEnabled(enabled); }

signals:
    void jointValueChanged(int index, double value);
    void playClicked();
    void stopClicked();
    void resetClicked();
    void planAndPlayClicked();
    void targetPoseChanged(const QVector3D& pos, const QQuaternion& orient);

private slots:
    void onJointSliderChanged(int index, int value);
    void onJointSpinBoxChanged(int index, double value);
    void onTargetPoseChanged();

private:
    int m_numJoints;
    QVector<double> m_jointValues;

    QVector<QSlider*> m_jointSliders;
    QVector<QLabel*> m_jointLabels;
    QVector<QDoubleSpinBox*> m_jointSpinBoxes;
    QVector<QDoubleSpinBox*> m_targetPoseInputs;

    QPushButton* m_playBtn;
    QPushButton* m_stopBtn;
    QPushButton* m_resetBtn;
    QPushButton* m_planBtn;
    QProgressBar* m_progressBar;

    void createJointControls(QVBoxLayout* layout);
    void createTargetPoseControls(QVBoxLayout* layout);
    void createTrajectoryControls(QVBoxLayout* layout);
    void updateJointDisplay(int index);
};

#endif
