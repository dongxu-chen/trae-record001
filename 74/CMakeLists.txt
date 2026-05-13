cmake_minimum_required(VERSION 3.14)

project(RobotKinematics VERSION 1.0 LANGUAGES CXX)

set(CMAKE_AUTOUIC ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS
    Core
    Gui
    Widgets
    3DCore
    3DRender
    3DInput
    3DExtras
    3DAnimation
)

add_executable(RobotKinematics
    main.cpp
    robot_widget.cpp
    robot_widget.h
    joint.cpp
    joint.h
    kinematics.cpp
    kinematics.h
    trajectory.cpp
    trajectory.h
    collision_checker.cpp
    collision_checker.h
    planning.cpp
    planning.h
    ui_control.cpp
    ui_control.h
)

target_link_libraries(RobotKinematics PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Widgets
    Qt6::3DCore
    Qt6::3DRender
    Qt6::3DInput
    Qt6::3DExtras
    Qt6::3DAnimation
)
