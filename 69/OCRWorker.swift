import Foundation
import PDFKit
import Vision
import AppKit

class OCRWorker {
    
    static let shared = OCRWorker()
    
    private init() {}
    
    enum RecognitionLevel {
        case fast
        case accurate
        
        var requestLevel: VNRequestTextRecognitionLevel {
            switch self {
            case .fast: return .fast
            case .accurate: return .accurate
            }
        }
    }
    
    struct OCRResult {
        let pageIndex: Int
        let text: String
        let boundingBoxes: [CGRect]
        let recognizedText: [RecognizedText]
    }
    
    struct RecognizedText {
        let text: String
        let boundingBox: CGRect
        let confidence: Float
        let topLeft: CGPoint
        let topRight: CGPoint
        let bottomLeft: CGPoint
        let bottomRight: CGPoint
    }
    
    var recognitionLevel: RecognitionLevel = .accurate
    var languages: [String] = ["zh-Hans", "en"]
    var recognitionLanguages: [String] {
        get { languages }
        set { languages = newValue }
    }
    var usesLanguageCorrection: Bool = true
    var customWords: [String] = []
    var minimumTextHeight: Float = 0.0
    
    func recognizeText(from pdfFile: PDFFile, progress: ((Double, Int, Int) -> Void)? = nil) async throws -> [OCRResult] {
        guard let document = PDFDocument(url: pdfFile.url) else {
            throw OCRError.failedToOpenDocument
        }
        
        if document.isLocked {
            throw OCRError.encryptedDocument
        }
        
        var results: [OCRResult] = []
        let pageCount = document.pageCount
        
        for pageIndex in 0..<pageCount {
            guard let page = document.page(at: pageIndex) else { continue }
            
            let pageProgress = Double(pageIndex) / Double(pageCount)
            progress?(pageProgress, pageIndex, pageCount)
            
            let pageResult = try await recognizeText(from: page, pageIndex: pageIndex)
            results.append(pageResult)
        }
        
        progress?(1.0, pageCount, pageCount)
        return results
    }
    
    func recognizeText(from pdfURL: URL, progress: ((Double, Int, Int) -> Void)? = nil) async throws -> [OCRResult] {
        let file = PDFFile(url: pdfURL)
        return try await recognizeText(from: file, progress: progress)
    }
    
    func recognizeText(from page: PDFPage, pageIndex: Int) async throws -> OCRResult {
        let image = renderPageToImage(page)
        
        guard let cgImage = image.cgImage else {
            throw OCRError.failedToRenderPage
        }
        
        return try await performOCR(on: cgImage, pageIndex: pageIndex, pageSize: page.bounds(for: .mediaBox).size)
    }
    
    func recognizeText(from image: NSImage, pageIndex: Int = 0) async throws -> OCRResult {
        guard let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
            throw OCRError.failedToRenderPage
        }
        
        return try await performOCR(on: cgImage, pageIndex: pageIndex, pageSize: image.size)
    }
    
    private func performOCR(on cgImage: CGImage, pageIndex: Int, pageSize: CGSize) async throws -> OCRResult {
        return try await withCheckedThrowingContinuation { continuation in
            let request = VNRecognizeTextRequest { request, error in
                if let error = error {
                    continuation.resume(throwing: error)
                    return
                }
                
                guard let observations = request.results as? [VNRecognizedTextObservation else {
                    continuation.resume(throwing: OCRError.recognitionFailed)
                    return
                }
                
                var recognizedTexts: [RecognizedText] = []
                var allText: String = ""
                var boundingBoxes: [CGRect] = []
                
                for observation in observations {
                    guard let topCandidate = observation.topCandidates(1).first else { continue }
                    
                    let text = topCandidate.string
                    allText += text + "\n"
                    
                    let boundingBox = observation.boundingBox
                    let convertedBox = self.convertBoundingBox(boundingBox, to: pageSize)
                    boundingBoxes.append(convertedBox)
                    
                    let quad = try? topCandidate.boundingBox(for: text.startIndex..<text.endIndex)
                    
                    let recognized = RecognizedText(
                        text: text,
                        boundingBox: convertedBox,
                        confidence: observation.confidence,
                        topLeft: quad?.topLeft ?? .zero,
                        topRight: quad?.topRight ?? .zero,
                        bottomLeft: quad?.bottomLeft ?? .zero,
                        bottomRight: quad?.bottomRight ?? .zero
                    )
                    
                    recognizedTexts.append(recognized)
                }
                
                let result = OCRResult(
                    pageIndex: pageIndex,
                    text: allText.trimmingCharacters(in: .whitespacesAndNewlines),
                    boundingBoxes: boundingBoxes,
                    recognizedText: recognizedTexts
                )
                
                continuation.resume(returning: result)
            }
            
            request.recognitionLevel = recognitionLevel.requestLevel
            request.recognitionLanguages = languages
            request.usesLanguageCorrection = usesLanguageCorrection
            request.customWords = customWords
            request.minimumTextHeight = minimumTextHeight
            
            let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
            
            DispatchQueue.global(qos: .userInitiated).async {
                do {
                    try handler.perform([request])
                } catch {
                    continuation.resume(throwing: error)
                }
            }
        }
    }
    
    private func renderPageToImage(_ page: PDFPage) -> NSImage {
        let pageBounds = page.bounds(for: .mediaBox)
        let scale: CGFloat = 2.0
        let size = CGSize(width: pageBounds.width * scale, height: pageBounds.height * scale)
        
        let image = NSImage(size: size)
        
        image.lockFocus()
        
        guard let context = NSGraphicsContext.current?.cgContext else {
            image.unlockFocus()
            return image
        }
        
        context.saveGState()
        context.translateBy(x: 0, y: size.height)
        context.scaleBy(x: scale, y: -scale)
        
        let whiteColor = NSColor.white
        whiteColor.setFill()
        context.fill(pageBounds)
        
        page.draw(with: .mediaBox, to: context)
        
        context.restoreGState()
        image.unlockFocus()
        
        return image
    }
    
    private func convertBoundingBox(_ boundingBox: CGRect, to pageSize: CGSize) -> CGRect {
        let x = boundingBox.origin.x * pageSize.width
        let y = (1 - boundingBox.origin.y - boundingBox.size.height) * pageSize.height
        let width = boundingBox.size.width * pageSize.width
        let height = boundingBox.size.height * pageSize.height
        
        return CGRect(x: x, y: y, width: width, height: height)
    }
    
    func exportTextResults(_ results: [OCRResult], to outputURL: URL) throws {
        var fullText = ""
        
        for result in results {
            fullText += "=== Page \(result.pageIndex + 1) ===\n\n"
            fullText += result.text
            fullText += "\n\n"
        }
        
        try fullText.write(to: outputURL, atomically: true, encoding: .utf8)
    }
    
    func searchText(in results: [OCRResult], keyword: String, caseSensitive: Bool = false) -> [SearchResult] {
        var searchResults: [SearchResult] = []
        let searchKeyword = caseSensitive ? keyword : keyword.lowercased()
        
        for result in results {
            let searchText = caseSensitive ? result.text : result.text.lowercased()
            
            if searchText.contains(searchKeyword) {
                var ranges: [NSRange] = []
                let nsText = searchText as NSString
                
                var searchRange = NSRange(location: 0, length: nsText.length)
                while searchRange.location < nsText.length {
                    let foundRange = nsText.range(of: searchKeyword, options: caseSensitive ? [] : .caseInsensitive, range: searchRange)
                    
                    if foundRange.location != NSNotFound {
                        ranges.append(foundRange)
                        searchRange = NSRange(location: foundRange.location + foundRange.length, length: nsText.length - foundRange.location - foundRange.length)
                    } else {
                        break
                    }
                }
                
                if !ranges.isEmpty {
                    searchResults.append(
                        SearchResult(
                            pageIndex: result.pageIndex,
                            ranges: ranges,
                            context: result.text,
                            boundingBoxes: result.boundingBoxes
                        )
                    )
                }
            }
        }
        
        return searchResults
    }
}

enum OCRError: LocalizedError {
    case failedToOpenDocument
    case encryptedDocument
    case failedToRenderPage
    case recognitionFailed
    case invalidImage
    case languageNotSupported(String)
    
    var errorDescription: String? {
        switch self {
        case .failedToOpenDocument:
            return "无法打开 PDF 文档"
        case .encryptedDocument:
            return "PDF 文档已加密，需要密码"
        case .failedToRenderPage:
            return "无法渲染 PDF 页面"
        case .recognitionFailed:
            return "文字识别失败"
        case .invalidImage:
            return "无效的图像"
        case .languageNotSupported(let lang):
            return "不支持的语言: \(lang)"
        }
    }
    
    var recoverySuggestion: String? {
        switch self {
        case .failedToOpenDocument:
            return "请确保文件存在且可访问"
        case .encryptedDocument:
            return "请先解锁加密的 PDF 文档"
        case .failedToRenderPage:
            return "请检查 PDF 文件是否损坏"
        case .recognitionFailed:
            return "请确保图片清晰度足够"
        case .invalidImage:
            return "请提供有效的图像"
        case .languageNotSupported(_):
            return "请选择支持的语言"
        }
    }
}

struct SearchResult {
    let pageIndex: Int
    let ranges: [NSRange]
    let context: String
    let boundingBoxes: [CGRect]
}
