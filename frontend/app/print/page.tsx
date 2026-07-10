"use client"

import { Suspense, useRef } from "react"
import { useSearchParams } from "next/navigation"
import { ArrowLeft, Download, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import Link from "next/link"
import { LogoutButton } from "@/components/logout-button"

function isValidImageUrl(url: string | null): boolean {
  if (!url) return false;
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

function PrintContent() {
  const searchParams = useSearchParams()
  const imageUrl = searchParams.get("image")
  const validImage = isValidImageUrl(imageUrl)
  const printRef = useRef<HTMLDivElement>(null)

  const handleDownload = async () => {
    if (!imageUrl) return
    try {
      const response = await fetch(imageUrl)
      const blob = await response.blob()
      const downloadLink = document.createElement('a')
      downloadLink.href = URL.createObjectURL(blob)
      downloadLink.download = 'aws-sticker.png'
      document.body.appendChild(downloadLink)
      downloadLink.click()
      document.body.removeChild(downloadLink)
      URL.revokeObjectURL(downloadLink.href)
    } catch (error) {
      console.error('Error downloading image')
    }
  }

  if (!imageUrl || !validImage) {
    return (
      <div className="relative z-10 flex min-h-screen flex-col items-center justify-center space-y-6 p-6">
        <div className="rounded-full bg-white/10 p-4 backdrop-blur-sm">
          <Download className="h-12 w-12 text-white/70" />
        </div>
        <h1 className="text-4xl font-bold tracking-tight text-white">
          No sticker selected
        </h1>
        <p className="text-center text-lg text-white/80">
          Please go back and select a sticker to download
        </p>
        <Link href="/">
          <Button
            size="lg"
            className="group relative overflow-hidden bg-white px-8 py-6 text-lg font-semibold text-purple-900 transition-transform hover:scale-105 active:scale-95"
          >
            <span className="relative z-10 flex items-center gap-2">
              Return to home page
              <ArrowLeft className="h-5 w-5" />
            </span>
            <div className="absolute inset-0 z-0 bg-gradient-to-r from-purple-500 to-indigo-500 opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
          </Button>
        </Link>
      </div>
    )
  }

  return (
    <>
      <nav className="relative z-10 flex items-center justify-between p-6 lg:px-8">
        <div className="flex items-center gap-4">
          <Link href="/">
            <Button variant="ghost" className="text-white hover:bg-white/10">
              <ArrowLeft className="mr-2 h-5 w-5" />
              Back to home page
            </Button>
          </Link>
        </div>
        <LogoutButton />
      </nav>

      <main className="relative z-10 mx-auto max-w-7xl px-6 py-12 lg:px-8">
        <div className="grid gap-12 lg:grid-cols-2 lg:gap-8">
          <div className="flex flex-col justify-center space-y-8">
            <div className="space-y-4">
              <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-1 text-sm font-medium text-white backdrop-blur-sm">
                <Download className="h-4 w-4" />
                Ready to download
              </div>
              <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl">
                Your AWS sticker
                <span className="block bg-gradient-to-r from-pink-300 via-purple-300 to-indigo-300 bg-clip-text text-transparent">
                  Is ready
                </span>
              </h1>
              <p className="text-lg text-white/80">
                Your custom sticker is ready to download.
              </p>
              <Button
                onClick={handleDownload}
                className="group relative overflow-hidden bg-white px-8 py-6 text-lg font-semibold text-purple-900 transition-transform hover:scale-105 active:scale-95"
              >
                <span className="relative z-10 flex items-center gap-2">
                  Download sticker
                  <Download className="h-5 w-5" />
                </span>
                <div className="absolute inset-0 z-0 bg-gradient-to-r from-purple-500 to-indigo-500 opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
              </Button>
            </div>
          </div>

          <div ref={printRef} className="flex items-center justify-center">
            <div className="overflow-hidden rounded-xl bg-white/10 p-6 backdrop-blur-sm">
              <img
                src={imageUrl}
                alt="Your AWS Sticker"
                className="h-auto w-full rounded-lg"
                style={{ maxWidth: '100%', height: 'auto' }}
              />
            </div>
          </div>
        </div>
      </main>
    </>
  )
}

export default function PrintPage() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-br from-violet-600 via-indigo-700 to-purple-800">
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -left-32 top-20 h-64 w-64 rounded-full bg-pink-500/20 blur-3xl" />
        <div className="absolute -right-32 top-40 h-64 w-64 rounded-full bg-blue-500/20 blur-3xl" />
        <div className="absolute bottom-20 left-40 h-64 w-64 rounded-full bg-purple-500/20 blur-3xl" />
      </div>
      <Suspense fallback={
        <div className="relative z-10 flex min-h-screen items-center justify-center">
          <Loader2 className="h-12 w-12 text-white animate-spin" />
        </div>
      }>
        <PrintContent />
      </Suspense>
    </div>
  )
}
