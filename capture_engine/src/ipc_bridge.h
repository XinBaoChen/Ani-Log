/**
 * @file ipc_bridge.h
 * @brief ZeroMQ IPC bridge between C++ capture engine and Python backend.
 *
 * Sends captured frames to the Python vision pipeline and receives
 * detection results back.
 */

#pragma once

#include <opencv2/core.hpp>
#include <zmq.h>
#include <string>
#include <functional>
#include <atomic>

namespace anilog {

/// Frame message sent from C++ to Python
struct FrameMessage {
    int frame_index;
    double timestamp;
    int width;
    int height;
    int channels;
    // Followed by raw pixel data
};

/// Detection result received from Python
struct DetectionResult {
    int frame_index;
    int num_detections;
    bool scene_changed;
    // Followed by detection data
};

/**
 * @class IPCBridge
 * @brief ZeroMQ-based IPC between C++ capture and Python processing.
 */
class IPCBridge {
public:
    IPCBridge();
    ~IPCBridge();

    /**
     * Initialize ZeroMQ sockets.
     * @param send_port Port for sending frames to Python
     * @param recv_port Port for receiving results from Python
     * @return true on success
     */
    bool initialize(int send_port = 5555, int recv_port = 5556);

    /**
     * Send a captured frame to the Python backend.
     * @param frame BGR cv::Mat
     * @param frame_index Sequential frame number
     * @param timestamp Frame timestamp in seconds
     * @return true on success
     */
    bool send_frame(const cv::Mat& frame, int frame_index, double timestamp);

    /**
     * Check for detection results (non-blocking).
     * @param callback Called with result data if available
     * @return true if a result was received
     */
    bool poll_results(std::function<void(const DetectionResult&)> callback);

    /**
     * Clean shutdown.
     */
    void shutdown();

    bool is_connected() const { return connected_; }

private:
    void* zmq_context_ = nullptr;
    void* send_socket_ = nullptr;
    void* recv_socket_ = nullptr;
    std::atomic<bool> connected_{false};
};

} // namespace anilog
