import { NextResponse } from 'next/server'
import dbConnect from '@/lib/mongodb'
import Note from '@/models/Note'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { renderToStaticMarkup } from 'react-dom/server'
import pdf from 'html-pdf'

export async function GET(request: Request, { params }: { params: { id: string } }) {
  try {
    await dbConnect()
    const { searchParams } = new URL(request.url)
    const format = searchParams.get('format') || 'md'

    const note = await Note.findById(params.id)
    if (!note) {
      return NextResponse.json({ error: 'Note not found' }, { status: 404 })
    }

    switch (format) {
      case 'md':
        return exportMarkdown(note)
      case 'html':
        return exportHTML(note)
      case 'pdf':
        return exportPDF(note)
      default:
        return NextResponse.json({ error: 'Invalid format' }, { status: 400 })
    }
  } catch (error) {
    return NextResponse.json({ error: 'Failed to export note' }, { status: 500 })
  }
}

function exportMarkdown(note: any) {
  const content = `# ${note.title}\n\n${note.content}`
  return new NextResponse(content, {
    headers: {
      'Content-Type': 'text/markdown',
      'Content-Disposition': `attachment; filename="${encodeURIComponent(note.title)}.md"`,
    },
  })
}

function exportHTML(note: any) {
  const htmlContent = renderToStaticMarkup(
    ReactMarkdown({
      children: note.content,
      remarkPlugins: [remarkGfm],
    })
  )

  const fullHtml = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>${note.title}</title>
      <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 2rem; }
        h1 { font-size: 2rem; font-weight: 700; margin-bottom: 1rem; }
        h2 { font-size: 1.5rem; font-weight: 600; margin-bottom: 0.75rem; }
        h3 { font-size: 1.25rem; font-weight: 600; margin-bottom: 0.5rem; }
        p { margin-bottom: 1rem; line-height: 1.75; }
        ul, ol { margin-bottom: 1rem; padding-left: 1.5rem; }
        code { background-color: #f3f4f6; padding: 0.125rem 0.375rem; border-radius: 0.25rem; font-family: monospace; }
        pre { background-color: #1f2937; color: #e5e7eb; padding: 1rem; border-radius: 0.5rem; overflow-x: auto; }
        pre code { background-color: transparent; padding: 0; color: inherit; }
        blockquote { border-left: 4px solid #e5e7eb; padding-left: 1rem; color: #6b7280; font-style: italic; }
        a { color: #3b82f6; text-decoration: underline; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 1rem; }
        th, td { border: 1px solid #e5e7eb; padding: 0.5rem; text-align: left; }
        th { background-color: #f9fafb; font-weight: 600; }
        hr { border: none; border-top: 1px solid #e5e7eb; margin: 2rem 0; }
      </style>
    </head>
    <body>
      <h1>${note.title}</h1>
      ${htmlContent}
    </body>
    </html>
  `

  return new NextResponse(fullHtml, {
    headers: {
      'Content-Type': 'text/html',
      'Content-Disposition': `attachment; filename="${encodeURIComponent(note.title)}.html"`,
    },
  })
}

async function exportPDF(note: any) {
  const htmlContent = renderToStaticMarkup(
    ReactMarkdown({
      children: note.content,
      remarkPlugins: [remarkGfm],
    })
  )

  const fullHtml = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>${note.title}</title>
      <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 2rem; }
        h1 { font-size: 2rem; font-weight: 700; margin-bottom: 1rem; }
        h2 { font-size: 1.5rem; font-weight: 600; margin-bottom: 0.75rem; }
        h3 { font-size: 1.25rem; font-weight: 600; margin-bottom: 0.5rem; }
        p { margin-bottom: 1rem; line-height: 1.75; }
        ul, ol { margin-bottom: 1rem; padding-left: 1.5rem; }
        code { background-color: #f3f4f6; padding: 0.125rem 0.375rem; border-radius: 0.25rem; font-family: monospace; }
        pre { background-color: #1f2937; color: #e5e7eb; padding: 1rem; border-radius: 0.5rem; overflow-x: auto; }
        pre code { background-color: transparent; padding: 0; color: inherit; }
        blockquote { border-left: 4px solid #e5e7eb; padding-left: 1rem; color: #6b7280; font-style: italic; }
        a { color: #3b82f6; text-decoration: underline; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 1rem; }
        th, td { border: 1px solid #e5e7eb; padding: 0.5rem; text-align: left; }
        th { background-color: #f9fafb; font-weight: 600; }
        hr { border: none; border-top: 1px solid #e5e7eb; margin: 2rem 0; }
      </style>
    </head>
    <body>
      <h1>${note.title}</h1>
      ${htmlContent}
    </body>
    </html>
  `

  return new Promise((resolve) => {
    pdf.create(fullHtml).toBuffer((err, buffer) => {
      if (err) {
        resolve(NextResponse.json({ error: 'Failed to generate PDF' }, { status: 500 }))
      } else {
        resolve(
          new NextResponse(buffer, {
            headers: {
              'Content-Type': 'application/pdf',
              'Content-Disposition': `attachment; filename="${encodeURIComponent(note.title)}.pdf"`,
            },
          })
        )
      }
    })
  })
}
