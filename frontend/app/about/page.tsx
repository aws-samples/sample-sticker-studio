import Image from "next/image"
import { Button } from "@/components/ui/button"
import Link from "next/link"
import { ArrowLeft, Sparkles, Cloud, Cpu, Palette } from "lucide-react"

export default function AboutPage() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-br from-violet-600 via-indigo-700 to-purple-800">
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -left-32 top-20 h-64 w-64 rounded-full bg-pink-500/20 blur-3xl" />
        <div className="absolute -right-32 top-40 h-64 w-64 rounded-full bg-blue-500/20 blur-3xl" />
        <div className="absolute bottom-20 left-40 h-64 w-64 rounded-full bg-purple-500/20 blur-3xl" />
      </div>

      <nav className="relative z-10 flex items-center gap-8 p-6 lg:px-8">
        <Link href="/" className="flex items-center gap-2 text-white">
          <Image src="/images/logo/AWS_logo.png" alt="AWS Logo" width={40} height={24} className="object-contain" />
        </Link>
        <div className="ml-auto">
          <Button variant="ghost" className="text-white hover:bg-white/10" asChild>
            <Link href="/">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Link>
          </Button>
        </div>
      </nav>

      <main className="relative z-10 mx-auto max-w-3xl px-6 py-12 lg:px-8">
        <div className="space-y-8">
          <div className="space-y-4">
            <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl">
              About the AWS Sticker Studio
            </h1>
            <p className="text-lg text-white/80">
              A serverless demo web application that lets you create personalized AWS-themed stickers by combining characters, activities, and locations — all powered by AI.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex items-start gap-3 rounded-2xl bg-white/5 p-5 backdrop-blur-sm">
              <div className="rounded-full bg-purple-500/20 p-2">
                <Cpu className="h-5 w-5 text-purple-200" />
              </div>
              <div>
                <h3 className="font-semibold text-white">Amazon Bedrock</h3>
                <p className="text-sm text-white/70">Image generation powered by Nova Canvas foundation model.</p>
              </div>
            </div>
            <div className="flex items-start gap-3 rounded-2xl bg-white/5 p-5 backdrop-blur-sm">
              <div className="rounded-full bg-blue-500/20 p-2">
                <Cloud className="h-5 w-5 text-blue-200" />
              </div>
              <div>
                <h3 className="font-semibold text-white">Serverless architecture</h3>
                <p className="text-sm text-white/70">Built with Lambda, API Gateway, ECS Fargate, and CloudFront. No need to manually scale or provision.</p>
              </div>
            </div>
            <div className="flex items-start gap-3 rounded-2xl bg-white/5 p-5 backdrop-blur-sm">
              <div className="rounded-full bg-pink-500/20 p-2">
                <Palette className="h-5 w-5 text-pink-200" />
              </div>
              <div>
                <h3 className="font-semibold text-white">Custom designs</h3>
                <p className="text-sm text-white/70">Mix and match characters, activities, and locations. You can extend for your own use-cases.</p>
              </div>
            </div>
            <div className="flex items-start gap-3 rounded-2xl bg-white/5 p-5 backdrop-blur-sm">
              <div className="rounded-full bg-indigo-500/20 p-2">
                <Sparkles className="h-5 w-5 text-indigo-200" />
              </div>
              <div>
                <h3 className="font-semibold text-white">Instant download</h3>
                <p className="text-sm text-white/70">Generate and print your stickers in seconds for memories of your events!</p>
              </div>
            </div>
          </div>

          <Link href="/create" className="inline-block">
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
        </div>
      </main>
    </div>
  )
}
