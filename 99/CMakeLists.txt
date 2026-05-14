cmake_minimum_required(VERSION 3.16)

project(ChartEditor VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 COMPONENTS 
    Core 
    Gui 
    Qml 
    Quick 
    QuickControls2 
    Svg
    PrintSupport
    REQUIRED
)

qt_standard_project_setup()

set(PROJECT_SOURCES
    main.cpp
    ChartModel.cpp
    ChartModel.h
    ChartPluginManager.cpp
    ChartPluginManager.h
    Exporter.cpp
    Exporter.h
    LiveDataGenerator.cpp
    LiveDataGenerator.h
    plugin_interface.h
)

qt_add_executable(ChartEditor
    ${PROJECT_SOURCES}
)

qt_add_qml_module(ChartEditor
    URI ChartEditor
    VERSION 1.0
    QML_FILES
        ChartView.qml
    NO_RESOURCE_TARGET_PATH
)

target_link_libraries(ChartEditor
    PRIVATE
        Qt6::Core
        Qt6::Gui
        Qt6::Qml
        Qt6::Quick
        Qt6::QuickControls2
        Qt6::Svg
        Qt6::PrintSupport
)

if(WIN32)
    set_target_properties(ChartEditor PROPERTIES
        WIN32_EXECUTABLE TRUE
    )
endif()

install(TARGETS ChartEditor
    BUNDLE DESTINATION .
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)
