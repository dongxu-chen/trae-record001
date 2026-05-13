import Foundation
import PDFKit

class PDFMerger {
    
    static let shared = PDFMerger()
    
    private init() {}
    
    var passwordProvider: ((String) -> String?)?
    
    func merge(pdfFiles: [PDFFile], to destinationURL: URL) throws {
        guard !pdfFiles.isEmpty else {
            throw PDFMergerError.noFilesProvided
        }
        
        let mergedDocument = PDFDocument()
        var totalPages = 0
        
        for pdfFile in pdfFiles {
            let sourceDocument = try openDocument(from: pdfFile.url, fileName: pdfFile.name)
            try insertPages(from: sourceDocument, into: mergedDocument, at: totalPages)
            totalPages += sourceDocument.pageCount
        }
        
        try writeDocument(mergedDocument, to: destinationURL)
    }
    
    func merge(pdfFiles: [PDFFile], pageRanges: [String: ClosedRange<Int>], to destinationURL: URL) throws {
        guard !pdfFiles.isEmpty else {
            throw PDFMergerError.noFilesProvided
        }
        
        let mergedDocument = PDFDocument()
        var totalPages = 0
        
        for pdfFile in pdfFiles {
            let sourceDocument = try openDocument(from: pdfFile.url, fileName: pdfFile.name)
            
            let range = pageRanges[pdfFile.id.uuidString] ?? 1...sourceDocument.pageCount
            let startIndex = max(0, range.lowerBound - 1)
            let endIndex = min(sourceDocument.pageCount - 1, range.upperBound - 1)
            
            guard startIndex <= endIndex else {
                throw PDFMergerError.invalidPageRange(pdfFile.name)
            }
            
            try insertPages(from: sourceDocument, range: startIndex...endIndex, into: mergedDocument, at: totalPages)
            totalPages += (endIndex - startIndex + 1)
        }
        
        try writeDocument(mergedDocument, to: destinationURL)
    }
    
    func merge(pdfURLs: [URL], to destinationURL: URL) throws {
        let pdfFiles = pdfURLs.map { PDFFile(url: $0) }
        try merge(pdfFiles: pdfFiles, to: destinationURL)
    }
    
    func merge(pdfDocuments: [PDFDocument], to destinationURL: URL) throws {
        guard !pdfDocuments.isEmpty else {
            throw PDFMergerError.noFilesProvided
        }
        
        let mergedDocument = PDFDocument()
        var totalPages = 0
        
        for document in pdfDocuments {
            try insertPages(from: document, into: mergedDocument, at: totalPages)
            totalPages += document.pageCount
        }
        
        try writeDocument(mergedDocument, to: destinationURL)
    }
    
    func split(pdfFile: PDFFile, pageRanges: [ClosedRange<Int>], outputDirectory: URL) throws -> [URL] {
        let sourceDocument = try openDocument(from: pdfFile.url, fileName: pdfFile.name)
        
        let fileBaseName = (pdfFile.name as NSString).deletingPathExtension
        var outputURLs: [URL] = []
        
        for (index, range) in pageRanges.enumerated() {
            let startIndex = max(0, range.lowerBound - 1)
            let endIndex = min(sourceDocument.pageCount - 1, range.upperBound - 1)
            
            guard startIndex <= endIndex else {
                throw PDFMergerError.invalidPageRange(pdfFile.name)
            }
            
            let splitDocument = PDFDocument()
            try insertPages(from: sourceDocument, range: startIndex...endIndex, into: splitDocument, at: 0)
            
            let outputFileName = "\(fileBaseName)_part\(index + 1).pdf"
            let outputURL = outputDirectory.appendingPathComponent(outputFileName)
            
            try writeDocument(splitDocument, to: outputURL)
            outputURLs.append(outputURL)
        }
        
        return outputURLs
    }
    
    func extractPages(from pdfFile: PDFFile, pages: [Int], to destinationURL: URL) throws {
        let sourceDocument = try openDocument(from: pdfFile.url, fileName: pdfFile.name)
        
        guard !pages.isEmpty else {
            throw PDFMergerError.noFilesProvided
        }
        
        let extractedDocument = PDFDocument()
        var insertIndex = 0
        
        for pageNumber in pages {
            let pageIndex = pageNumber - 1
            guard pageIndex >= 0 && pageIndex < sourceDocument.pageCount else {
                throw PDFMergerError.invalidPageRange(pdfFile.name)
            }
            
            try insertPage(from: sourceDocument, at: pageIndex, into: extractedDocument, at: insertIndex)
            insertIndex += 1
        }
        
        try writeDocument(extractedDocument, to: destinationURL)
    }
    
    func rotatePages(in pdfFile: PDFFile, pages: [Int]? = nil, rotation: Int, to destinationURL: URL) throws {
        let sourceDocument = try openDocument(from: pdfFile.url, fileName: pdfFile.name)
        
        guard let copiedDocument = sourceDocument.copy() as? PDFDocument else {
            throw PDFMergerError.failedToOpenFile(pdfFile.name)
        }
        
        let pagesToRotate: [Int]
        if let pages = pages {
            pagesToRotate = pages.map { $0 - 1 }
        } else {
            pagesToRotate = Array(0..<copiedDocument.pageCount)
        }
        
        for pageIndex in pagesToRotate {
            guard pageIndex >= 0 && pageIndex < copiedDocument.pageCount else {
                throw PDFMergerError.invalidPageRange(pdfFile.name)
            }
            
            guard let page = copiedDocument.page(at: pageIndex) else { continue }
            
            let currentRotation = page.rotation
            let newRotation = (currentRotation + rotation) % 360
            page.rotation = newRotation
        }
        
        try writeDocument(copiedDocument, to: destinationURL)
    }
    
    private func openDocument(from url: URL, fileName: String) throws -> PDFDocument {
        guard let document = PDFDocument(url: url) else {
            throw PDFMergerError.failedToOpenFile(fileName)
        }
        
        if document.isLocked {
            var unlocked = false
            
            if let provider = passwordProvider {
                if let password = provider(fileName) {
                    unlocked = document.unlock(withPassword: password)
                }
            }
            
            if !unlocked {
                throw PDFMergerError.encryptedPDF(fileName)
            }
        }
        
        return document
    }
    
    private func insertPages(from source: PDFDocument, into destination: PDFDocument, at insertIndex: Int) throws {
        for pageIndex in 0..<source.pageCount {
            try insertPage(from: source, at: pageIndex, into: destination, at: insertIndex + pageIndex)
        }
    }
    
    private func insertPages(from source: PDFDocument, range: ClosedRange<Int>, into destination: PDFDocument, at insertIndex: Int) throws {
        for (offset, pageIndex) in range.enumerated() {
            try insertPage(from: source, at: pageIndex, into: destination, at: insertIndex + offset)
        }
    }
    
    private func insertPage(from source: PDFDocument, at sourceIndex: Int, into destination: PDFDocument, at destinationIndex: Int) throws {
        guard let sourcePage = source.page(at: sourceIndex) else {
            throw PDFMergerError.failedToReadPage("source", sourceIndex)
        }
        
        guard let copiedPage = createPageCopy(from: sourcePage) else {
            throw PDFMergerError.failedToReadPage("source", sourceIndex)
        }
        
        destination.insert(copiedPage, at: destinationIndex)
    }
    
    private func createPageCopy(from sourcePage: PDFPage) -> PDFPage? {
        if let copiedPage = sourcePage.copy() as? PDFPage {
            return copiedPage
        }
        
        return PDFPage()
    }
    
    private func writeDocument(_ document: PDFDocument, to url: URL) throws {
        let directory = url.deletingLastPathComponent()
        if !FileManager.default.fileExists(atPath: directory.path) {
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        }
        
        guard document.write(to: url) else {
            throw PDFMergerError.failedToWriteFile
        }
    }
}

enum PDFMergerError: LocalizedError {
    case noFilesProvided
    case failedToOpenFile(String)
    case failedToReadPage(String, Int)
    case failedToWriteFile
    case invalidPageRange(String)
    case encryptedPDF(String)
    case passwordRequired(String)
    case incorrectPassword(String)
    
    var errorDescription: String? {
        switch self {
        case .noFilesProvided:
            return "没有提供要合并的 PDF 文件"
        case .failedToOpenFile(let fileName):
            return "无法打开文件: \(fileName)"
        case .failedToReadPage(let fileName, let pageIndex):
            return "无法读取文件 \(fileName) 的第 \(pageIndex + 1) 页"
        case .failedToWriteFile:
            return "无法写入输出文件"
        case .invalidPageRange(let fileName):
            return "文件 \(fileName) 的页码范围无效"
        case .encryptedPDF(let fileName):
            return "文件 \(fileName) 已加密，需要密码"
        case .passwordRequired(let fileName):
            return "需要密码才能打开 \(fileName)"
        case .incorrectPassword(let fileName):
            return "文件 \(fileName) 的密码不正确"
        }
    }
    
    var recoverySuggestion: String? {
        switch self {
        case .noFilesProvided:
            return "请先添加至少一个 PDF 文件"
        case .failedToOpenFile(_):
            return "请确保文件存在且具有读取权限"
        case .failedToReadPage(_, _):
            return "请检查文件是否损坏"
        case .failedToWriteFile:
            return "请确保输出目录可写且有足够的磁盘空间"
        case .invalidPageRange(_):
            return "请检查页码范围是否正确（从1开始）"
        case .encryptedPDF(_), .passwordRequired(_), .incorrectPassword(_):
            return "请提供正确的密码或移除加密保护"
        }
    }
    
    var isEncryptionError: Bool {
        switch self {
        case .encryptedPDF, .passwordRequired, .incorrectPassword:
            return true
        default:
            return false
        }
    }
}

extension PDFMerger {
    
    func getPageCount(for pdfFile: PDFFile) -> Int {
        guard let document = PDFDocument(url: pdfFile.url) else { return 0 }
        if document.isLocked {
            return 0
        }
        return document.pageCount
    }
    
    func getPageCount(for url: URL) -> Int {
        guard let document = PDFDocument(url: url) else { return 0 }
        if document.isLocked {
            return 0
        }
        return document.pageCount
    }
    
    func validatePDF(url: URL) -> Bool {
        guard let document = PDFDocument(url: url) else { return false }
        return !document.isLocked
    }
    
    func validatePDF(pdfFile: PDFFile) -> Bool {
        guard let document = PDFDocument(url: pdfFile.url) else { return false }
        return !document.isLocked
    }
    
    func isPDFEncrypted(url: URL) -> Bool {
        guard let document = PDFDocument(url: url) else { return false }
        return document.isLocked
    }
    
    func isPDFEncrypted(pdfFile: PDFFile) -> Bool {
        guard let document = PDFDocument(url: pdfFile.url) else { return false }
        return document.isLocked
    }
    
    func tryUnlockPDF(url: URL, withPassword password: String) -> Bool {
        guard let document = PDFDocument(url: url) else { return false }
        if !document.isLocked {
            return true
        }
        return document.unlock(withPassword: password)
    }
    
    func tryUnlockPDF(pdfFile: PDFFile, withPassword password: String) -> Bool {
        return tryUnlockPDF(url: pdfFile.url, withPassword: password)
    }
    
    func getPDFInfo(for pdfFile: PDFFile) -> [String: Any] {
        guard let document = PDFDocument(url: pdfFile.url) else {
            return [:]
        }
        
        var info: [String: Any] = [:]
        info["pageCount"] = document.isLocked ? 0 : document.pageCount
        info["fileName"] = pdfFile.name
        info["isEncrypted"] = document.isLocked
        
        if let docAttributes = document.documentAttributes {
            if let title = docAttributes[PDFDocumentAttribute.titleAttribute] {
                info["title"] = title
            }
            if let author = docAttributes[PDFDocumentAttribute.authorAttribute] {
                info["author"] = author
            }
            if let subject = docAttributes[PDFDocumentAttribute.subjectAttribute] {
                info["subject"] = subject
            }
            if let creator = docAttributes[PDFDocumentAttribute.creatorAttribute] {
                info["creator"] = creator
            }
            if let creationDate = docAttributes[PDFDocumentAttribute.creationDateAttribute] {
                info["creationDate"] = creationDate
            }
            if let modificationDate = docAttributes[PDFDocumentAttribute.modificationDateAttribute] {
                info["modificationDate"] = modificationDate
            }
        }
        
        return info
    }
}

extension PDFMerger {
    
    func performOCR(on pdfFile: PDFFile, 
                    recognitionLevel: OCRWorker.RecognitionLevel = .accurate,
                    languages: [String] = ["zh-Hans", "en"],
                    progress: ((Double, Int, Int) -> Void)? = nil) async throws -> [OCRWorker.OCRResult] {
        let worker = OCRWorker.shared
        worker.recognitionLevel = recognitionLevel
        worker.recognitionLanguages = languages
        
        return try await worker.recognizeText(from: pdfFile, progress: progress)
    }
    
    func performOCR(on pdfURL: URL,
                    recognitionLevel: OCRWorker.RecognitionLevel = .accurate,
                    languages: [String] = ["zh-Hans", "en"],
                    progress: ((Double, Int, Int) -> Void)? = nil) async throws -> [OCRWorker.OCRResult] {
        let worker = OCRWorker.shared
        worker.recognitionLevel = recognitionLevel
        worker.recognitionLanguages = languages
        
        return try await worker.recognizeText(from: pdfURL, progress: progress)
    }
    
    func extractTextWithOCR(from pdfFile: PDFFile) async throws -> String {
        let results = try await performOCR(on: pdfFile)
        
        var fullText = ""
        for result in results {
            fullText += "=== 第 \(result.pageIndex + 1) 页 ===\n\n"
            fullText += result.text
            fullText += "\n\n"
        }
        
        return fullText
    }
    
    func exportOCRText(_ results: [OCRWorker.OCRResult], to outputURL: URL) throws {
        try OCRWorker.shared.exportTextResults(results, to: outputURL)
    }
    
    func searchInOCRResults(_ results: [OCRWorker.OCRResult], 
                           keyword: String,
                           caseSensitive: Bool = false) -> [SearchResult] {
        let ocrResults = OCRWorker.shared.searchText(in: results, keyword: keyword, caseSensitive: caseSensitive)
        
        return ocrResults.map { ocrResult in
            SearchResult(
                pageIndex: ocrResult.pageIndex,
                ranges: ocrResult.ranges,
                context: ocrResult.context,
                boundingBoxes: ocrResult.boundingBoxes
            )
        }
    }
    
    func createSearchablePDF(from pdfFile: PDFFile,
                             to outputURL: URL,
                             recognitionLevel: OCRWorker.RecognitionLevel = .accurate,
                             languages: [String] = ["zh-Hans", "en"],
                             progress: ((Double, Int, Int) -> Void)? = nil) async throws {
        let results = try await performOCR(
            on: pdfFile,
            recognitionLevel: recognitionLevel,
            languages: languages,
            progress: progress
        )
        
        guard let sourceDocument = PDFDocument(url: pdfFile.url) else {
            throw PDFMergerError.failedToOpenFile(pdfFile.name)
        }
        
        for result in results {
            guard let page = sourceDocument.page(at: result.pageIndex) else { continue }
            
            for recognizedText in result.recognizedText {
                addTextAnnotation(
                    to: page,
                    text: recognizedText.text,
                    boundingBox: recognizedText.boundingBox
                )
            }
        }
        
        try writeDocument(sourceDocument, to: outputURL)
    }
    
    private func addTextAnnotation(to page: PDFPage, text: String, boundingBox: CGRect) {
        let annotation = PDFAnnotation(bounds: boundingBox, forType: .text, withProperties: [
            PDFAnnotationKey.contents: text,
            PDFAnnotationKey.font: NSFont.systemFont(ofSize: 10),
            PDFAnnotationKey.color: NSColor.clear
        ])
        
        annotation.setValue(text, forAnnotationKey: .contents)
        annotation.setValue(NSColor.clear, forAnnotationKey: .color)
        page.addAnnotation(annotation)
    }
}

struct SearchResult {
    let pageIndex: Int
    let ranges: [NSRange]
    let context: String
    let boundingBoxes: [CGRect]
}

