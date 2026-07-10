export type ItemType = "character" | "activity" | "location"

export interface Item {
  id: number
  name: string
  category: string
  type: ItemType
  image: string
  description: string
  tags: string[]
}

