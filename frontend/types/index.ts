export interface AIAnalysis {
  composition: string
  lighting: string
  pose_anatomy: string
  costume_structure: string
  palette: string[]
  tags: string[]
  analysis_model?: string
}

export type SourceType = 'local_upload' | 'instagram' | 'pixiv' | 'web_bookmark' | 'external_url'

export interface MediaItem {
  id: string
  file_path: string
  source_type: SourceType
  ai_analysis_policy?: 'allowed' | 'blocked' | 'unlisted' | 'unknown'
  title?: string
  original_file_name?: string
  source_url?: string
  author_name?: string
  favicon_url?: string
  folder_name?: string
  width: number
  height: number
  aspect_ratio: number
  board_id?: string
  pixiv_illust_id?: string
  created_at?: string
  ai_analysis?: AIAnalysis | null
}

export interface BookmarkItem {
  id: string
  title: string
  file_path: string
  source_type: SourceType
  ai_analysis_policy?: 'allowed' | 'blocked' | 'unlisted' | 'unknown'
  source_url?: string
  author_name?: string
  favicon_url?: string
  width: number
  height: number
  aspect_ratio: number
  folder_name?: string
  board_id?: string
  created_at?: string
  ai_analysis?: AIAnalysis | null
}

export interface FolderItem {
  id?: string
  name: string
  icon: string
  color: string
  count: number
}

export interface CanvasItem {
  id: string
  board_id: string
  media_item_id: string
  pos_x: number
  pos_y: number
  width: number
  height: number
  rotation: number
  z_index: number
  is_flipped_h: boolean
  is_flipped_v: boolean
  is_grayscale: boolean
  opacity: number
  border_color: string
  border_width: number
  is_locked: boolean
  caption?: string
  media?: MediaItem
  ai_analysis?: AIAnalysis | null
}

export interface Board {
  id: string
  title: string
  description?: string
  thumbnail_url?: string
  viewport_x: number
  viewport_y: number
  viewport_zoom: number
  /** キャンバス背景パターン（名称は互換性のため dark- 接頭辞のまま） */
  background_theme: 'dark-grid' | 'dark-dots' | 'dark-plain'
  item_count?: number
  items?: CanvasItem[]
  created_at?: string
  updated_at?: string
}

/** /auth/me が返すログインユーザー */
export interface AuthUser {
  id: string
  email: string
  username: string
  avatar_url?: string | null
  instagram_connected: boolean
  pixiv_connected: boolean
  pixiv_username?: string | null
}

export interface InstagramMediaPost {
  id: string
  caption?: string
  media_type: string
  media_url: string
  permalink?: string
  thumbnail_url?: string
  timestamp?: string
  username?: string
}
