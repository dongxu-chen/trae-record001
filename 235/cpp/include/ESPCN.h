#ifndef ESPCN_H
#define ESPCN_H

#include <string>
#include <vector>
#include <memory>
#include <unordered_map>
#include <mutex>
#include <opencv2/opencv.hpp>
#include <onnxruntime_cxx_api.h>

class AlignedBuffer {
public:
    AlignedBuffer(size_t size, size_t alignment = 64);
    ~AlignedBuffer();
    
    void* data() const { return data_; }
    size_t size() const { return size_; }
    size_t alignment() const { return alignment_; }
    
    void resize(size_t new_size);
    
private:
    void* data_;
    void* raw_data_;
    size_t size_;
    size_t alignment_;
};

class MemoryPool {
public:
    MemoryPool(size_t alignment = 64);
    ~MemoryPool();
    
    std::shared_ptr<AlignedBuffer> acquire(size_t size);
    void release(std::shared_ptr<AlignedBuffer> buffer);
    void clear();
    
private:
    std::vector<std::shared_ptr<AlignedBuffer>> free_buffers_;
    size_t alignment_;
    std::mutex mutex_;
};

class ESPCN {
public:
    ESPCN(const std::string& model_path, int scale_factor, bool use_gpu = false);
    ~ESPCN();
    
    cv::Mat super_resolve(const cv::Mat& input_image);
    
    std::vector<cv::Mat> super_resolve_batch(const std::vector<cv::Mat>& input_images);
    
    int get_scale_factor() const { return scale_factor_; }
    
private:
    void initialize_session(const std::string& model_path, bool use_gpu);
    void preprocess(const cv::Mat& image, float* output_buffer);
    cv::Mat postprocess(const float* input_buffer, int input_height, int input_width);
    
    void ensure_buffer_size(size_t required_size, std::shared_ptr<AlignedBuffer>& buffer);
    
    std::unique_ptr<Ort::Session> session_;
    std::unique_ptr<Ort::Env> env_;
    Ort::MemoryInfo memory_info_;
    
    std::vector<const char*> input_names_;
    std::vector<const char*> output_names_;
    
    int scale_factor_;
    int input_channels_;
    
    std::unique_ptr<MemoryPool> memory_pool_;
    std::shared_ptr<AlignedBuffer> input_buffer_;
    std::shared_ptr<AlignedBuffer> output_buffer_;
    size_t current_input_size_;
    size_t current_output_size_;
};

#endif
