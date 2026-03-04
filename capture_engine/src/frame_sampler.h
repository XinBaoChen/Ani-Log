/**
 * @file frame_sampler.h
 * @brief Intelligent frame sampling engine.
 *
 * Manages frame rate reduction and scene-change-aware sampling
 * to minimize unnecessary processing while capturing all important moments.
 */

#pragma once

#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>
#include <chrono>
#include <functional>

namespace anilog {

/// Frame sampling configuration
struct SamplerConfig {
    int target_fps = 2;                  ///< Target analysis FPS
    double scene_threshold = 0.4;        ///< Scene change sensitivity (0-1)
    bool adaptive = true;                ///< Enable adaptive sampling
    int min_scene_frames = 3;            ///< Min frames per scene
    cv::Size analysis_size = {640, 360}; ///< Resize for analysis
};

/// Result of a sampling decision
struct SampleResult {
    bool should_process;     ///< Whether this frame should be analyzed
    bool scene_changed;      ///< Whether a scene change was detected
    double scene_score;      ///< Scene change confidence score
    cv::Mat processed_frame; ///< Resized frame ready for analysis
    double timestamp;        ///< Frame timestamp in seconds
};

/**
 * @class FrameSampler
 * @brief Decides which frames to send to the vision pipeline.
 *
 * Uses histogram comparison and structural difference to detect
 * scene changes and adaptively adjust sampling rate.
 */
class FrameSampler {
public:
    explicit FrameSampler(const SamplerConfig& config = {});

    /**
     * Process a captured frame and decide whether to analyze it.
     * @param frame Raw captured frame (BGR)
     * @param timestamp Current timestamp
     * @return SampleResult with decision and processed frame
     */
    SampleResult process(const cv::Mat& frame, double timestamp);

    /**
     * Reset state (for new sessions).
     */
    void reset();

    /**
     * Get total number of sampled frames.
     */
    int sampled_count() const { return sampled_count_; }

    /**
     * Get total number of scene changes detected.
     */
    int scene_change_count() const { return scene_changes_; }

private:
    SamplerConfig config_;

    cv::Mat prev_gray_;
    cv::Mat prev_hist_;
    double last_sample_time_ = -1.0;
    int sampled_count_ = 0;
    int scene_changes_ = 0;
    int frames_since_scene_ = 0;

    /**
     * Compute scene change score between current and previous frame.
     */
    double compute_scene_score(const cv::Mat& gray);

    /**
     * Resize frame to analysis dimensions.
     */
    cv::Mat resize_for_analysis(const cv::Mat& frame);
};

} // namespace anilog
