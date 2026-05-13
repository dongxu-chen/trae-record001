#include "mime_types.hpp"
#include <unordered_map>
#include <string>
#include <cctype>

namespace mime_types {

static const std::unordered_map<std::string, std::string> mime_map = {
    {"htm", "text/html"},
    {"html", "text/html"},
    {"shtml", "text/html"},
    {"css", "text/css"},
    {"js", "application/javascript"},
    {"mjs", "application/javascript"},
    {"json", "application/json"},
    {"jsonld", "application/ld+json"},
    {"txt", "text/plain"},
    {"md", "text/markdown"},
    {"markdown", "text/markdown"},
    {"xml", "application/xml"},
    {"xsl", "application/xml"},
    {"yaml", "text/yaml"},
    {"yml", "text/yaml"},
    {"toml", "text/toml"},
    {"jpg", "image/jpeg"},
    {"jpeg", "image/jpeg"},
    {"jpe", "image/jpeg"},
 {"png", "image/png"},
    {"gif", "image/gif"},
    {"ico", "image/x-icon"},
    {"cur", "image/x-icon"},
    {"svg", "image/svg+xml"},
    {"svgz", "image/svg+xml"},
    {"webp", "image/webp"},
    {"bmp", "image/bmp"},
    {"tif", "image/tiff"},
    {"tiff", "image/tiff"},
    {"pdf", "application/pdf"},
    {"zip", "application/zip"},
    {"gz", "application/gzip"},
    {"gzip", "application/gzip"},
    {"tar", "application/x-tar"},
    {"tgz", "application/gzip"},
    {"rar", "application/x-rar-compressed"},
    {"7z", "application/x-7z-compressed"},
    {"bz2", "application/x-bzip2"},
    {"xz", "application/x-xz"},
    {"mp3", "audio/mpeg"},
    {"wav", "audio/wav"},
    {"ogg", "audio/ogg"},
    {"m4a", "audio/mp4"},
    {"flac", "audio/flac"},
    {"aac", "audio/aac"},
    {"opus", "audio/opus"},
    {"mp4", "video/mp4"},
    {"webm", "video/webm"},
    {"m4v", "video/mp4"},
    {"avi", "video/x-msvideo"},
    {"mov", "video/quicktime"},
    {"mkv", "video/x-matroska"},
    {"flv", "video/x-flv"},
    {"csv", "text/csv"},
    {"rtf", "application/rtf"},
    {"doc", "application/msword"},
    {"docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    {"xls", "application/vnd.ms-excel"},
    {"xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    {"ppt", "application/vnd.ms-powerpoint"},
    {"pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"},
    {"ttf", "font/ttf"},
    {"otf", "font/otf"},
    {"woff", "font/woff"},
    {"woff2", "font/woff2"},
    {"eot", "application/vnd.ms-fontobject"},
    {"wasm", "application/wasm"},
    {"map", "application/json"},
};

std::string extension_to_type(const std::string& extension)
{
    std::string lower;
    lower.reserve(extension.size());
    for (char c : extension) {
        lower.push_back(static_cast<char>(std::tolower(static_cast<unsigned char>(c))));
    }

    auto it = mime_map.find(lower);
    if (it != mime_map.end()) {
        return it->second;
    }
    return "application/octet-stream";
}

}
