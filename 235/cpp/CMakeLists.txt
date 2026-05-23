cmake_minimum_required(VERSION 3.15)
project(ESPCN)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(OpenCV REQUIRED)

set(ONNXRUNTIME_DIR "" CACHE PATH "Path to ONNX Runtime directory")

if(NOT ONNXRUNTIME_DIR)
    message(FATAL_ERROR "Please set ONNXRUNTIME_DIR to the path of your ONNX Runtime installation")
endif()

include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${OpenCV_INCLUDE_DIRS}
    ${ONNXRUNTIME_DIR}/include
)

link_directories(
    ${ONNXRUNTIME_DIR}/lib
)

set(SOURCES
    src/ESPCN.cpp
    src/main.cpp
)

add_executable(espcn_infer ${SOURCES})

target_link_libraries(espcn_infer
    ${OpenCV_LIBS}
    onnxruntime
)

if(WIN32)
    add_custom_command(TARGET espcn_infer POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${ONNXRUNTIME_DIR}/bin/onnxruntime.dll"
        $<TARGET_FILE_DIR:espcn_infer>
    )
endif()

install(TARGETS espcn_infer DESTINATION bin)
