"use client"

import { useState } from "react"
import Image from "next/image"
import { useRouter } from "next/navigation"
import { ArrowLeft, Sparkles, Printer, Wand2, Search, X, Plus, Edit3, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Carousel, CarouselContent, CarouselItem, CarouselNext, CarouselPrevious } from "@/components/ui/carousel"
import Link from "next/link"
import { cn } from "@/lib/utils"
import { items } from "@/data/items"
import type { Item, ItemType } from "@/lib/types"
import { LogoutButton } from "@/components/logout-button"
import { generateSticker } from "@/lib/actions/generate"

type SelectedElements = {
  character: Item | null
  activity: Item | null
  location: Item | null
}

type CustomPrompts = {
  character: string
  activity: string
  location: string
}

export default function CharacterSelector() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<ItemType>("character")
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedCategories, setSelectedCategories] = useState<string[]>([])
  const [isGenerating, setIsGenerating] = useState(false)
  // Update the state type for generated images to handle base64 strings
  const [generatedImageUrls, setGeneratedImageUrls] = useState<string[]>([])
  const [selectedImage, setSelectedImage] = useState<string | null>(null)
  // const [customPrompt, setCustomPrompt] = useState("")
  const [selectedElements, setSelectedElements] = useState<SelectedElements>({
    character: null,
    activity: null,
    location: null,
  })
  const [customPrompts, setCustomPrompts] = useState<CustomPrompts>({
    character: "",
    activity: "",
    location: "",
  })
  const [isCustomMode, setIsCustomMode] = useState<{[key in ItemType]: boolean}>({
    character: false,
    activity: false,
    location: false,
  })
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null)

  // Get unique categories for current tab
  const currentTabItems = items.filter(item => item.type === activeTab)
  const availableCategories = [...new Set(currentTabItems.map(item => item.category))].sort()
  // Add "Custom" as a category option
  const allCategories = [...availableCategories, "Custom"]

  // Filter items by type, search query, and categories
  const filteredItems = items.filter((item) => {
    const matchesType = item.type === activeTab
    const matchesSearch = searchQuery === "" || 
      item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
    
    const matchesCategory = selectedCategories.length === 0 || selectedCategories.includes(item.category)
    
    return matchesType && matchesSearch && matchesCategory
  })

  // Show custom card only when "Custom" category is selected or no categories are selected
  const showCustomCard = selectedCategories.length === 0 || selectedCategories.includes("Custom")

  // Clear search and filters when switching tabs
  const handleTabChange = (value: ItemType) => {
    setActiveTab(value)
    setSearchQuery("")
    setSelectedCategories([]) // Reset category filters when switching tabs
  }

  // Toggle category filter
  const toggleCategory = (category: string) => {
    setSelectedCategories(prev => 
      prev.includes(category) 
        ? prev.filter(c => c !== category)
        : [...prev, category]
    )
  }

  // Clear all filters
  const clearFilters = () => {
    setSelectedCategories([])
    setSearchQuery("")
  }

  // Reset everything - selections, custom prompts, filters, and generated images
  const resetEverything = () => {
    setSelectedElements({
      character: null,
      activity: null,
      location: null,
    })
    setCustomPrompts({
      character: "",
      activity: "",
      location: "",
    })
    setIsCustomMode({
      character: false,
      activity: false,
      location: false,
    })
    setSelectedCategories([])
    setSearchQuery("")
    setGeneratedImageUrls([])
    setSelectedImage(null)
    setActiveTab("character")
  }

  const handleItemSelect = (item: Item) => {
      // Scroll to top smoothly
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });

    // Clear custom mode when selecting a predefined item
    setIsCustomMode(prev => ({ ...prev, [item.type]: false }))
    setCustomPrompts(prev => ({ ...prev, [item.type]: "" }))

    setSelectedElements((prev) => ({
      ...prev,
      [item.type]: item,
    }))

    // Trigger selection effect
    setSelectedItemId(item.id)
    // Reset after animation duration
    setTimeout(() => setSelectedItemId(null), 1000)

    // Automatically switch to activity tab after character selection
    if (item.type === "character") {
      setTimeout(() => {
        setActiveTab("activity")
      }, 500) // Wait for the selection animation to complete
    }
    // Optionally, switch to location tab after activity selection
    else if (item.type === "activity") {
      setTimeout(() => {
        setActiveTab("location")
      }, 500)
    }
  }

  const handleCustomSelect = (type: ItemType) => {
    // Clear predefined selection when going custom
    setSelectedElements(prev => ({ ...prev, [type]: null }))
    setIsCustomMode(prev => ({ ...prev, [type]: true }))
    
    // Scroll to top smoothly
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  }

  const handleCustomPromptChange = (type: ItemType, value: string) => {
    setCustomPrompts(prev => ({ ...prev, [type]: value }))
  }

  // Format character prompts automatically
  const getFormattedPrompt = (type: ItemType, value: string) => {
    if (type === "character" && value.trim()) {
      // For characters, wrap single words in the friendly template
      const trimmedValue = value.trim()
      // Check if it's a single word (no spaces) or if user wants the template
      if (!trimmedValue.toLowerCase().startsWith("a ") && !trimmedValue.includes(" ")) {
        return `A friendly cute ${trimmedValue.toLowerCase()}`
      }
      // If user typed multiple words or starts with "a", use as-is
      return trimmedValue
    }
    return value
  }

  const handleCustomPromptSave = (type: ItemType) => {
    if (customPrompts[type].trim()) {
      // Clear category filters before auto-advancing to prevent "Custom" filter carrying over
      setSelectedCategories([])
      
      // Auto-advance to next tab like regular selection
      if (type === "character") {
        setTimeout(() => setActiveTab("activity"), 300)
      } else if (type === "activity") {
        setTimeout(() => setActiveTab("location"), 300)
      }
    }
  }

  const handleGenerate = async () => {
    if (!canGenerate) return

    setIsGenerating(true)
    setGeneratedImageUrls([])
    setSelectedImage(null)

    try {
      const description = {
        character: selectedElements.character?.description || getFormattedPrompt("character", customPrompts.character),
        activity: selectedElements.activity?.description || getFormattedPrompt("activity", customPrompts.activity),
        location: selectedElements.location?.description || getFormattedPrompt("location", customPrompts.location),
      };
      const result = await generateSticker(description)

      if (result.error) throw new Error(result.error)

      setGeneratedImageUrls(result.presignedUrls ?? [])
    } catch (error) {
      console.error("Generation failed:", error instanceof Error ? error.message : "Unknown error")
    } finally {
      setIsGenerating(false)
    }
  }

  // Cleanup object URLs when component unmounts
  // useEffect(() => {
  //   return () => {
  //     generatedImageUrls.forEach((url) => URL.revokeObjectURL(url))
  //   }
  // }, [generatedImageUrls])

  // Update the print handler to use the base64 data
  const handlePrint = () => {
    if (!selectedImage) return

    const params = new URLSearchParams({ image: selectedImage })
    router.push(`/print?${params.toString()}`)
  }

  // Only enable generate when all three elements are selected (either predefined or custom)
  const canGenerate = (selectedElements.character || customPrompts.character.trim()) && 
                     (selectedElements.activity || customPrompts.activity.trim()) && 
                     (selectedElements.location || customPrompts.location.trim())
  const canPrint = selectedImage !== null

  return (
    <div className="min-h-screen bg-gradient-to-br from-violet-600 via-indigo-700 to-purple-800">
      <header className="border-b border-white/10 bg-white/5 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between p-4">
          <div className="flex items-center gap-4">
            <Link href="/">
              <Button variant="ghost" size="icon" className="text-white hover:bg-white/10">
                <ArrowLeft className="h-5 w-5" />
              </Button>
            </Link>
            <h1 className="text-lg font-semibold text-white">Design studio</h1>
          </div>
          
          <div className="flex items-center gap-2">
            {/* Reset Button - only show if there's something to reset */}
            {(selectedElements.character || selectedElements.activity || selectedElements.location || 
              customPrompts.character || customPrompts.activity || customPrompts.location ||
              selectedCategories.length > 0 || searchQuery || generatedImageUrls.length > 0) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={resetEverything}
                className="text-white/60 hover:text-white hover:bg-white/10 gap-2"
              >
                <RotateCcw className="h-4 w-4" />
                <span className="hidden sm:inline">Reset all</span>
              </Button>
            )}
            <LogoutButton />
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-6 p-6 lg:grid-cols-[240px,1fr,400px]">
        {/* Compact Filters Sidebar */}
        <div className="space-y-4 rounded-xl border border-white/10 bg-white/5 p-4 backdrop-blur-sm lg:block hidden">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-white">Categories</h3>
            {selectedCategories.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearFilters}
                className="h-6 px-2 text-xs text-white/60 hover:text-white hover:bg-white/10"
              >
                <X className="h-3 w-3" />
              </Button>
            )}
          </div>

          {/* Categories Filter */}
          <div className="space-y-1">
            {allCategories.map((category) => {
              const count = category === "Custom" 
                ? (customPrompts[activeTab] ? 1 : 0)
                : currentTabItems.filter(item => item.category === category).length
              const isSelected = selectedCategories.includes(category)
              return (
                <button
                  key={category}
                  onClick={() => toggleCategory(category)}
                  className={cn(
                    "flex w-full items-center justify-between rounded px-3 py-2 text-left text-sm transition-colors",
                    isSelected 
                      ? "bg-white/20 text-white" 
                      : "text-white/70 hover:bg-white/10 hover:text-white"
                  )}
                >
                  <span>{category}</span>
                  <span className="text-xs text-white/50">({count})</span>
                </button>
              )
            })}
          </div>

          {/* Results Count */}
          {(selectedCategories.length > 0 || searchQuery) && (
            <div className="rounded bg-white/10 px-3 py-2 text-center">
              <p className="text-xs text-white/70">
                {filteredItems.length} of {currentTabItems.length} {activeTab}s
              </p>
            </div>
          )}
        </div>

        {/* Main Content */}
        <div className="space-y-6">
          <Tabs value={activeTab} onValueChange={(value: string) => handleTabChange(value as ItemType)} className="w-full">
            <TabsList className="grid w-full grid-cols-3 bg-white/10">
              <TabsTrigger value="character" className="text-white data-[state=active]:bg-white/20">
                CHARACTER
              </TabsTrigger>
              <TabsTrigger value="activity" className="text-white data-[state=active]:bg-white/20">
                ACTIVITY
              </TabsTrigger>
              <TabsTrigger value="location" className="text-white data-[state=active]:bg-white/20">
                LOCATION
              </TabsTrigger>
            </TabsList>
          </Tabs>

          {/* Search Bar */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-white/60" />
            <Input
              type="text"
              placeholder={`Search ${activeTab === 'activity' ? 'activities' : `${activeTab}s`}...`}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 bg-white/10 border-white/20 text-white placeholder:text-white/60 focus:bg-white/20 focus:border-white/40"
            />
          </div>

          {/* Items Grid */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filteredItems.map((item) => (
              <button
                key={item.id}
                className={cn(
                  "group relative overflow-hidden rounded-xl bg-white/5 p-4 text-left transition-all duration-300",
                  selectedElements[item.type]?.id === item.id &&
                    "ring-2 ring-white ring-offset-2 ring-offset-purple-700",
                  // Street Fighter style selection effect
                  selectedItemId === item.id && [
                    "after:absolute after:inset-0 after:animate-[pulse_0.5s_ease-in-out_infinite]",
                    "after:bg-gradient-to-r after:from-yellow-500/40 after:via-purple-500/40 after:to-pink-500/40",
                    "before:absolute before:inset-0 before:animate-[flash_0.2s_ease-in-out_3]",
                    "before:bg-white/30",
                  ],
                )}
                onClick={() => handleItemSelect(item)}
              >
                <div className="mb-4 aspect-square overflow-hidden rounded-lg">
                  <Image
                    src={item.image || "/placeholder.svg"}
                    alt={item.name}
                    width={400}
                    height={400}
                    className="h-full w-full object-cover transition-transform group-hover:scale-105"
                  />
                </div>
                <div className="space-y-1">
                  <h3 className="font-medium text-white">{item.name}</h3>
                  <p className="text-sm text-white/60">{item.category}</p>
                </div>
                <div className="absolute right-4 top-4 rounded-full bg-white/10 p-2 opacity-0 transition-opacity group-hover:opacity-100">
                  <Sparkles className="h-4 w-4 text-white" />
                </div>
              </button>
            ))}

            {/* Custom Prompt Card */}
            {showCustomCard && (
              !isCustomMode[activeTab] ? (
                <button
                  className={cn(
                    "group relative overflow-hidden rounded-xl bg-gradient-to-br from-purple-500/20 to-blue-500/20 p-4 text-left transition-all duration-300 border-2 border-dashed border-white/30 hover:border-white/50",
                    customPrompts[activeTab] && "ring-2 ring-purple-400 ring-offset-2 ring-offset-purple-700"
                  )}
                  onClick={() => handleCustomSelect(activeTab)}
                >
                  <div className="mb-4 aspect-square flex items-center justify-center rounded-lg bg-white/10">
                    {customPrompts[activeTab] ? (
                      <Edit3 className="h-12 w-12 text-white/80" />
                    ) : (
                      <Plus className="h-12 w-12 text-white/60" />
                    )}
                  </div>
                  <div className="space-y-1">
                    <h3 className="font-medium text-white">
                      {customPrompts[activeTab] ? "Edit Custom" : "Custom"}
                    </h3>
                    <p className="text-sm text-white/60">
                      {customPrompts[activeTab] 
                        ? customPrompts[activeTab].slice(0, 30) + (customPrompts[activeTab].length > 30 ? "..." : "")
                        : `Describe your own ${activeTab}`
                      }
                    </p>
                  </div>
                  <div className="absolute right-4 top-4 rounded-full bg-white/10 p-2 opacity-0 transition-opacity group-hover:opacity-100">
                    <Wand2 className="h-4 w-4 text-white" />
                  </div>
                </button>
              ) : (
                /* Custom Prompt Input Card */
                <div className="rounded-xl bg-gradient-to-br from-purple-500/20 to-blue-500/20 p-4 border-2 border-purple-400 ring-2 ring-purple-400 ring-offset-2 ring-offset-purple-700">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="font-medium text-white">Custom {activeTab}</h3>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setIsCustomMode(prev => ({ ...prev, [activeTab]: false }))}
                        className="h-6 w-6 p-0 text-white/60 hover:text-white hover:bg-white/10"
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                    
                    <Textarea
                      placeholder={activeTab === "character" 
                        ? `Enter a single word (e.g., "Bird", "Robot", "Wizard")...`
                        : `Describe your custom ${activeTab}... (e.g., "a friendly robot with blue eyes")`
                      }
                      value={customPrompts[activeTab]}
                      onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => handleCustomPromptChange(activeTab, e.target.value)}
                      onKeyDown={(e: React.KeyboardEvent<HTMLTextAreaElement>) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault()
                          handleCustomPromptSave(activeTab)
                        }
                      }}
                      className="min-h-[100px] bg-white/10 border-white/20 text-white placeholder:text-white/50 focus:bg-white/20 focus:border-white/40 resize-none"
                      autoFocus
                    />
                    
                    {/* Preview for character formatting */}
                    {activeTab === "character" && customPrompts[activeTab] && (
                      <div className="rounded bg-white/10 p-2">
                        <p className="text-xs text-white/60 mb-1">Preview:</p>
                        <p className="text-sm text-white/80 italic">
                          &quot;{getFormattedPrompt("character", customPrompts[activeTab])}&quot;
                        </p>
                      </div>
                    )}
                    
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={() => handleCustomPromptSave(activeTab)}
                        disabled={!customPrompts[activeTab].trim()}
                        className="bg-white/20 text-white hover:bg-white/30 disabled:opacity-50"
                      >
                        Save
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setIsCustomMode(prev => ({ ...prev, [activeTab]: false }))
                          setCustomPrompts(prev => ({ ...prev, [activeTab]: "" }))
                        }}
                        className="text-white/60 hover:text-white hover:bg-white/10"
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                </div>
              )
            )}
          </div>
        </div>

        {/* Preview Panel */}
        <div className="space-y-6 rounded-xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm">
          <div className="space-y-4">

            {/* Custom Prompt Input 
            <div className="relative space-y-3 rounded-xl border-2 border-white/20 bg-gradient-to-r from-purple-500/10 via-blue-500/10 to-purple-500/10 p-4 shadow-[0_0_25px_-5px_rgba(147,51,234,0.3)]">
              <div className="flex items-center justify-between">
                <label htmlFor="prompt" className="block text-sm font-medium text-white">
                  Customize Your Sticker
                </label>
                <span className="inline-flex items-center rounded-full bg-purple-500/20 px-2 py-1 text-xs font-medium text-purple-200">
                  AI Powered
                </span>
              </div>

              <div className="relative">
                <div className="relative flex items-center gap-2 overflow-hidden rounded-lg border-2 border-white/30 bg-white/10 px-3 py-3 backdrop-blur-sm transition-all duration-300 focus-within:border-purple-400 focus-within:bg-white/20 focus-within:shadow-[0_0_15px_-3px_rgba(147,51,234,0.4)]">
                  <MessageSquare className="h-5 w-5 text-purple-200" />
                  <input
                    id="prompt"
                    type="text"
                    placeholder="Describe additional details for your sticker..."
                    value={customPrompt}
                    onChange={(e) => setCustomPrompt(e.target.value)}
                    className="flex-1 bg-transparent text-sm text-white placeholder:text-white/40 focus:outline-none"
                  />
                </div>
                 Decorative elements 
                <div className="absolute -left-3 -top-3 h-6 w-6 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 opacity-40 blur-lg" />
                <div className="absolute -bottom-3 -right-3 h-6 w-6 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 opacity-40 blur-lg" />
              </div>

              <div className="flex items-start gap-2 text-xs text-white/60">
                <Sparkles className="h-4 w-4 text-purple-300" />
                <p>Enhance your sticker by adding specific details like style, mood, or special effects</p>
              </div>
            </div> */}

            <div className="space-y-4">
              <h3 className="font-medium text-white">Selected elements</h3>
              <div className="grid grid-cols-3 gap-2">
                <div className="rounded-lg border border-white/10 bg-white/5 p-3 text-center">
                  <p className="text-sm text-white/60">Character</p>
                  <p className="text-sm font-medium text-white">
                    {selectedElements.character?.name || 
                     (customPrompts.character ? "Custom" : "None")}
                  </p>
                  {customPrompts.character && (
                    <p className="text-xs text-white/50 mt-1 truncate">
                      {customPrompts.character.slice(0, 20)}...
                    </p>
                  )}
                </div>
                <div className="rounded-lg border border-white/10 bg-white/5 p-3 text-center">
                  <p className="text-sm text-white/60">Activity</p>
                  <p className="text-sm font-medium text-white">
                    {selectedElements.activity?.name || 
                     (customPrompts.activity ? "Custom" : "None")}
                  </p>
                  {customPrompts.activity && (
                    <p className="text-xs text-white/50 mt-1 truncate">
                      {customPrompts.activity.slice(0, 20)}...
                    </p>
                  )}
                </div>
                <div className="rounded-lg border border-white/10 bg-white/5 p-3 text-center">
                  <p className="text-sm text-white/60">Location</p>
                  <p className="text-sm font-medium text-white">
                    {selectedElements.location?.name || 
                     (customPrompts.location ? "Custom" : "None")}
                  </p>
                  {customPrompts.location && (
                    <p className="text-xs text-white/50 mt-1 truncate">
                      {customPrompts.location.slice(0, 20)}...
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Generate Button - Updated to match the new styling */}
            <Button
                onClick={handleGenerate}
                disabled={!canGenerate || isGenerating}
                className={cn(
                    "relative w-full overflow-hidden border-2 border-transparent bg-gradient-to-r from-purple-500 to-blue-500 text-white transition-all hover:from-purple-600 hover:to-blue-600",
                    !canGenerate && "opacity-50 cursor-not-allowed",
                    "before:absolute before:inset-0 before:bg-gradient-to-r before:from-transparent before:via-white/10 before:to-transparent before:translate-x-[-200%] hover:before:translate-x-[200%] before:transition-transform before:duration-1000",
                )}
            >
              <span className="relative flex items-center justify-center gap-2">
                <Wand2 className="h-4 w-4"/>
                {isGenerating ? "Generating..." : "Generate sticker"}
              </span>
            </Button>

          </div>

          {/* Preview Content */}
          {isGenerating ? (
              <div
                  className="flex aspect-square flex-col items-center justify-center rounded-lg bg-gradient-to-br from-purple-400/20 to-blue-400/20 p-8">
                <div className="h-12 w-12 animate-spin rounded-full border-4 border-white/10 border-t-white"/>
                <p className="mt-4 text-sm text-white/70">Generating your sticker...</p>
              </div>
          ) : (generatedImageUrls && generatedImageUrls.length > 0) ? (
              <Carousel className="w-full">
                <CarouselContent>
                  {generatedImageUrls.map((imageUrl, index) => (
                      <CarouselItem key={index}>
                        <button
                            className={cn(
                                "relative aspect-square w-full overflow-hidden rounded-lg",
                                selectedImage === imageUrl && "ring-2 ring-white",
                            )}
                            onClick={() => setSelectedImage(imageUrl)}
                        >
                          {/* Use a regular img tag for object URLs */}
                      <img
                        src={imageUrl || "/placeholder.svg"}
                        alt={`Generated sticker ${index + 1}`}
                        className="h-full w-full object-cover"
                      />
                    </button>
                  </CarouselItem>
                ))}
              </CarouselContent>
              <CarouselPrevious className="border-white/10 text-white hover:bg-white/10" />
              <CarouselNext className="border-white/10 text-white hover:bg-white/10" />
            </Carousel>
          ) : (
            <div className="aspect-square rounded-lg bg-gradient-to-br from-purple-400/20 to-blue-400/20 p-8">
              <div className="flex h-full w-full flex-col items-center justify-center rounded-lg bg-white/5 text-center">
                <Wand2 className="mb-4 h-8 w-8 text-white/40" />
                <p className="text-sm text-white/60">
                  {canGenerate ? "Click Generate to create your sticker" : "Select one item from each category"}
                </p>
              </div>
            </div>
          )}

          {/* Print Button */}
          {/* Update the button in the JSX */}
          <Button
            className="mt-6 w-full bg-white text-purple-900 hover:bg-white/90"
            onClick={handlePrint}
            disabled={!canPrint}
          >
            <Printer className="mr-2 h-4 w-4" />
            Print selected
          </Button>
        </div>
      </div>
    </div>
  )
}

