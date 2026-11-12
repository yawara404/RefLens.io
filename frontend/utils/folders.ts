import type { FolderItem } from '~/types'

/** 特別扱いする「すべての資料」フォルダ名（DB 上の予約名） */
export const ALL_REFERENCES = 'All References'
export const ALL_REFERENCES_LABEL = 'すべての資料'
export const DEFAULT_FOLDER_COLOR = '#6366f1'

/** 画面表示用のフォルダ名 */
export function formatFolderLabel(name?: string | null): string {
  if (!name || name === ALL_REFERENCES) return ALL_REFERENCES_LABEL
  return name
}

/** フォルダ名からカラーを引く（未設定・不明は既定色） */
export function folderColorByName(folders: FolderItem[], folderName?: string | null): string {
  if (!folderName) return DEFAULT_FOLDER_COLOR
  return folders.find(f => f.name === folderName)?.color || DEFAULT_FOLDER_COLOR
}
