import Image from "next/image"
import { Button } from "@/components/ui/button"
import Link from "next/link"
import { Sparkles, Palette, Shapes, LogIn } from "lucide-react"
import { FloatingStickers } from "@/components/floating-stickers"
import { LogoutButton } from "@/components/logout-button"
import { getSession } from "@/lib/auth"

export default async function WelcomePage() {
  const session = await getSession();
  return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-br from-violet-600 via-indigo-700 to-purple-800">
      {/* Animated Background Elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -left-32 top-20 h-64 w-64 rounded-full bg-pink-500/20 blur-3xl" />
        <div className="absolute -right-32 top-40 h-64 w-64 rounded-full bg-blue-500/20 blur-3xl" />
        <div className="absolute bottom-20 left-40 h-64 w-64 rounded-full bg-purple-500/20 blur-3xl" />
      </div>

      {/* Navigation */}
      <nav className="relative z-10 flex items-center gap-8 p-6 lg:px-8">
        <div className="flex items-center gap-2 text-white">
          <Image src="/images/logo/AWS_logo.png" alt="AWS Logo" width={40} height={24} className="object-contain" />
        </div>
{/*        <div className="flex flex-col items-center gap-2">
          <div className="flex items-center gap-2">
            <Image src="/images/logo/bedrock.svg" alt="Bedrock logo" width={40} height={24}
                   className="object-contain"/>
          </div>
          <div className="flex items-center gap-2">
            <Image src="/images/logo/bedrock-text.svg" alt="Bedrock text" width={60} height={36}
                   className="object-contain"/>
          </div>
        </div>*/}
{/*        <div className="flex flex-col items-center gap-2">
          <div className="flex items-center gap-2">
            <Image src="/images/logo/nova.svg" alt="Nova logo" width={40} height={24} className="object-contain"/>
          </div>
          <div className="flex items-center gap-2">
            <Image src="/images/logo/nova-text.svg" alt="Nova text" width={55} height={28}
                   className="object-contain"/>
          </div>
        </div>*/}
        <div className="flex items-center gap-4 ml-auto">
          <Button variant="ghost" className="text-white hover:bg-white/10" asChild>
            <Link href="/about">About</Link>
          </Button>
          {session ? (
            <LogoutButton />
          ) : (
            <Button variant="ghost" className="text-white hover:bg-white/10" asChild>
              <a href="/auth/login">
                <LogIn className="mr-2 h-4 w-4" />
                Login
              </a>
            </Button>
          )}
        </div>
      </nav>

      {/* Main Content */}
      <main className="relative z-10 mx-auto max-w-7xl px-6 py-12 lg:px-8">
        <div className="grid gap-12 lg:grid-cols-2 lg:gap-8">
          {/* Left Column */}
          <div className="flex flex-col justify-center space-y-8">
            <div className="space-y-4">
              <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-1 text-sm font-medium text-white backdrop-blur-sm">
                <Sparkles className="h-4 w-4" />
                Create unique stickers with AI
              </div>
              <h1 className="text-4xl font-bold tracking-tight text-white sm:text-6xl">
                Design your perfect
                <span className="block bg-gradient-to-r from-pink-300 via-purple-300 to-indigo-300 bg-clip-text text-transparent">
                  AWS sticker
                </span>
              </h1>
              <p className="text-lg text-white/80">
                Unleash your creativity with our AI-powered sticker studio. Mix and match characters, activities, and
                locations to create your unique AWS-themed sticker.
              </p>
            </div>

            <Link href={session ? "/create" : "/auth/login?return_to=/create"} className="w-fit">
              <Button
                size="lg"
                className="group relative overflow-hidden bg-white px-12 py-8 text-xl font-semibold text-purple-900 transition-transform hover:scale-105 active:scale-95"
              >
                <span className="relative z-10 flex items-center gap-2">
                  Start creating
                  <Sparkles className="h-5 w-5" />
                </span>
                <div className="absolute inset-0 z-0 bg-gradient-to-r from-purple-500 to-indigo-500 opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
                <div className="absolute inset-0 -z-10 animate-pulse bg-white/50 blur-xl transition-all duration-500 group-hover:bg-purple-400/50" />
              </Button>
            </Link>

            {/* Feature List */}
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="flex items-start gap-3 rounded-2xl bg-white/5 p-4 backdrop-blur-sm">
                <div className="rounded-full bg-purple-500/20 p-2">
                  <Palette className="h-5 w-5 text-purple-200" />
                </div>
                <div>
                  <h3 className="font-semibold text-white">AI-powered design</h3>
                  <p className="text-sm text-white/70">Create unique combinations with AI assistance</p>
                </div>
              </div>
              <div className="flex items-start gap-3 rounded-2xl bg-white/5 p-4 backdrop-blur-sm">
                <div className="rounded-full bg-blue-500/20 p-2">
                  <Shapes className="h-5 w-5 text-blue-200" />
                </div>
                <div>
                  <h3 className="font-semibold text-white">Custom elements</h3>
                  <p className="text-sm text-white/70">Mix and match from our vast library</p>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column - Preview */}
          <div className="relative flex items-center justify-center lg:justify-end">
            <FloatingStickers />
          </div>
        </div>
      </main>
    </div>
  )
}

