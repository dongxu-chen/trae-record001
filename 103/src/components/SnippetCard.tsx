import Link from 'next/link'

interface Snippet {
  id: string
  title: string
  description: string | null
  language: string
  createdAt: Date
  author: {
    id: string
    name: string | null
    email: string
  }
}

interface SnippetCardProps {
  snippet: Snippet
}

export default function SnippetCard({ snippet }: SnippetCardProps) {
  return (
    <Link href={`/snippets/${snippet.id}`}>
      <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow cursor-pointer">
        <div className="flex justify-between items-start mb-4">
          <h3 className="text-xl font-semibold text-gray-800">{snippet.title}</h3>
          <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2.5 py-0.5 rounded">
            {snippet.language}
          </span>
        </div>
        {snippet.description && (
          <p className="text-gray-600 mb-4 line-clamp-2">{snippet.description}</p>
        )}
        <div className="flex justify-between items-center text-sm text-gray-500">
          <span>By {snippet.author.name || snippet.author.email}</span>
          <span>{new Date(snippet.createdAt).toLocaleDateString()}</span>
        </div>
      </div>
    </Link>
  )
}
