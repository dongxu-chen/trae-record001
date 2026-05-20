import { ref, computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import hljs from 'highlight.js'

export function useSafeMarkdown() {
  const htmlContent = ref('')
  const viewerVisible = ref(false)
  const viewerSrc = ref('')
  const viewerAlt = ref('')

  const renderMarkdown = (markdown: string) => {
    const renderer = new marked.Renderer()

    const originalImage = renderer.image.bind(renderer)
    renderer.image = (href, title, text) => {
      return `
        <figure class="my-6 group cursor-pointer" onclick="window.dispatchEvent(new CustomEvent('imageClick', { detail: { src: '${href}', alt: '${text}' } }))">
          <div class="relative overflow-hidden rounded-lg">
            <img
              src="${href}"
              alt="${text}"
              title="${title || text}"
              loading="lazy"
              class="w-full h-auto rounded-lg shadow-md group-hover:shadow-xl transition-shadow duration-300"
            />
            <div class="absolute inset-0 flex items-center justify-center bg-black/0 group-hover:bg-black/10 transition-colors duration-300">
              <svg class="w-12 h-12 text-white opacity-0 group-hover:opacity-100 transition-opacity duration-300 drop-shadow-lg" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
              </svg>
            </div>
          </div>
          ${text ? `<figcaption class="text-center text-sm text-gray-500 dark:text-gray-400 mt-2">${text}</figcaption>` : ''}
        </figure>
      `
    }

    marked.setOptions({
      renderer,
      highlight: (code, lang) => {
        if (lang && hljs.getLanguage(lang)) {
          return hljs.highlight(code, { language: lang }).value
        }
        return hljs.highlightAuto(code).value
      },
    })

    const rawHtml = marked(markdown) as string
    htmlContent.value = DOMPurify.sanitize(rawHtml, {
      USE_PROFILES: { html: true },
      ALLOWED_TAGS: [
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'p', 'br', 'hr',
        'ul', 'ol', 'li',
        'blockquote',
        'a', 'img', 'figure', 'figcaption',
        'strong', 'em', 'code', 'pre',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'div', 'span', 'svg', 'path',
      ],
      ALLOWED_ATTR: [
        'href', 'target', 'rel',
        'src', 'alt', 'title', 'loading',
        'class', 'id', 'style', 'onclick',
        'fill', 'stroke', 'viewBox', 'stroke-width', 'stroke-linecap', 'stroke-linejoin',
      ],
      ALLOW_DATA_ATTR: false,
    })
  }

  const closeViewer = () => {
    viewerVisible.value = false
  }

  return {
    htmlContent,
    viewerVisible,
    viewerSrc,
    viewerAlt,
    renderMarkdown,
    closeViewer,
  }
}
