/**
 * @file screen_capture.h
 * @brief Platform-agnostic screen capture interface.
 *
 * Provides a unified API for grabbing screen frames across
 * Windows (DirectX/DXGI), Linux (X11), and macOS (CoreGraphics).
 */

#pragma once

#include <opencv2/core.hpp>
#include <memory>
#include <string>
#include <optional>

namespace anilog {

/// Capture source type
enum class CaptureSource {
    FullScreen,  ///< Capture entire primary monitor
    Window,      ///< Capture specific window by title
    Region       ///< Capture a screen region
};

/// Rectangular region for capture
struct CaptureRegion {
    int x = 0;
    int y = 0;
    int width = 0;
    int height = 0;
};

/// Configuration for the screen capture engine
struct CaptureConfig {
    CaptureSource source = CaptureSource::FullScreen;
    std::string window_title;     ///< For Window mode
    CaptureRegion region;         ///< For Region mode
    int monitor_index = 0;        ///< Which monitor to capture
    bool include_cursor = false;  ///< Include mouse cursor in capture
};

/**
 * @class ScreenCapture
 * @brief Abstract base class for platform-specific screen capture.
 */
class ScreenCapture {
public:
    virtual ~ScreenCapture() = default;

    /**
     * Initialize the capture engine.
     * @param config Capture configuration
     * @return true on success
     */
    virtual bool initialize(const CaptureConfig& config) = 0;

    /**
     * Grab a single frame from the screen.
     * @return Captured frame as BGR cv::Mat, or empty Mat on failure
     */
    virtual cv::Mat grab_frame() = 0;

    /**
     * Get the native resolution of the capture source.
     */
    virtual cv::Size get_resolution() const = 0;

    /**
     * Check if the capture engine is initialized and ready.
     */
    virtual bool is_ready() const = 0;

    /**
     * Release capture resources.
     */
    virtual void release() = 0;

    /**
     * Factory method: create platform-appropriate capture instance.
     */
    static std::unique_ptr<ScreenCapture> create();
};

} // namespace anilog
