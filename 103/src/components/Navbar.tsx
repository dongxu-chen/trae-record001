'use client'

import Link from 'next/link'
import { useSession, signOut } from 'next-auth/react'
import NotificationBell from './NotificationBell'

export default function Navbar() {
  const { data: session } = useSession()

  return (
    <nav className="bg-white shadow-lg">
      <div className="container mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          <Link href="/" className="text-2xl font-bold text-blue-600">
            CodeSnippets
          </Link>

          <div className="flex items-center space-x-4">
            {session ? (
              <>
                <NotificationBell />
                <Link
                  href="/snippets/new"
                  className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition"
                >
                  New Snippet
                </Link>
                <Link
                  href="/my-snippets"
                  className="text-gray-600 hover:text-blue-600 transition"
                >
                  My Snippets
                </Link>
                <button
                  onClick={() => signOut()}
                  className="text-gray-600 hover:text-red-600 transition"
                >
                  Logout
                </button>
                <span className="text-gray-700">
                  {session.user?.name || session.user?.email}
                </span>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  className="text-gray-600 hover:text-blue-600 transition"
                >
                  Login
                </Link>
                <Link
                  href="/register"
                  className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition"
                >
                  Register
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
