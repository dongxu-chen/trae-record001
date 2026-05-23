#include <iostream>
#include <string>
#include <chrono>
#include <filesystem>
#include <vector>
#include "ESPCN.h"

namespace fs = std::filesystem;

void print_usage(const char* program_name) {
    std::cout << "Usage: " << program_name << " [OPTIONS]" << std::endl;
    std::cout << "Options:" << std::endl;
    std::cout << "  --model <path>       Path to ONNX model file (required)" << std::endl;
    std::cout << "  --input <path>       Input image path or directory (required)" << std::endl;
    std::cout << "  --output <path>      Output directory (default: ./results)" << std::endl;
    std::cout << "  --scale <number>     Scale factor: 2 or 4 (default: 4)" << std::endl;
    std::cout << "  --gpu                Use GPU if available (default: false)" << std::endl;
    std::cout << "  --benchmark          Run benchmark mode" << std::endl;
}

std::vector<std::string> get_image_files(const std::string& dir_path) {
    std::vector<std::string> image_files;
    const std::vector<std::string> extensions = {".png", ".jpg", ".jpeg", ".bmp"};
    
    for (const auto& entry : fs::directory_iterator(dir_path)) {
        if (entry.is_regular_file()) {
            std::string ext = entry.path().extension().string();
            std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
            
            for (const auto& valid_ext : extensions) {
                if (ext == valid_ext) {
                    image_files.push_back(entry.path().string());
                    break;
                }
            }
        }
    }
    
    return image_files;
}

int main(int argc, char* argv[]) {
    std::string model_path = "";
    std::string input_path = "";
    std::string output_dir = "./results";
    int scale_factor = 4;
    bool use_gpu = false;
    bool benchmark = false;
    
    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        
        if (arg == "--model" && i + 1 < argc) {
            model_path = argv[++i];
        } else if (arg == "--input" && i + 1 < argc) {
            input_path = argv[++i];
        } else if (arg == "--output" && i + 1 < argc) {
            output_dir = argv[++i];
        } else if (arg == "--scale" && i + 1 < argc) {
            scale_factor = std::stoi(argv[++i]);
        } else if (arg == "--gpu") {
            use_gpu = true;
        } else if (arg == "--benchmark") {
            benchmark = true;
        } else if (arg == "--help" || arg == "-h") {
            print_usage(argv[0]);
            return 0;
        }
    }
    
    if (model_path.empty() || input_path.empty()) {
        std::cerr << "Error: --model and --input are required!" << std::endl;
        print_usage(argv[0]);
        return 1;
    }
    
    try {
        std::cout << "Loading ESPCN model..." << std::endl;
        std::cout << "Model path: " << model_path << std::endl;
        std::cout << "Scale factor: x" << scale_factor << std::endl;
        
        ESPCN model(model_path, scale_factor, use_gpu);
        std::cout << "Model loaded successfully!" << std::endl;
        
        fs::create_directories(output_dir);
        
        if (benchmark) {
            std::cout << "\n=== Benchmark Mode ===" << std::endl;
            cv::Mat test_image = cv::Mat::zeros(256, 256, CV_8UC3);
            cv::randu(test_image, cv::Scalar(0, 0, 0), cv::Scalar(255, 255, 255));
            
            model.super_resolve(test_image);
            
            const int num_iterations = 100;
            auto start = std::chrono::high_resolution_clock::now();
            
            for (int i = 0; i < num_iterations; i++) {
                model.super_resolve(test_image);
            }
            
            auto end = std::chrono::high_resolution_clock::now();
            auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
            
            std::cout << "Input size: 256x256" << std::endl;
            std::cout << "Iterations: " << num_iterations << std::endl;
            std::cout << "Total time: " << duration.count() << " ms" << std::endl;
            std::cout << "Average time: " << duration.count() / (double)num_iterations << " ms/image" << std::endl;
            std::cout << "FPS: " << 1000.0 / (duration.count() / (double)num_iterations) << std::endl;
            
            return 0;
        }
        
        if (fs::is_regular_file(input_path)) {
            std::cout << "\nProcessing single image: " << input_path << std::endl;
            
            cv::Mat input_image = cv::imread(input_path);
            if (input_image.empty()) {
                std::cerr << "Failed to read image: " << input_path << std::endl;
                return 1;
            }
            
            std::cout << "Input size: " << input_image.cols << "x" << input_image.rows << std::endl;
            
            auto start = std::chrono::high_resolution_clock::now();
            cv::Mat output_image = model.super_resolve(input_image);
            auto end = std::chrono::high_resolution_clock::now();
            auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
            
            std::cout << "Output size: " << output_image.cols << "x" << output_image.rows << std::endl;
            std::cout << "Processing time: " << duration.count() << " ms" << std::endl;
            
            fs::path input_file(input_path);
            std::string output_filename = input_file.stem().string() + "_x" + 
                                         std::to_string(scale_factor) + input_file.extension().string();
            std::string output_path = (fs::path(output_dir) / output_filename).string();
            
            cv::imwrite(output_path, output_image);
            std::cout << "Result saved to: " << output_path << std::endl;
            
        } else if (fs::is_directory(input_path)) {
            std::cout << "\nProcessing images from directory: " << input_path << std::endl;
            
            std::vector<std::string> image_files = get_image_files(input_path);
            std::cout << "Found " << image_files.size() << " images" << std::endl;
            
            if (image_files.empty()) {
                std::cerr << "No images found in directory!" << std::endl;
                return 1;
            }
            
            double total_time = 0.0;
            int success_count = 0;
            
            for (size_t i = 0; i < image_files.size(); i++) {
                const std::string& image_path = image_files[i];
                std::cout << "[" << (i + 1) << "/" << image_files.size() << "] " 
                          << fs::path(image_path).filename().string() << "... ";
                
                cv::Mat input_image = cv::imread(image_path);
                if (input_image.empty()) {
                    std::cout << "FAILED (can't read image)" << std::endl;
                    continue;
                }
                
                auto start = std::chrono::high_resolution_clock::now();
                cv::Mat output_image = model.super_resolve(input_image);
                auto end = std::chrono::high_resolution_clock::now();
                auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
                
                fs::path input_file(image_path);
                std::string output_filename = input_file.stem().string() + "_x" + 
                                             std::to_string(scale_factor) + input_file.extension().string();
                std::string output_path = (fs::path(output_dir) / output_filename).string();
                
                cv::imwrite(output_path, output_image);
                
                total_time += duration.count();
                success_count++;
                
                std::cout << "OK (" << duration.count() << " ms)" << std::endl;
            }
            
            std::cout << "\n=== Summary ===" << std::endl;
            std::cout << "Processed: " << success_count << "/" << image_files.size() << " images" << std::endl;
            std::cout << "Total time: " << total_time << " ms" << std::endl;
            if (success_count > 0) {
                std::cout << "Average time: " << total_time / success_count << " ms/image" << std::endl;
            }
            
        } else {
            std::cerr << "Input path does not exist: " << input_path << std::endl;
            return 1;
        }
        
        std::cout << "\nDone!" << std::endl;
        
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
    
    return 0;
}
