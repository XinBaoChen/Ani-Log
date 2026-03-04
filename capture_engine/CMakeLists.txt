cmake_minimum_required(VERSION 3.20)
project(AniLogCapture VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ─── Dependencies ─────────────────────────────────────────────
find_package(OpenCV REQUIRED)

# ZeroMQ
find_package(PkgConfig)
if(PkgConfig_FOUND)
    pkg_check_modules(ZMQ libzmq)
endif()

if(NOT ZMQ_FOUND)
    find_path(ZMQ_INCLUDE_DIRS zmq.h)
    find_library(ZMQ_LIBRARIES zmq)
endif()

# Platform-specific capture libraries
if(WIN32)
    set(PLATFORM_LIBS d3d11 dxgi)
    set(PLATFORM_SOURCES src/screen_capture_win.cpp)
elseif(UNIX AND NOT APPLE)
    find_package(X11 REQUIRED)
    set(PLATFORM_LIBS ${X11_LIBRARIES})
    set(PLATFORM_SOURCES src/screen_capture_x11.cpp)
elseif(APPLE)
    find_library(COREGRAPHICS CoreGraphics)
    find_library(COREFOUNDATION CoreFoundation)
    set(PLATFORM_LIBS ${COREGRAPHICS} ${COREFOUNDATION})
    set(PLATFORM_SOURCES src/screen_capture_mac.cpp)
endif()

# ─── Executable ───────────────────────────────────────────────
add_executable(anilog_capture
    src/main.cpp
    src/screen_capture.cpp
    src/frame_sampler.cpp
    src/ipc_bridge.cpp
    ${PLATFORM_SOURCES}
)

target_include_directories(anilog_capture PRIVATE
    ${OpenCV_INCLUDE_DIRS}
    ${ZMQ_INCLUDE_DIRS}
    src/
)

target_link_libraries(anilog_capture PRIVATE
    ${OpenCV_LIBS}
    ${ZMQ_LIBRARIES}
    ${PLATFORM_LIBS}
)

# ─── Install ──────────────────────────────────────────────────
install(TARGETS anilog_capture DESTINATION bin)
