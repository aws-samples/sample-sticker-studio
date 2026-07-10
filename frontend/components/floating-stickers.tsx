"use client"

import Image from "next/image"
import { useRef, useState, useCallback, type MouseEvent } from "react"

const stickers = [
  { src: "/images/stickers/sticker-1.png", alt: "Floating sticker 1", className: "absolute left-0 top-0 h-36 w-36 animate-float-slow" },
  { src: "/images/stickers/sticker-4.png", alt: "Floating sticker 4", className: "absolute right-0 top-0 h-36 w-36 animate-float-slow" },
  { src: "/images/stickers/sticker-5.png", alt: "Floating sticker 5", className: "absolute left-10 top-40 h-36 w-36 animate-float-slow" },
  { src: "/images/stickers/sticker-6.png", alt: "Floating sticker 6", className: "absolute right-20 bottom-[35%] h-36 w-36 animate-float-slow" },
  { src: "/images/stickers/sticker-3.png", alt: "Floating sticker 3", className: "absolute bottom-0 left-0 h-36 w-36 animate-float-fast" },
  { src: "/images/stickers/sticker-2.png", alt: "Floating sticker 2", className: "absolute bottom-0 right-0 h-36 w-36 animate-float-medium" },
]

const RADIUS = 200
const STRENGTH = 30

export function FloatingStickers() {
  const containerRef = useRef<HTMLDivElement>(null)
  const stickerRefs = useRef<(HTMLDivElement | null)[]>([])
  const [offsets, setOffsets] = useState<{ x: number; y: number }[]>(stickers.map(() => ({ x: 0, y: 0 })))

  const handleMouseMove = useCallback((e: MouseEvent) => {
    const container = containerRef.current
    if (!container) return
    const rect = container.getBoundingClientRect()
    const mx = e.clientX - rect.left
    const my = e.clientY - rect.top

    setOffsets(
      stickerRefs.current.map((el) => {
        if (!el) return { x: 0, y: 0 }
        const sr = el.getBoundingClientRect()
        const cx = sr.left - rect.left + sr.width / 2
        const cy = sr.top - rect.top + sr.height / 2
        const dx = cx - mx
        const dy = cy - my
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist > RADIUS || dist === 0) return { x: 0, y: 0 }
        const force = (1 - dist / RADIUS) * STRENGTH
        return { x: (dx / dist) * force, y: (dy / dist) * force }
      })
    )
  }, [])

  const handleMouseLeave = useCallback(() => {
    setOffsets(stickers.map(() => ({ x: 0, y: 0 })))
  }, [])

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className="relative aspect-square w-full max-w-lg"
    >
      {stickers.map((s, i) => (
        <div
          key={s.src}
          ref={(el) => { stickerRefs.current[i] = el }}
          className={s.className}
          style={{
            translate: `${offsets[i].x}px ${offsets[i].y}px`,
            transition: "translate 0.3s ease-out",
          }}
        >
          <Image src={s.src} alt={s.alt} fill className="object-contain" />
        </div>
      ))}
    </div>
  )
}
