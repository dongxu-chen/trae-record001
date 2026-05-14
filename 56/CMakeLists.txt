cmake_minimum_required(VERSION 3.20)
project(FilamentMaterialViewer)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

option(FILAMENT_ROOT "Path to Filament SDK directory")

if(NOT FILAMENT_ROOT)
    message(FATAL_ERROR "Please set FILAMENT_ROOT to your Filament installation path")
endif()

set(FILAMENT_INCLUDE_DIRS
    ${FILAMENT_ROOT}/include
    ${FILAMENT_ROOT}/third_party/imgui
    ${FILAMENT_ROOT}/third_party/libgltfio
    ${FILAMENT_ROOT}/third_party/stb
)

set(FILAMENT_LIB_DIRS
    ${FILAMENT_ROOT}/lib
    ${FILAMENT_ROOT}/lib/third_party
)

link_directories(${FILAMENT_LIB_DIRS})

add_executable(MaterialViewer
    src/main.cpp
    src/viewer.cpp
    src/lighting.cpp
    src/ui.cpp
    src/animation.cpp
    src/config_loader.cpp
)

target_include_directories(MaterialViewer PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${FILAMENT_INCLUDE_DIRS}
)

if(WIN32)
    target_link_libraries(MaterialViewer PRIVATE
        filament
        backend
        bluegl
        ibl
        image
        matdbg
        viewer
        filagui
        imgui
        gltfio
        gltfio_core
        gltfio_resources
        utils
        geometry
        math
        cgltf
        stb
    )
else()
    target_link_libraries(MaterialViewer PRIVATE
        filament
        backend
        bluegl
        ibl
        image
        matdbg
        viewer
        filagui
        imgui
        gltfio
        gltfio_core
        gltfio_resources
        utils
        geometry
        math
        cgltf
        stb
    )
endif()

if(WIN32)
    add_custom_command(TARGET MaterialViewer POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_directory
        ${FILAMENT_ROOT}/lib
        $<TARGET_FILE_DIR:MaterialViewer>
    )
endif()
