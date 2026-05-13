import SwiftUI
import PDFKit
import AppKit

struct ThumbnailView: View {
    let document: PDFDocument?
    @Binding var selectedPageIndex: Int
    var onPageSelected: ((Int) -> Void)?
    
    @State private var thumbnailSize: CGSize = CGSize(width: 100, height: 140)
    @State private var isDragging: Bool = false
    @State private var dragOffset: CGFloat = 0
    @State private var hoveredIndex: Int?
    
    var body: some View {
        VStack(spacing: 0) {
            headerBar
            
            Divider()
            
            if let document = document, document.pageCount > 0 {
                ScrollViewReader { proxy in
                    ScrollView(showsIndicators: true) {
                        LazyVStack(spacing: 12) {
                            ForEach(0..<document.pageCount, id: \.self) { index in
                                ThumbnailCell(
                                    page: document.page(at: index),
                                    pageNumber: index + 1,
                                    isSelected: selectedPageIndex == index,
                                    isHovered: hoveredIndex == index,
                                    size: thumbnailSize
                                )
                                .id(index)
                                .onTapGesture {
                                    selectedPageIndex = index
                                    onPageSelected?(index)
                                }
                                .onHover { hovering in
                                    hoveredIndex = hovering ? index : nil
                                }
                                .scaleEffect(hoveredIndex == index ? 1.05 : 1.0)
                                .animation(.easeInOut(duration: 0.15), value: hoveredIndex)
                            }
                        }
                        .padding(.vertical, 16)
                        .padding(.horizontal, 12)
                    }
                    .onChange(of: selectedPageIndex) { newIndex in
                        withAnimation(.easeInOut(duration: 0.3)) {
                            proxy.scrollTo(newIndex, anchor: .center)
                        }
                    }
                }
            } else {
                emptyState
            }
            
            Divider()
            
            footerBar
        }
        .frame(minWidth: 140, maxWidth: 200)
        .background(Color(nsColor: .controlBackgroundColor))
        .gesture(
            DragGesture(minimumDistance: 10)
                .onChanged { value in
                    isDragging = true
                    dragOffset = value.translation.height
                }
                .onEnded { _ in
                    isDragging = false
                    dragOffset = 0
                }
        )
    }
    
    private var headerBar: some View {
        HStack {
            Text("页面缩略图")
                .font(.subheadline)
                .fontWeight(.medium)
                .foregroundColor(.secondary)
            
            Spacer()
            
            Menu {
                Button("小") { thumbnailSize = CGSize(width: 80, height: 110) }
                Button("中") { thumbnailSize = CGSize(width: 100, height: 140) }
                Button("大") { thumbnailSize = CGSize(width: 130, height: 180) }
            } label: {
                Image(systemName: "slider.horizontal.3")
                    .font(.caption)
            }
            .menuStyle(.borderlessButton)
            .frame(width: 24)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(Color(nsColor: .windowBackgroundColor))
    }
    
    private var emptyState: some View {
        VStack(spacing: 12) {
            Image(systemName: "doc.on.doc")
                .font(.system(size: 36))
                .foregroundColor(.tertiary)
            
            Text("暂无 PDF 文档")
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .frame(maxHeight: .infinity)
    }
    
    private var footerBar: some View {
        HStack {
            Button(action: goToPreviousPage) {
                Image(systemName: "chevron.up")
                    .font(.caption)
            }
            .buttonStyle(.borderless)
            .disabled(selectedPageIndex <= 0)
            
            Spacer()
            
            Text("\(selectedPageIndex + 1) / \(document?.pageCount ?? 0)")
                .font(.caption)
                .monospacedDigit()
                .foregroundColor(.secondary)
            
            Spacer()
            
            Button(action: goToNextPage) {
                Image(systemName: "chevron.down")
                    .font(.caption)
            }
            .buttonStyle(.borderless)
            .disabled(selectedPageIndex >= (document?.pageCount ?? 1) - 1)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(Color(nsColor: .windowBackgroundColor))
    }
    
    private func goToPreviousPage() {
        if selectedPageIndex > 0 {
            selectedPageIndex -= 1
            onPageSelected?(selectedPageIndex)
        }
    }
    
    private func goToNextPage() {
        if let pageCount = document?.pageCount, selectedPageIndex < pageCount - 1 {
            selectedPageIndex += 1
            onPageSelected?(selectedPageIndex)
        }
    }
}

struct ThumbnailCell: View {
    let page: PDFPage?
    let pageNumber: Int
    let isSelected: Bool
    let isHovered: Bool
    let size: CGSize
    
    @State private var thumbnailImage: NSImage?
    
    var body: some View {
        VStack(spacing: 6) {
            ZStack {
                if let image = thumbnailImage {
                    Image(nsImage: image)
                        .resizable()
                        .scaledToFit()
                        .frame(width: size.width, height: size.height)
                        .background(Color.white)
                        .cornerRadius(4)
                        .shadow(
                            color: isSelected ? Color.accentColor.opacity(0.5) : Color.black.opacity(0.15),
                            radius: isSelected ? 6 : 3,
                            x: 0,
                            y: isSelected ? 2 : 1
                        )
                        .overlay(
                            RoundedRectangle(cornerRadius: 4)
                                .stroke(isSelected ? Color.accentColor : Color.clear, lineWidth: 2)
                        )
                } else {
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color.gray.opacity(0.1))
                        .frame(width: size.width, height: size.height)
                        .overlay(
                            ProgressView()
                                .progressViewStyle(.circular)
                        )
                }
            }
            
            Text("\(pageNumber)")
                .font(.caption2)
                .foregroundColor(isSelected ? .accentColor : .secondary)
                .fontWeight(isSelected ? .semibold : .regular)
        }
        .frame(width: size.width + 8)
        .onAppear {
            loadThumbnail()
        }
        .onChange(of: page) { _ in
            loadThumbnail()
        }
    }
    
    private func loadThumbnail() {
        guard let page = page else { return }
        
        DispatchQueue.global(qos: .userInitiated).async {
            let thumbnail = page.thumbnail(
                of: CGSize(width: size.width * 2, height: size.height * 2),
                for: .mediaBox
            )
            
            DispatchQueue.main.async {
                self.thumbnailImage = thumbnail
            }
        }
    }
}

struct ThumbnailView_Previews: PreviewProvider {
    static var previews: some View {
        ThumbnailView(
            document: nil,
            selectedPageIndex: .constant(0)
        )
        .frame(width: 150, height: 500)
    }
}

class ThumbnailGridView: NSView {
    var document: PDFDocument? {
        didSet {
            updateThumbnails()
        }
    }
    
    var selectedPageIndex: Int = 0 {
        didSet {
            updateSelection()
        }
    }
    
    var onPageSelected: ((Int) -> Void)?
    
    private var collectionView: NSCollectionView!
    private var thumbnailSize: NSSize = NSSize(width: 100, height: 140)
    private var thumbnailCache: NSCache<NSNumber, NSImage> = NSCache()
    
    override init(frame frameRect: NSRect) {
        super.init(frame: frameRect)
        setupCollectionView()
        setupGestureRecognizers()
    }
    
    required init?(coder: NSCoder) {
        super.init(coder: coder)
        setupCollectionView()
        setupGestureRecognizers()
    }
    
    private func setupCollectionView() {
        let layout = NSCollectionViewFlowLayout()
        layout.itemSize = NSSize(width: 100, height: 140)
        layout.minimumInteritemSpacing = 8
        layout.minimumLineSpacing = 12
        layout.sectionInset = NSEdgeInsets(top: 16, left: 12, bottom: 16, right: 12)
        
        collectionView = NSCollectionView(frame: bounds)
        collectionView.autoresizingMask = [.width, .height]
        collectionView.collectionViewLayout = layout
        collectionView.dataSource = self
        collectionView.delegate = self
        collectionView.allowsMultipleSelection = false
        collectionView.backgroundColors = [.controlBackgroundColor]
        
        collectionView.register(
            ThumbnailItem.self,
            forItemWithIdentifier: NSUserInterfaceItemIdentifier("ThumbnailItem")
        )
        
        addSubview(collectionView)
    }
    
    private func setupGestureRecognizers() {
        let clickGesture = NSClickGestureRecognizer(target: self, action: #selector(handleClick(_:)))
        collectionView.addGestureRecognizer(clickGesture)
        
        let doubleClickGesture = NSClickGestureRecognizer(target: self, action: #selector(handleDoubleClick(_:)))
        doubleClickGesture.numberOfClicksRequired = 2
        collectionView.addGestureRecognizer(doubleClickGesture)
        
        clickGesture.require(toFail: doubleClickGesture)
    }
    
    @objc private func handleClick(_ gesture: NSClickGestureRecognizer) {
        let location = gesture.location(in: collectionView)
        if let indexPath = collectionView.indexPathForItem(at: location) {
            selectedPageIndex = indexPath.item
            onPageSelected?(indexPath.item)
        }
    }
    
    @objc private func handleDoubleClick(_ gesture: NSClickGestureRecognizer) {
        let location = gesture.location(in: collectionView)
        if let indexPath = collectionView.indexPathForItem(at: location) {
            selectedPageIndex = indexPath.item
            onPageSelected?(indexPath.item)
        }
    }
    
    private func updateThumbnails() {
        DispatchQueue.main.async {
            self.collectionView.reloadData()
        }
    }
    
    private func updateSelection() {
        DispatchQueue.main.async {
            let indexSet = IndexSet(integer: self.selectedPageIndex)
            self.collectionView.selectItems(at: [IndexPath(item: self.selectedPageIndex, section: 0)], scrollPosition: .centeredVertically)
        }
    }
    
    func scrollToPage(_ pageIndex: Int, animated: Bool = true) {
        guard pageIndex >= 0 && pageIndex < (document?.pageCount ?? 0) else { return }
        
        let indexPath = IndexPath(item: pageIndex, section: 0)
        collectionView.scrollToItems(at: [indexPath], scrollPosition: .centeredVertically)
        
        if animated {
            NSAnimationContext.runAnimationGroup { context in
                context.duration = 0.3
                collectionView.animator().scrollToItems(at: [indexPath], scrollPosition: .centeredVertically)
            }
        }
    }
    
    func setThumbnailSize(_ size: NSSize) {
        thumbnailSize = size
        if let layout = collectionView.collectionViewLayout as? NSCollectionViewFlowLayout {
            layout.itemSize = size
        }
        collectionView.collectionViewLayout?.invalidateLayout()
    }
}

extension ThumbnailGridView: NSCollectionViewDataSource, NSCollectionViewDelegate {
    func collectionView(_ collectionView: NSCollectionView, numberOfItemsInSection section: Int) -> Int {
        return document?.pageCount ?? 0
    }
    
    func collectionView(_ collectionView: NSCollectionView, itemForRepresentedObjectAt indexPath: IndexPath) -> NSCollectionViewItem {
        let item = collectionView.makeItem(withIdentifier: NSUserInterfaceItemIdentifier("ThumbnailItem"), for: indexPath) as! ThumbnailItem
        
        guard let page = document?.page(at: indexPath.item) else {
            return item
        }
        
        item.pageNumber = indexPath.item + 1
        item.isSelectedCell = indexPath.item == selectedPageIndex
        
        let cacheKey = NSNumber(value: indexPath.item)
        if let cachedImage = thumbnailCache.object(forKey: cacheKey) {
            item.thumbnailImage = cachedImage
        } else {
            item.thumbnailImage = nil
            
            DispatchQueue.global(qos: .userInitiated).async { [weak self] in
                let size = NSSize(width: self?.thumbnailSize.width ?? 100, height: self?.thumbnailSize.height ?? 140)
                let thumbnail = page.thumbnail(of: NSSize(width: size.width * 2, height: size.height * 2), for: .mediaBox)
                
                DispatchQueue.main.async {
                    self?.thumbnailCache.setObject(thumbnail, forKey: cacheKey)
                    
                    if let currentItem = collectionView.item(at: indexPath) as? ThumbnailItem {
                        currentItem.thumbnailImage = thumbnail
                    }
                }
            }
        }
        
        return item
    }
    
    func collectionView(_ collectionView: NSCollectionView, didSelectItemsAt indexPaths: Set<IndexPath>) {
        guard let indexPath = indexPaths.first else { return }
        selectedPageIndex = indexPath.item
        onPageSelected?(indexPath.item)
    }
}

class ThumbnailItem: NSCollectionViewItem {
    private let imageView = NSImageView()
    private let pageLabel = NSTextField(labelWithString: "")
    
    var thumbnailImage: NSImage? {
        didSet {
            imageView.image = thumbnailImage
        }
    }
    
    var pageNumber: Int = 1 {
        didSet {
            pageLabel.stringValue = "\(pageNumber)"
        }
    }
    
    var isSelectedCell: Bool = false {
        didSet {
            updateSelectionStyle()
        }
    }
    
    override func loadView() {
        view = NSView(frame: NSRect(x: 0, y: 0, width: 100, height: 140))
        view.wantsLayer = true
        
        imageView.imageScaling = .scaleProportionallyUpOrDown
        imageView.wantsLayer = true
        imageView.layer?.backgroundColor = NSColor.white.cgColor
        imageView.layer?.cornerRadius = 4
        imageView.layer?.shadowColor = NSColor.black.cgColor
        imageView.layer?.shadowOpacity = 0.15
        imageView.layer?.shadowRadius = 3
        imageView.layer?.shadowOffset = CGSize(width: 0, height: 1)
        imageView.translatesAutoresizingMaskIntoConstraints = false
        
        pageLabel.alignment = .center
        pageLabel.font = NSFont.systemFont(ofSize: 11, weight: .regular)
        pageLabel.textColor = .secondaryLabelColor
        pageLabel.translatesAutoresizingMaskIntoConstraints = false
        
        view.addSubview(imageView)
        view.addSubview(pageLabel)
        
        NSLayoutConstraint.activate([
            imageView.topAnchor.constraint(equalTo: view.topAnchor),
            imageView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            imageView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            imageView.heightAnchor.constraint(equalTo: view.heightAnchor, multiplier: 0.88),
            
            pageLabel.topAnchor.constraint(equalTo: imageView.bottomAnchor, constant: 4),
            pageLabel.centerXAnchor.constraint(equalTo: view.centerXAnchor)
        ])
    }
    
    override var isSelected: Bool {
        didSet {
            isSelectedCell = isSelected
        }
    }
    
    private func updateSelectionStyle() {
        if isSelectedCell {
            imageView.layer?.borderWidth = 2
            imageView.layer?.borderColor = NSColor.controlAccentColor.cgColor
            imageView.layer?.shadowOpacity = 0.3
            imageView.layer?.shadowRadius = 6
            pageLabel.textColor = .controlAccentColor
            pageLabel.font = NSFont.systemFont(ofSize: 11, weight: .semibold)
        } else {
            imageView.layer?.borderWidth = 0
            imageView.layer?.borderColor = NSColor.clear.cgColor
            imageView.layer?.shadowOpacity = 0.15
            imageView.layer?.shadowRadius = 3
            pageLabel.textColor = .secondaryLabelColor
            pageLabel.font = NSFont.systemFont(ofSize: 11, weight: .regular)
        }
    }
    
    override func prepareForReuse() {
        super.prepareForReuse()
        thumbnailImage = nil
        pageNumber = 1
        isSelectedCell = false
    }
}
