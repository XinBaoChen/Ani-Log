/**
 * @file screen_capture_win.cpp
 * @brief Windows screen capture using DXGI Desktop Duplication API.
 *
 * This provides low-latency, GPU-accelerated screen capture on Windows 8+.
 * Falls back to GDI BitBlt for older systems.
 */

#ifdef _WIN32

#include "screen_capture.h"

#include <d3d11.h>
#include <dxgi1_2.h>
#include <wrl/client.h>
#include <iostream>

#pragma comment(lib, "d3d11.lib")
#pragma comment(lib, "dxgi.lib")

using Microsoft::WRL::ComPtr;

namespace anilog {

class ScreenCaptureWin : public ScreenCapture {
public:
    ScreenCaptureWin() = default;
    ~ScreenCaptureWin() override { release(); }

    bool initialize(const CaptureConfig& config) override {
        config_ = config;

        // Create D3D11 device
        D3D_FEATURE_LEVEL feature_level;
        HRESULT hr = D3D11CreateDevice(
            nullptr,
            D3D_DRIVER_TYPE_HARDWARE,
            nullptr,
            0,
            nullptr, 0,
            D3D11_SDK_VERSION,
            &device_,
            &feature_level,
            &context_
        );

        if (FAILED(hr)) {
            std::cerr << "[AniLog] Failed to create D3D11 device" << std::endl;
            return false;
        }

        // Get DXGI device
        ComPtr<IDXGIDevice> dxgi_device;
        device_.As(&dxgi_device);

        ComPtr<IDXGIAdapter> adapter;
        dxgi_device->GetAdapter(&adapter);

        // Get output (monitor)
        ComPtr<IDXGIOutput> output;
        hr = adapter->EnumOutputs(config.monitor_index, &output);
        if (FAILED(hr)) {
            std::cerr << "[AniLog] Failed to get monitor output" << std::endl;
            return false;
        }

        ComPtr<IDXGIOutput1> output1;
        output.As(&output1);

        // Create desktop duplication
        hr = output1->DuplicateOutput(device_.Get(), &duplication_);
        if (FAILED(hr)) {
            std::cerr << "[AniLog] Failed to create desktop duplication" << std::endl;
            return false;
        }

        // Get output description for resolution
        DXGI_OUTPUT_DESC desc;
        output->GetDesc(&desc);
        width_ = desc.DesktopCoordinates.right - desc.DesktopCoordinates.left;
        height_ = desc.DesktopCoordinates.bottom - desc.DesktopCoordinates.top;

        ready_ = true;
        std::cout << "[AniLog] DXGI capture initialized: "
                  << width_ << "x" << height_ << std::endl;

        return true;
    }

    cv::Mat grab_frame() override {
        if (!ready_ || !duplication_) return {};

        ComPtr<IDXGIResource> resource;
        DXGI_OUTDUPL_FRAME_INFO frame_info;

        HRESULT hr = duplication_->AcquireNextFrame(100, &frame_info, &resource);

        if (hr == DXGI_ERROR_WAIT_TIMEOUT) {
            return last_frame_.clone(); // Return last frame on timeout
        }

        if (FAILED(hr)) {
            // Attempt recovery
            if (hr == DXGI_ERROR_ACCESS_LOST) {
                release();
                initialize(config_);
            }
            return {};
        }

        // Get texture
        ComPtr<ID3D11Texture2D> texture;
        resource.As(&texture);

        // Create staging texture for CPU access
        D3D11_TEXTURE2D_DESC desc;
        texture->GetDesc(&desc);
        desc.Usage = D3D11_USAGE_STAGING;
        desc.BindFlags = 0;
        desc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
        desc.MiscFlags = 0;

        ComPtr<ID3D11Texture2D> staging;
        device_->CreateTexture2D(&desc, nullptr, &staging);
        context_->CopyResource(staging.Get(), texture.Get());

        // Map to CPU memory
        D3D11_MAPPED_SUBRESOURCE mapped;
        context_->Map(staging.Get(), 0, D3D11_MAP_READ, 0, &mapped);

        // Copy to cv::Mat (BGRA → BGR)
        cv::Mat bgra(height_, width_, CV_8UC4, mapped.pData, mapped.RowPitch);
        cv::Mat bgr;
        cv::cvtColor(bgra, bgr, cv::COLOR_BGRA2BGR);

        context_->Unmap(staging.Get(), 0);
        duplication_->ReleaseFrame();

        last_frame_ = bgr.clone();
        return bgr;
    }

    cv::Size get_resolution() const override {
        return { width_, height_ };
    }

    bool is_ready() const override { return ready_; }

    void release() override {
        duplication_.Reset();
        context_.Reset();
        device_.Reset();
        ready_ = false;
    }

private:
    CaptureConfig config_;
    ComPtr<ID3D11Device> device_;
    ComPtr<ID3D11DeviceContext> context_;
    ComPtr<IDXGIOutputDuplication> duplication_;
    int width_ = 0;
    int height_ = 0;
    bool ready_ = false;
    cv::Mat last_frame_;
};

std::unique_ptr<ScreenCapture> create_win_capture() {
    return std::make_unique<ScreenCaptureWin>();
}

} // namespace anilog

#endif // _WIN32
