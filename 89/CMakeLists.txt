cmake_minimum_required(VERSION 3.10)
project(static_file_server)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(MSVC)
    add_compile_options(/W4)
else()
    add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(Boost REQUIRED COMPONENTS system filesystem)
find_package(OpenSSL REQUIRED)

include_directories(${Boost_INCLUDE_DIRS})
include_directories(${OPENSSL_INCLUDE_DIR})

add_executable(static_file_server
    server.cpp
    router.cpp
    file_handler.cpp
    mime_types.cpp
    cache_control.cpp
    compression.cpp
)

target_link_libraries(static_file_server
    ${Boost_LIBRARIES}
    ${OPENSSL_LIBRARIES}
)

if(WIN32)
    target_link_libraries(static_file_server ws2_32 mswsock crypt32)
endif()

if(UNIX)
    target_link_libraries(static_file_server pthread dl)
endif()
