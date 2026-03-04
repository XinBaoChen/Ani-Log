/**
 * @file main.cpp
 * @brief Ani-Log Capture Engine — main entry point.
 *
 * Captures screen frames, samples intelligently, and sends
 * to the Python vision pipeline via ZeroMQ.
 *
 * Usage:
 *   anilog_capture [--fps N] [--port N] [--monitor N] [--window "title"]
 */

#include "screen_capture.h"
#include "frame_sampler.h"
#include "ipc_bridge.h"

#include <iostream>
#include <chrono>
#include <thread>
#include <csignal>
#include <string>
#include <atomic>

std::atomic<bool> g_running{true};

void signal_handler(int) {
    g_running = false;
}

void print_usage() {
    std::cout << R"(
╔═══════════════════════════════════════════════════════╗
║        🎌 Ani-Log Capture Engine v0.1.0              ║
║        Autonomous Scene Contextualizer               ║
╚═══════════════════════════════════════════════════════╝

Usage: anilog_capture [options]

Options:
  --fps N          Target sampling FPS (default: 2)
  --port N         ZeroMQ send port (default: 5555)
  --result-port N  ZeroMQ result port (default: 5556)
  --monitor N      Monitor index (default: 0)
  --window "title" Capture specific window
  --threshold F    Scene change threshold (default: 0.4)
  --help           Show this help

)" << std::endl;
}

struct Options {
    int fps = 2;
    int send_port = 5555;
    int recv_port = 5556;
    int monitor = 0;
    std::string window_title;
    double scene_threshold = 0.4;
};

Options parse_args(int argc, char** argv) {
    Options opts;

    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];

        if (arg == "--help") {
            print_usage();
            exit(0);
        } else if (arg == "--fps" && i + 1 < argc) {
            opts.fps = std::stoi(argv[++i]);
        } else if (arg == "--port" && i + 1 < argc) {
            opts.send_port = std::stoi(argv[++i]);
        } else if (arg == "--result-port" && i + 1 < argc) {
            opts.recv_port = std::stoi(argv[++i]);
        } else if (arg == "--monitor" && i + 1 < argc) {
            opts.monitor = std::stoi(argv[++i]);
        } else if (arg == "--window" && i + 1 < argc) {
            opts.window_title = argv[++i];
        } else if (arg == "--threshold" && i + 1 < argc) {
            opts.scene_threshold = std::stod(argv[++i]);
        }
    }

    return opts;
}

int main(int argc, char** argv) {
    // Handle Ctrl+C gracefully
    std::signal(SIGINT, signal_handler);
    std::signal(SIGTERM, signal_handler);

    Options opts = parse_args(argc, argv);

    std::cout << "\n🎌 Ani-Log Capture Engine starting..." << std::endl;
    std::cout << "   FPS: " << opts.fps << std::endl;
    std::cout << "   ZMQ Send Port: " << opts.send_port << std::endl;
    std::cout << "   ZMQ Recv Port: " << opts.recv_port << std::endl;
    std::cout << "   Scene Threshold: " << opts.scene_threshold << std::endl;

    // ─── Initialize Screen Capture ──────────────────────────
    auto capture = anilog::ScreenCapture::create();
    if (!capture) {
        std::cerr << "Failed to create screen capture" << std::endl;
        return 1;
    }

    anilog::CaptureConfig cap_config;
    cap_config.monitor_index = opts.monitor;

    if (!opts.window_title.empty()) {
        cap_config.source = anilog::CaptureSource::Window;
        cap_config.window_title = opts.window_title;
        std::cout << "   Capturing window: \"" << opts.window_title << "\"" << std::endl;
    }

    if (!capture->initialize(cap_config)) {
        std::cerr << "Failed to initialize screen capture" << std::endl;
        return 1;
    }

    auto resolution = capture->get_resolution();
    std::cout << "   Resolution: " << resolution.width << "x" << resolution.height << std::endl;

    // ─── Initialize Frame Sampler ───────────────────────────
    anilog::SamplerConfig sampler_config;
    sampler_config.target_fps = opts.fps;
    sampler_config.scene_threshold = opts.scene_threshold;
    anilog::FrameSampler sampler(sampler_config);

    // ─── Initialize IPC Bridge ──────────────────────────────
    anilog::IPCBridge ipc;
    if (!ipc.initialize(opts.send_port, opts.recv_port)) {
        std::cerr << "Failed to initialize IPC bridge" << std::endl;
        std::cerr << "Make sure the Python backend is running" << std::endl;
        return 1;
    }

    // ─── Main Capture Loop ──────────────────────────────────
    std::cout << "\n✅ Capture running. Press Ctrl+C to stop.\n" << std::endl;

    auto start_time = std::chrono::steady_clock::now();
    int total_frames = 0;
    int sent_frames = 0;
    int detections_received = 0;

    double capture_interval = 1.0 / 30.0; // Capture at ~30 FPS internally

    while (g_running) {
        auto loop_start = std::chrono::steady_clock::now();

        // Calculate timestamp
        auto elapsed = std::chrono::duration<double>(loop_start - start_time);
        double timestamp = elapsed.count();

        // Grab frame
        cv::Mat frame = capture->grab_frame();
        if (frame.empty()) {
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
            continue;
        }
        total_frames++;

        // Run through sampler
        auto sample = sampler.process(frame, timestamp);

        if (sample.should_process) {
            // Send to Python
            if (ipc.send_frame(sample.processed_frame, total_frames, timestamp)) {
                sent_frames++;
            }

            if (sample.scene_changed) {
                std::cout << "🎬 Scene change #" << sampler.scene_change_count()
                          << " at " << std::fixed << std::setprecision(1)
                          << timestamp << "s" << std::endl;
            }
        }

        // Poll for results from Python
        ipc.poll_results([&](const anilog::DetectionResult& result) {
            detections_received += result.num_detections;
        });

        // Print stats periodically
        if (total_frames % 300 == 0) {
            std::cout << "📊 Captured: " << total_frames
                      << " | Sampled: " << sent_frames
                      << " | Scenes: " << sampler.scene_change_count()
                      << " | Detections: " << detections_received
                      << " | Time: " << std::fixed << std::setprecision(1)
                      << timestamp << "s" << std::endl;
        }

        // Maintain capture rate
        auto loop_end = std::chrono::steady_clock::now();
        double loop_time = std::chrono::duration<double>(loop_end - loop_start).count();
        double sleep_time = capture_interval - loop_time;

        if (sleep_time > 0) {
            std::this_thread::sleep_for(
                std::chrono::microseconds(static_cast<int>(sleep_time * 1e6))
            );
        }
    }

    // ─── Cleanup ────────────────────────────────────────────
    std::cout << "\n🛑 Shutting down..." << std::endl;
    std::cout << "   Total frames captured: " << total_frames << std::endl;
    std::cout << "   Frames sent to pipeline: " << sent_frames << std::endl;
    std::cout << "   Scene changes detected: " << sampler.scene_change_count() << std::endl;
    std::cout << "   Detections received: " << detections_received << std::endl;

    ipc.shutdown();
    capture->release();

    std::cout << "👋 Goodbye!" << std::endl;

    return 0;
}
