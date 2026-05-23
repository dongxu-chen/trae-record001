#include "ESPCN.h"
#include <algorithm>
#include <iostream>
#include <cstdlib>
#include <cstring>

AlignedBuffer::AlignedBuffer(size_t size, size_t alignment)
    : size_(size), alignment_(alignment), data_(nullptr), raw_data_(nullptr) {
    resize(size);
}

AlignedBuffer::~AlignedBuffer() {
    if (raw_data_) {
        std::free(raw_data_);
    }
}

void AlignedBuffer::resize(size_t new_size) {
    if (new_size <= size_ && data_) {
        size_ = new_size;
        return;
    }
    
    if (raw_data_) {
        std::free(raw_data_);
    }
    
    size_t allocate_size = new_size + alignment_;
    raw_data_ = std::malloc(allocate_size);
    if (!raw_data_) {
        throw std::bad_alloc();
    }
    
    uintptr_t raw_addr = reinterpret_cast<uintptr_t>(raw_data_);
    uintptr_t aligned_addr = (raw_addr + alignment_ - 1) & ~(alignment_ - 1);
    data_ = reinterpret_cast<void*>(aligned_addr);
    size_ = new_size;
}

MemoryPool::MemoryPool(size_t alignment) : alignment_(alignment) {}

MemoryPool::~MemoryPool() {
    clear();
}

std::shared_ptr<AlignedBuffer> MemoryPool::acquire(size_t size) {
    std::lock_guard<std::mutex> lock(mutex_);
    
    for (auto it = free_buffers_.begin(); it != free_buffers_.end(); ++it) {
        if ((*it)->size() >= size) {
            auto buffer = *it;
            free_buffers_.erase(it);
            return buffer;
        }
    }
    
    return std::make_shared<AlignedBuffer>(size, alignment_);
}

void MemoryPool::release(std::shared_ptr<AlignedBuffer> buffer) {
    if (!buffer) return;
    
    std::lock_guard<std::mutex> lock(mutex_);
    free_buffers_.push_back(buffer);
}

void MemoryPool::clear() {
    std::lock_guard<std::mutex> lock(mutex_);
    free_buffers_.clear();
}

ESPCN::ESPCN(const std::string& model_path, int scale_factor, bool use_gpu)
    : scale_factor_(scale_factor)
    , input_channels_(3)
    , memory_info_(Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault))
    , current_input_size_(0)
    , current_output_size_(0) {
    
    env_ = std::make_unique<Ort::Env>(ORT_LOGGING_LEVEL_WARNING, "ESPCN");
    memory_pool_ = std::make_unique<MemoryPool>(64);
    initialize_session(model_path, use_gpu);
}

ESPCN::~ESPCN() {
    for (auto name : input_names_) {
        delete[] name;
    }
    for (auto name : output_names_) {
        delete[] name;
    }
    
    if (input_buffer_) {
        memory_pool_->release(input_buffer_);
    }
    if (output_buffer_) {
        memory_pool_->release(output_buffer_);
    }
}

void ESPCN::initialize_session(const std::string& model_path, bool use_gpu) {
    Ort::SessionOptions session_options;
    session_options.SetIntraOpNumThreads(1);
    session_options.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);
    
    std::vector<std::string> available_providers = Ort::GetAvailableProviders();
    bool has_cuda = false;
    for (const auto& provider : available_providers) {
        if (provider == "CUDAExecutionProvider") {
            has_cuda = true;
            break;
        }
    }
    
    if (use_gpu && has_cuda) {
        OrtCUDAProviderOptions cuda_options;
        cuda_options.device_id = 0;
        session_options.AppendExecutionProvider_CUDA(cuda_options);
        std::cout << "Using CUDA Execution Provider" << std::endl;
    } else {
        std::cout << "Using CPU Execution Provider" << std::endl;
    }
    
#ifdef _WIN32
    std::wstring wide_model_path(model_path.begin(), model_path.end());
    session_ = std::make_unique<Ort::Session>(*env_, wide_model_path.c_str(), session_options);
#else
    session_ = std::make_unique<Ort::Session>(*env_, model_path.c_str(), session_options);
#endif
    
    Ort::AllocatorWithDefaultOptions allocator;
    
    size_t num_input_nodes = session_->GetInputCount();
    for (size_t i = 0; i < num_input_nodes; i++) {
        char* input_name = session_->GetInputName(i, allocator);
        input_names_.push_back(input_name);
    }
    
    size_t num_output_nodes = session_->GetOutputCount();
    for (size_t i = 0; i < num_output_nodes; i++) {
        char* output_name = session_->GetOutputName(i, allocator);
        output_names_.push_back(output_name);
    }
}

void ESPCN::ensure_buffer_size(size_t required_size, std::shared_ptr<AlignedBuffer>& buffer) {
    if (!buffer || buffer->size() < required_size) {
        if (buffer) {
            memory_pool_->release(buffer);
        }
        buffer = memory_pool_->acquire(required_size);
    }
}

void ESPCN::preprocess(const cv::Mat& image, float* output_buffer) {
    cv::Mat rgb_image;
    if (image.channels() == 3) {
        cv::cvtColor(image, rgb_image, cv::COLOR_BGR2RGB);
    } else if (image.channels() == 1) {
        cv::cvtColor(image, rgb_image, cv::COLOR_GRAY2RGB);
    } else {
        rgb_image = image.clone();
    }
    
    rgb_image.convertTo(rgb_image, CV_32FC3, 1.0 / 255.0);
    
    int height = rgb_image.rows;
    int width = rgb_image.cols;
    
    for (int c = 0; c < input_channels_; c++) {
        for (int h = 0; h < height; h++) {
            for (int w = 0; w < width; w++) {
                output_buffer[c * height * width + h * width + w] = 
                    rgb_image.at<cv::Vec3f>(h, w)[c];
            }
        }
    }
}

cv::Mat ESPCN::postprocess(const float* input_buffer, int input_height, int input_width) {
    int output_height = input_height * scale_factor_;
    int output_width = input_width * scale_factor_;
    
    cv::Mat output_image(output_height, output_width, CV_32FC3);
    
    for (int c = 0; c < input_channels_; c++) {
        for (int h = 0; h < output_height; h++) {
            for (int w = 0; w < output_width; w++) {
                float value = input_buffer[c * output_height * output_width + h * output_width + w];
                value = std::max(0.0f, std::min(1.0f, value));
                output_image.at<cv::Vec3f>(h, w)[c] = value;
            }
        }
    }
    
    output_image.convertTo(output_image, CV_8UC3, 255.0);
    cv::cvtColor(output_image, output_image, cv::COLOR_RGB2BGR);
    
    return output_image;
}

cv::Mat ESPCN::super_resolve(const cv::Mat& input_image) {
    if (input_image.empty()) {
        throw std::runtime_error("Input image is empty");
    }
    
    int input_height = input_image.rows;
    int input_width = input_image.cols;
    
    size_t input_size = input_channels_ * input_height * input_width * sizeof(float);
    size_t output_size = input_channels_ * input_height * scale_factor_ * input_width * scale_factor_ * sizeof(float);
    
    ensure_buffer_size(input_size, input_buffer_);
    ensure_buffer_size(output_size, output_buffer_);
    
    current_input_size_ = input_size;
    current_output_size_ = output_size;
    
    float* input_data = static_cast<float*>(input_buffer_->data());
    preprocess(input_image, input_data);
    
    std::array<int64_t, 4> input_shape = {1, input_channels_, input_height, input_width};
    
    Ort::Value input_tensor = Ort::Value::CreateTensor<float>(
        memory_info_,
        input_data,
        input_channels_ * input_height * input_width,
        input_shape.data(),
        input_shape.size()
    );
    
    auto output_tensors = session_->Run(
        Ort::RunOptions{nullptr},
        input_names_.data(),
        &input_tensor,
        1,
        output_names_.data(),
        1
    );
    
    float* output_data = output_tensors[0].GetTensorMutableData<float>();
    
    return postprocess(output_data, input_height, input_width);
}

std::vector<cv::Mat> ESPCN::super_resolve_batch(const std::vector<cv::Mat>& input_images) {
    std::vector<cv::Mat> results;
    results.reserve(input_images.size());
    
    if (input_images.empty()) {
        return results;
    }
    
    int max_height = 0;
    int max_width = 0;
    for (const auto& img : input_images) {
        max_height = std::max(max_height, img.rows);
        max_width = std::max(max_width, img.cols);
    }
    
    size_t max_input_size = input_channels_ * max_height * max_width * sizeof(float);
    size_t max_output_size = input_channels_ * max_height * scale_factor_ * max_width * scale_factor_ * sizeof(float);
    
    ensure_buffer_size(max_input_size, input_buffer_);
    ensure_buffer_size(max_output_size, output_buffer_);
    
    for (const auto& image : input_images) {
        results.push_back(super_resolve(image));
    }
    
    return results;
}
