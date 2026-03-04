/**
 * @file ipc_bridge.cpp
 * @brief ZeroMQ IPC bridge implementation.
 */

#include "ipc_bridge.h"
#include <opencv2/imgcodecs.hpp>
#include <iostream>
#include <cstring>
#include <vector>

namespace anilog {

IPCBridge::IPCBridge() = default;

IPCBridge::~IPCBridge() {
    shutdown();
}

bool IPCBridge::initialize(int send_port, int recv_port) {
    zmq_context_ = zmq_ctx_new();
    if (!zmq_context_) {
        std::cerr << "[AniLog IPC] Failed to create ZMQ context" << std::endl;
        return false;
    }

    // PUSH socket for sending frames
    send_socket_ = zmq_socket(zmq_context_, ZMQ_PUSH);
    std::string send_addr = "tcp://127.0.0.1:" + std::to_string(send_port);
    if (zmq_connect(send_socket_, send_addr.c_str()) != 0) {
        std::cerr << "[AniLog IPC] Failed to connect send socket to " << send_addr << std::endl;
        return false;
    }

    // Set send high water mark (drop if Python can't keep up)
    int hwm = 5;
    zmq_setsockopt(send_socket_, ZMQ_SNDHWM, &hwm, sizeof(hwm));

    // SUB socket for receiving results
    recv_socket_ = zmq_socket(zmq_context_, ZMQ_SUB);
    std::string recv_addr = "tcp://127.0.0.1:" + std::to_string(recv_port);
    if (zmq_connect(recv_socket_, recv_addr.c_str()) != 0) {
        std::cerr << "[AniLog IPC] Failed to connect recv socket to " << recv_addr << std::endl;
        return false;
    }
    zmq_setsockopt(recv_socket_, ZMQ_SUBSCRIBE, "", 0);

    connected_ = true;
    std::cout << "[AniLog IPC] Connected: send=" << send_addr
              << " recv=" << recv_addr << std::endl;

    return true;
}

bool IPCBridge::send_frame(const cv::Mat& frame, int frame_index, double timestamp) {
    if (!connected_ || !send_socket_) return false;

    // Encode frame as JPEG for efficient transfer
    std::vector<uchar> buffer;
    std::vector<int> params = {cv::IMWRITE_JPEG_QUALITY, 85};
    cv::imencode(".jpg", frame, buffer, params);

    // Build message: header + image data
    FrameMessage header;
    header.frame_index = frame_index;
    header.timestamp = timestamp;
    header.width = frame.cols;
    header.height = frame.rows;
    header.channels = frame.channels();

    // Send header (part 1)
    zmq_msg_t header_msg;
    zmq_msg_init_size(&header_msg, sizeof(FrameMessage));
    memcpy(zmq_msg_data(&header_msg), &header, sizeof(FrameMessage));
    zmq_msg_send(&header_msg, send_socket_, ZMQ_SNDMORE);
    zmq_msg_close(&header_msg);

    // Send image data (part 2)
    zmq_msg_t data_msg;
    zmq_msg_init_size(&data_msg, buffer.size());
    memcpy(zmq_msg_data(&data_msg), buffer.data(), buffer.size());
    int rc = zmq_msg_send(&data_msg, send_socket_, ZMQ_DONTWAIT);
    zmq_msg_close(&data_msg);

    return rc >= 0;
}

bool IPCBridge::poll_results(std::function<void(const DetectionResult&)> callback) {
    if (!connected_ || !recv_socket_) return false;

    zmq_pollitem_t poll_item = {recv_socket_, 0, ZMQ_POLLIN, 0};
    int rc = zmq_poll(&poll_item, 1, 0); // Non-blocking

    if (rc > 0 && (poll_item.revents & ZMQ_POLLIN)) {
        zmq_msg_t msg;
        zmq_msg_init(&msg);

        if (zmq_msg_recv(&msg, recv_socket_, ZMQ_DONTWAIT) >= 0) {
            if (zmq_msg_size(&msg) >= sizeof(DetectionResult)) {
                DetectionResult result;
                memcpy(&result, zmq_msg_data(&msg), sizeof(DetectionResult));
                callback(result);
            }
        }

        zmq_msg_close(&msg);
        return true;
    }

    return false;
}

void IPCBridge::shutdown() {
    connected_ = false;

    if (send_socket_) {
        zmq_close(send_socket_);
        send_socket_ = nullptr;
    }
    if (recv_socket_) {
        zmq_close(recv_socket_);
        recv_socket_ = nullptr;
    }
    if (zmq_context_) {
        zmq_ctx_destroy(zmq_context_);
        zmq_context_ = nullptr;
    }
}

} // namespace anilog
