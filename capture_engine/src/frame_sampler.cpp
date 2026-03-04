/**
 * @file frame_sampler.cpp
 * @brief Frame sampling implementation.
 */

#include "frame_sampler.h"
#include <opencv2/imgproc.hpp>
#include <iostream>

namespace anilog {

FrameSampler::FrameSampler(const SamplerConfig& config) : config_(config) {}

SampleResult FrameSampler::process(const cv::Mat& frame, double timestamp) {
    SampleResult result;
    result.timestamp = timestamp;
    result.should_process = false;
    result.scene_changed = false;
    result.scene_score = 0.0;

    if (frame.empty()) return result;

    // Convert to grayscale for comparison
    cv::Mat gray;
    cv::cvtColor(frame, gray, cv::COLOR_BGR2GRAY);

    // Check scene change
    double scene_score = compute_scene_score(gray);
    result.scene_score = scene_score;

    bool scene_changed = scene_score > config_.scene_threshold;
    result.scene_changed = scene_changed;

    if (scene_changed) {
        scene_changes_++;
        frames_since_scene_ = 0;
    } else {
        frames_since_scene_++;
    }

    // Decide whether to sample this frame
    double interval = 1.0 / config_.target_fps;
    bool time_triggered = (last_sample_time_ < 0) ||
                          (timestamp - last_sample_time_ >= interval);

    if (scene_changed || time_triggered) {
        result.should_process = true;
        result.processed_frame = resize_for_analysis(frame);
        last_sample_time_ = timestamp;
        sampled_count_++;
    }

    // Adaptive: sample more densely right after scene change
    if (config_.adaptive && scene_changed) {
        // Force next few frames to be sampled
        last_sample_time_ = timestamp - interval * 0.8;
    }

    // Store current frame for next comparison
    prev_gray_ = gray.clone();

    return result;
}

double FrameSampler::compute_scene_score(const cv::Mat& gray) {
    if (prev_gray_.empty()) {
        // First frame — compute histogram and return
        int channels[] = {0};
        int hist_size[] = {256};
        float range[] = {0, 256};
        const float* ranges[] = {range};
        cv::calcHist(&gray, 1, channels, {}, prev_hist_, 1, hist_size, ranges);
        cv::normalize(prev_hist_, prev_hist_);
        return 1.0;  // First frame is always a "scene change"
    }

    // Compute current histogram
    cv::Mat curr_hist;
    int channels[] = {0};
    int hist_size[] = {256};
    float range[] = {0, 256};
    const float* ranges[] = {range};
    cv::calcHist(&gray, 1, channels, {}, curr_hist, 1, hist_size, ranges);
    cv::normalize(curr_hist, curr_hist);

    // Histogram correlation (1.0 = identical, -1.0 = inverse)
    double hist_corr = cv::compareHist(prev_hist_, curr_hist, cv::HISTCMP_CORREL);

    // Structural difference
    cv::Mat small_prev, small_curr;
    cv::resize(prev_gray_, small_prev, cv::Size(160, 90));
    cv::resize(gray, small_curr, cv::Size(160, 90));

    cv::Mat diff;
    cv::absdiff(small_prev, small_curr, diff);
    double struct_diff = cv::mean(diff)[0] / 255.0;

    // Update stored histogram
    prev_hist_ = curr_hist.clone();

    // Combined score (higher = more different)
    double combined = 0.6 * (1.0 - hist_corr) + 0.4 * struct_diff;

    return combined;
}

cv::Mat FrameSampler::resize_for_analysis(const cv::Mat& frame) {
    cv::Mat resized;
    cv::resize(frame, resized, config_.analysis_size, 0, 0, cv::INTER_AREA);
    return resized;
}

void FrameSampler::reset() {
    prev_gray_ = {};
    prev_hist_ = {};
    last_sample_time_ = -1.0;
    sampled_count_ = 0;
    scene_changes_ = 0;
    frames_since_scene_ = 0;
}

} // namespace anilog
