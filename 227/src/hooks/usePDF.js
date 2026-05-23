import { useState, useCallback, useRef, useEffect } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import * as pdfjsWorker from 'pdfjs-dist/build/pdf.worker.entry';

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker;

const BASE_SCALE = 1.5;

export function usePDF() {
  const [pdfDoc, setPdfDoc] = useState(null);
  const [numPages, setNumPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(BASE_SCALE);
  const [pageAnnotations, setPageAnnotations] = useState({});
  const [pageThumbnails, setPageThumbnails] = useState([]);
  const [searchResults, setSearchResults] = useState([]);
  const [currentSearchIndex, setCurrentSearchIndex] = useState(-1);
  const [searchQuery, setSearchQuery] = useState('');
  const [pageSizes, setPageSizes] = useState({});
  const pdfFileRef = useRef(null);
  const loadedPagesRef = useRef(new Set());

  const loadPDF = useCallback(async (file) => {
    try {
      const arrayBuffer = await file.arrayBuffer();
      const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
      const doc = await loadingTask.promise;
      
      setPdfDoc(doc);
      setNumPages(doc.numPages);
      setCurrentPage(1);
      setPageAnnotations({});
      setPageThumbnails([]);
      setSearchResults([]);
      setCurrentSearchIndex(-1);
      loadedPagesRef.current.clear();
      pdfFileRef.current = file;

      const sizes = {};
      const thumbnails = [];
      
      for (let i = 1; i <= doc.numPages; i++) {
        const page = await doc.getPage(i);
        const baseViewport = page.getViewport({ scale: BASE_SCALE });
        sizes[i] = { width: baseViewport.width, height: baseViewport.height };
        
        const thumbViewport = page.getViewport({ scale: 0.2 });
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.height = thumbViewport.height;
        canvas.width = thumbViewport.width;
        
        await page.render({
          canvasContext: context,
          viewport: thumbViewport
        }).promise;
        
        thumbnails.push(canvas.toDataURL());
      }
      
      setPageSizes(sizes);
      setPageThumbnails(thumbnails);
      loadedPagesRef.current.add(1);
    } catch (error) {
      console.error('Error loading PDF:', error);
    }
  }, []);

  const searchInPDF = useCallback(async (query) => {
    if (!pdfDoc || !query.trim()) {
      setSearchResults([]);
      setCurrentSearchIndex(-1);
      setSearchQuery('');
      return;
    }

    setSearchQuery(query);
    const results = [];
    
    for (let pageNum = 1; pageNum <= pdfDoc.numPages; pageNum++) {
      const page = await pdfDoc.getPage(pageNum);
      const textContent = await page.getTextContent();
      const baseViewport = page.getViewport({ scale: BASE_SCALE });
      
      let textItems = [];
      textContent.items.forEach((item) => {
        if (item.str) {
          textItems.push({
            text: item.str,
            x: item.transform[4] * BASE_SCALE,
            y: baseViewport.height - item.transform[5] * BASE_SCALE,
            width: item.width * BASE_SCALE,
            height: item.height * BASE_SCALE || 12 * BASE_SCALE,
            pageNum
          });
        }
      });

      const fullText = textItems.map(item => item.text).join(' ');
      const regex = new RegExp(query, 'gi');
      let match;
      
      while ((match = regex.exec(fullText)) !== null) {
        let charCount = 0;
        for (const item of textItems) {
          if (charCount <= match.index && charCount + item.text.length >= match.index) {
            results.push({
              pageNum,
              baseX: item.x,
              baseY: item.y,
              baseWidth: Math.max(item.width, query.length * 8),
              baseHeight: item.height,
              x: item.x * (scale / BASE_SCALE),
              y: item.y * (scale / BASE_SCALE),
              width: Math.max(item.width, query.length * 8) * (scale / BASE_SCALE),
              height: item.height * (scale / BASE_SCALE)
            });
            break;
          }
          charCount += item.text.length + 1;
        }
      }
    }
    
    setSearchResults(results);
    setCurrentSearchIndex(results.length > 0 ? 0 : -1);
    
    if (results.length > 0) {
      setCurrentPage(results[0].pageNum);
    }
  }, [pdfDoc, scale]);

  const nextSearchResult = useCallback(() => {
    if (searchResults.length === 0) return;
    const nextIndex = (currentSearchIndex + 1) % searchResults.length;
    setCurrentSearchIndex(nextIndex);
    setCurrentPage(searchResults[nextIndex].pageNum);
  }, [searchResults, currentSearchIndex]);

  const prevSearchResult = useCallback(() => {
    if (searchResults.length === 0) return;
    const prevIndex = (currentSearchIndex - 1 + searchResults.length) % searchResults.length;
    setCurrentSearchIndex(prevIndex);
    setCurrentPage(searchResults[prevIndex].pageNum);
  }, [searchResults, currentSearchIndex]);

  const saveAnnotations = useCallback((pageNum, annotations) => {
    setPageAnnotations(prev => ({
      ...prev,
      [pageNum]: annotations
    }));
  }, []);

  const addPage = useCallback(() => {
    if (!pdfDoc) return;
    const newPageNum = numPages + 1;
    setNumPages(newPageNum);
    setPageThumbnails(prev => [...prev, null]);
    setPageAnnotations(prev => ({
      ...prev,
      [newPageNum]: []
    }));
  }, [pdfDoc, numPages]);

  const deletePage = useCallback((pageNum) => {
    if (numPages <= 1) return;
    
    setNumPages(prev => prev - 1);
    setPageThumbnails(prev => prev.filter((_, i) => i !== pageNum - 1));
    setPageAnnotations(prev => {
      const newAnnotations = {};
      Object.keys(prev).forEach(key => {
        const keyNum = parseInt(key);
        if (keyNum < pageNum) {
          newAnnotations[keyNum] = prev[keyNum];
        } else if (keyNum > pageNum) {
          newAnnotations[keyNum - 1] = prev[keyNum];
        }
      });
      return newAnnotations;
    });
    
    if (currentPage >= pageNum && currentPage > 1) {
      setCurrentPage(prev => prev - 1);
    }
  }, [numPages, currentPage]);

  const movePage = useCallback((fromIndex, toIndex) => {
    if (fromIndex === toIndex || toIndex < 0 || toIndex >= numPages) return;
    
    setPageThumbnails(prev => {
      const newThumbnails = [...prev];
      const [removed] = newThumbnails.splice(fromIndex, 1);
      newThumbnails.splice(toIndex, 0, removed);
      return newThumbnails;
    });
    
    setPageAnnotations(prev => {
      const newAnnotations = {};
      const fromPage = fromIndex + 1;
      const toPage = toIndex + 1;
      
      Object.keys(prev).forEach(key => {
        const keyNum = parseInt(key);
        if (keyNum === fromPage) {
          newAnnotations[toPage] = prev[keyNum];
        } else if (fromPage < toPage && keyNum > fromPage && keyNum <= toPage) {
          newAnnotations[keyNum - 1] = prev[keyNum];
        } else if (fromPage > toPage && keyNum >= toPage && keyNum < fromPage) {
          newAnnotations[keyNum + 1] = prev[keyNum];
        } else {
          newAnnotations[keyNum] = prev[keyNum];
        }
      });
      return newAnnotations;
    });
    
    if (currentPage === fromPage) {
      setCurrentPage(toPage);
    }
  }, [numPages, currentPage]);

  const goToPage = useCallback((pageNum) => {
    if (pageNum >= 1 && pageNum <= numPages) {
      setCurrentPage(pageNum);
    }
  }, [numPages]);

  const nextPage = useCallback(() => {
    if (currentPage < numPages) {
      setCurrentPage(prev => prev + 1);
    }
  }, [currentPage, numPages]);

  const prevPage = useCallback(() => {
    if (currentPage > 1) {
      setCurrentPage(prev => prev - 1);
    }
  }, [currentPage]);

  const zoomIn = useCallback(() => {
    setScale(prev => Math.min(prev + 0.25, 3));
  }, []);

  const zoomOut = useCallback(() => {
    setScale(prev => Math.max(prev - 0.25, 0.5));
  }, []);

  const transformAnnotationsForScale = useCallback((annotations, oldScale, newScale) => {
    if (!annotations || annotations.length === 0) return [];
    const scaleFactor = newScale / oldScale;
    
    return annotations.map(ann => {
      const transformed = { ...ann };
      
      if (ann.left !== undefined) transformed.left = ann.left * scaleFactor;
      if (ann.top !== undefined) transformed.top = ann.top * scaleFactor;
      if (ann.width !== undefined) transformed.width = ann.width * scaleFactor;
      if (ann.height !== undefined) transformed.height = ann.height * scaleFactor;
      if (ann.rx !== undefined) transformed.rx = ann.rx * scaleFactor;
      if (ann.ry !== undefined) transformed.ry = ann.ry * scaleFactor;
      if (ann.x1 !== undefined) transformed.x1 = ann.x1 * scaleFactor;
      if (ann.y1 !== undefined) transformed.y1 = ann.y1 * scaleFactor;
      if (ann.x2 !== undefined) transformed.x2 = ann.x2 * scaleFactor;
      if (ann.y2 !== undefined) transformed.y2 = ann.y2 * scaleFactor;
      if (ann.fontSize !== undefined) transformed.fontSize = ann.fontSize * scaleFactor;
      if (ann.strokeWidth !== undefined) transformed.strokeWidth = Math.max(1, ann.strokeWidth * scaleFactor);
      if (ann.scaleX !== undefined) transformed.scaleX = ann.scaleX;
      if (ann.scaleY !== undefined) transformed.scaleY = ann.scaleY;
      
      return transformed;
    });
  }, []);

  const getScaledSearchResults = useCallback(() => {
    if (searchResults.length === 0) return [];
    const scaleFactor = scale / BASE_SCALE;
    
    return searchResults.map(result => ({
      ...result,
      x: result.baseX * scaleFactor,
      y: result.baseY * scaleFactor,
      width: result.baseWidth * scaleFactor,
      height: result.baseHeight * scaleFactor
    }));
  }, [searchResults, scale]);

  const markPageLoaded = useCallback((pageNum) => {
    loadedPagesRef.current.add(pageNum);
  }, []);

  const isPageLoaded = useCallback((pageNum) => {
    return loadedPagesRef.current.has(pageNum);
  }, []);

  return {
    pdfDoc,
    numPages,
    currentPage,
    scale,
    baseScale: BASE_SCALE,
    pageAnnotations,
    pageThumbnails,
    pageSizes,
    searchResults,
    currentSearchIndex,
    searchQuery,
    loadPDF,
    searchInPDF,
    nextSearchResult,
    prevSearchResult,
    saveAnnotations,
    addPage,
    deletePage,
    movePage,
    goToPage,
    nextPage,
    prevPage,
    zoomIn,
    zoomOut,
    setScale,
    transformAnnotationsForScale,
    getScaledSearchResults,
    markPageLoaded,
    isPageLoaded
  };
}
