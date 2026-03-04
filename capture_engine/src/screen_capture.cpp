/**
 * @file screen_capture.cpp
 * @brief Common ScreenCapture utilities and factory.
 */

#include "screen_capture.h"
#include <iostream>

namespace anilog {

// Forward declarations for platform-specific implementations
#ifdef _WIN32
class ScreenCaptureWin;
std::unique_ptr<ScreenCapture> create_win_capture();
#elif __linux__
class ScreenCaptureX11;
std::unique_ptr<ScreenCapture> create_x11_capture();
#elif __APPLE__
class ScreenCaptureMac;
std::unique_ptr<ScreenCapture> create_mac_capture();
#endif

std::unique_ptr<ScreenCapture> ScreenCapture::create() {
#ifdef _WIN32
    return create_win_capture();
#elif __linux__
    return create_x11_capture();
#elif __APPLE__
    return create_mac_capture();
#else
    std::cerr << "[AniLog] Unsupported platform for screen capture" << std::endl;
    return nullptr;
#endif
}

} // namespace anilog
