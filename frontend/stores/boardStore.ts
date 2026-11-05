import { defineStore } from 'pinia'
import type { Board, CanvasItem, AIAnalysis, BookmarkItem, FolderItem } from '~/types'
import { useToast } from '~/composables/useToast'
import { useBackendUrl } from '~/composables/useBackendUrl'

const HISTORY_LIMIT = 30

export const useBoardStore = defineStore('board', {
  state: () => ({
    currentBoard: null as Board | null,
    items: [] as CanvasItem[],
    selectedItemIds: [] as string[],
    searchQuery: '',
    isSaving: false,
    isLoading: false,
    hasUnsavedChanges: false,
    history: [] as string[],
    historyIndex: -1,

    // ライブラリ（ブックマーク）管理
    bookmarks: [] as BookmarkItem[],
    folders: [] as FolderItem[],
    selectedFolder: 'All References',
    selectedSourceType: 'all',
    isBrowserOpen: false,
    quickLookItem: null as BookmarkItem | null,
    isAddingBookmark: false,

    // キャンバス中央へのスマート配置用座標とオフセットカウンタ
    viewportCenter: { x: 240, y: 180 },
    placementCascadeIndex: 0,

    /** 一度でも読み込んだことがあるか（空状態表示の抑止） */
    hasLoadedBookmarks: false,

    /** fetchBookmarks の発行順。古い応答が新しい結果を上書きしないようにする */
    bookmarkRequestSeq: 0,
  }),

  getters: {
    canUndo(state): boolean {
      return state.historyIndex > 0
    },

    canRedo(state): boolean {
      return state.historyIndex < state.history.length - 1
    },

    selectedItems(state): CanvasItem[] {
      return state.items.filter(item => state.selectedItemIds.includes(item.id))
    },

    activeItem(state): CanvasItem | null {
      if (state.selectedItemIds.length === 1) {
        return state.items.find(item => item.id === state.selectedItemIds[0]) || null
      }
      return null
    },

    /** 検索クエリに一致するアイテムのID（不一致は減光表示） */
    filteredItemIds(state): string[] {
      const q = state.searchQuery.toLowerCase().trim()
      if (!q) return state.items.map(i => i.id)

      return state.items
        .filter(item => {
          if (item.caption?.toLowerCase().includes(q)) return true

          const ai = item.ai_analysis
          if (!ai) return false
          if (ai.tags?.some(t => t.toLowerCase().includes(q))) return true
          return [ai.composition, ai.lighting, ai.pose_anatomy, ai.costume_structure]
            .some(field => field?.toLowerCase().includes(q))
        })
        .map(i => i.id)
    },

    /** ライブラリ内でフィルタリングされたブックマーク（キャンバスのsearchQueryとは独立） */
    filteredBookmarks(state): BookmarkItem[] {
      return state.bookmarks.filter(b => {
        if (state.selectedSourceType !== 'all' && state.selectedSourceType !== 'pixiv_bookmarks' && b.source_type !== state.selectedSourceType) {
          return false
        }
        if (state.selectedFolder && state.selectedFolder !== 'All References' && b.folder_name !== state.selectedFolder) {
          return false
        }
        return true
      })
    },
  },

  actions: {
    /** バックエンド API のURLを組み立てる（app.baseURL を考慮） */
    api(path: string) {
      const { apiBase } = useBackendUrl()
      return `${apiBase.value}${path}`
    },

    // -------------------------------------------------------------
    // Undo / Redo
    // -------------------------------------------------------------
    recordHistory() {
      const snapshot = JSON.stringify(this.items)
      if (this.historyIndex >= 0 && this.history[this.historyIndex] === snapshot) return

      this.history = this.history.slice(0, this.historyIndex + 1)
      this.history.push(snapshot)

      if (this.history.length > HISTORY_LIMIT) {
        this.history.shift()
      } else {
        this.historyIndex++
      }
      this.hasUnsavedChanges = true
    },

    undo() {
      if (this.historyIndex > 0) {
        this.historyIndex--
        this.items = JSON.parse(this.history[this.historyIndex])
        this.hasUnsavedChanges = true
      }
    },

    redo() {
      if (this.historyIndex < this.history.length - 1) {
        this.historyIndex++
        this.items = JSON.parse(this.history[this.historyIndex])
        this.hasUnsavedChanges = true
      }
    },

    // -------------------------------------------------------------
    // ボード
    // -------------------------------------------------------------
    async loadBoard(boardId: string) {
      this.isLoading = true
      try {
        const res = await $fetch<Board>(this.api(`/boards/${boardId}`))
        this.currentBoard = res
        this.items = res.items || []
        this.selectedItemIds = []
        this.history = [JSON.stringify(this.items)]
        this.historyIndex = 0
        this.hasUnsavedChanges = false
      } catch (e) {
        console.error('Failed to load board:', e)
        useToast().error('ボードを読み込めませんでした', 'バックエンドの接続を確認してください')
      } finally {
        this.isLoading = false
      }
    },

    /** 最初のボード（無ければ作成）を開く。Manager/View からの遷移用。 */
    async loadFirstBoard(): Promise<Board | null> {
      try {
        const boards = await $fetch<{ id: string }[]>(this.api('/boards/'))
        if (!boards?.length) return null
        await this.loadBoard(boards[0].id)
        return this.currentBoard
      } catch (e) {
        console.error('Failed to load first board:', e)
        return null
      }
    },

    async saveCanvas(viewportX: number, viewportY: number, viewportZoom: number) {
      if (!this.currentBoard) return
      this.isSaving = true

      try {
        await $fetch(this.api(`/boards/${this.currentBoard.id}/items/batch`), {
          method: 'POST',
          body: {
            viewport_x: viewportX,
            viewport_y: viewportY,
            viewport_zoom: viewportZoom,
            items: this.items.map(it => ({
              id: it.id,
              pos_x: it.pos_x,
              pos_y: it.pos_y,
              width: it.width,
              height: it.height,
              rotation: it.rotation,
              z_index: it.z_index,
              is_flipped_h: it.is_flipped_h,
              is_flipped_v: it.is_flipped_v,
              is_grayscale: it.is_grayscale,
              opacity: it.opacity,
              border_color: it.border_color,
              border_width: it.border_width,
              is_locked: it.is_locked,
              caption: it.caption,
            })),
          },
        })
        this.hasUnsavedChanges = false
      } catch (e) {
        console.error('Failed to save canvas:', e)
        useToast().error('保存に失敗しました', (e as any)?.data?.detail || (e as any)?.message)
      } finally {
        this.isSaving = false
      }
    },

    // -------------------------------------------------------------
    // ライブラリ
    // -------------------------------------------------------------
    async fetchBookmarks() {
      // 同時に走ったリクエストが古い結果を上書きしないよう、発行順を比べる。
      // （ログイン直後の再読み込みと保存直後の再取得が重なると
      //   「保存したはずが一覧から消える」症状が出る）
      const seq = ++this.bookmarkRequestSeq

      try {
        const res = await $fetch<BookmarkItem[]>(this.api('/bookmarks/'))
        if (seq !== this.bookmarkRequestSeq) return
        this.bookmarks = res || []
        this.hasLoadedBookmarks = true
      } catch (e) {
        if (seq !== this.bookmarkRequestSeq) return
        console.error('Failed to fetch bookmarks:', e)
      }
    },

    async fetchFolders() {
      try {
        this.folders = (await $fetch<FolderItem[]>(this.api('/bookmarks/folders'))) || []
      } catch (e) {
        console.error('Failed to fetch folders:', e)
      }
    },

    async createFolder(name: string, color = '#6366f1') {
      const trimmed = name.trim()
      if (!trimmed) return

      await $fetch(this.api('/bookmarks/folders'), {
        method: 'POST',
        body: { name: trimmed, color },
      })
      await this.fetchFolders()
      this.selectedFolder = trimmed
      useToast().success('フォルダを作成しました', trimmed)
    },

    /** ユーザー作成コレクションの名前を変更する（既定コレクションは対象外） */
    async renameFolder(folderId: string, name: string, color?: string) {
      const trimmed = name.trim()
      if (!trimmed) return false

      const previousName = this.folders.find(f => f.id === folderId)?.name

      try {
        await $fetch(this.api(`/bookmarks/folders/${folderId}`), {
          method: 'PUT',
          body: { name: trimmed, ...(color ? { color } : {}) },
        })
        // 表示中のコレクションをリネームした場合は選択状態も追従させる
        if (previousName && this.selectedFolder === previousName) {
          this.selectedFolder = trimmed
        }
        await Promise.all([this.fetchFolders(), this.fetchBookmarks()])
        useToast().success('コレクションを更新しました', trimmed)
        return true
      } catch (e: any) {
        useToast().error(
          'コレクション名の変更に失敗しました',
          e?.data?.detail || e?.message
        )
        return false
      }
    },

    /** ユーザー作成コレクションのカラーを変更する */
    async updateFolderColor(folderId: string, color: string) {
      const folder = this.folders.find(f => f.id === folderId)
      try {
        await $fetch(this.api(`/bookmarks/folders/${folderId}`), {
          method: 'PUT',
          body: { color },
        })
        if (folder) {
          folder.color = color
        }
        await this.fetchFolders()
        useToast().success('フォルダカラーを変更しました', folder?.name)
        return true
      } catch (e: any) {
        useToast().error(
          'フォルダカラーの変更に失敗しました',
          e?.data?.detail || e?.message
        )
        return false
      }
    },

    /** ユーザー作成コレクションを削除する（中の資料は All References へ戻す） */
    async deleteFolder(folderId: string) {
      const name = this.folders.find(f => f.id === folderId)?.name

      try {
        await $fetch(this.api(`/bookmarks/folders/${folderId}`), { method: 'DELETE' })
        if (name && this.selectedFolder === name) {
          this.selectedFolder = 'All References'
        }
        await Promise.all([this.fetchFolders(), this.fetchBookmarks()])
        useToast().success(
          'コレクションを削除しました',
          name ? `${name} の資料は All References に移動しました` : undefined
        )
        return true
      } catch (e: any) {
        useToast().error(
          'コレクションの削除に失敗しました',
          e?.data?.detail || e?.message
        )
        return false
      }
    },

    async addBookmark(
      url: string,
      folderName?: string,
      placeOnCanvas = false,
      worldX = 100,
      worldY = 100
    ) {
      const trimmed = url.trim()
      if (!trimmed) return null

      this.isAddingBookmark = true
      try {
        const res = await $fetch<{
          success: boolean
          bookmark_id: string
          canvas_item_id?: string
        }>(this.api('/bookmarks/add'), {
          method: 'POST',
          body: {
            url: trimmed,
            folder_name: folderName || this.selectedFolder,
            board_id: placeOnCanvas && this.currentBoard ? this.currentBoard.id : undefined,
            pos_x: worldX,
            pos_y: worldY,
          },
        })

        await this.fetchBookmarks()
        await this.fetchFolders()

        if (placeOnCanvas && this.currentBoard) {
          await this.loadBoard(this.currentBoard.id)
        }
        return res
      } catch (e: any) {
        useToast().error(
          'URLの保存に失敗しました',
          e?.data?.detail || e?.message || 'URLが正しいか確認してください'
        )
        return null
      } finally {
        this.isAddingBookmark = false
      }
    },

    setViewportCenter(worldX: number, worldY: number) {
      this.viewportCenter = { x: Math.round(worldX), y: Math.round(worldY) }
      this.placementCascadeIndex = 0
    },

    getNextPlacementCoords(worldX?: number, worldY?: number) {
      if (typeof worldX === 'number' && typeof worldY === 'number') {
        return { x: Math.round(worldX), y: Math.round(worldY) }
      }
      const step = (this.placementCascadeIndex % 8) * 32
      this.placementCascadeIndex++
      return {
        x: Math.round(this.viewportCenter.x - 140 + step),
        y: Math.round(this.viewportCenter.y - 140 + step),
      }
    },

    async placeBookmarkOnBoard(bookmarkId: string, worldX?: number, worldY?: number) {
      if (!this.currentBoard) return
      const coords = this.getNextPlacementCoords(worldX, worldY)
      try {
        const res = await $fetch<{ success: boolean; item: CanvasItem }>(
          this.api('/bookmarks/place-on-board'),
          {
            method: 'POST',
            body: {
              board_id: this.currentBoard.id,
              bookmark_id: bookmarkId,
              pos_x: coords.x,
              pos_y: coords.y,
            },
          }
        )
        if (res?.item) {
          this.items.push(res.item)
          this.selectedItemIds = [res.item.id]
          this.recordHistory()
        }
      } catch (e: any) {
        useToast().error('キャンバスへの配置に失敗しました', (e as any)?.data?.detail || (e as any)?.message)
      }
    },

    async moveBookmarkFolder(bookmarkId: string, folderName: string) {
      try {
        await $fetch(this.api(`/bookmarks/${bookmarkId}/folder`), {
          method: 'PUT',
          body: { folder_name: folderName },
        })
        const b = this.bookmarks.find(item => item.id === bookmarkId)
        if (b) b.folder_name = folderName
        await this.fetchFolders()
        return true
      } catch (e) {
        console.error('Move bookmark folder failed:', e)
        useToast().error('フォルダの変更に失敗しました', (e as any)?.data?.detail || (e as any)?.message)
        return false
      }
    },

    async moveBookmarksFolder(bookmarkIds: string[], folderName: string) {
      if (!bookmarkIds.length) return false
      try {
        await $fetch(this.api('/bookmarks/batch/folder'), {
          method: 'PUT',
          body: { bookmark_ids: bookmarkIds, folder_name: folderName },
        })
        for (const id of bookmarkIds) {
          const b = this.bookmarks.find(item => item.id === id)
          if (b) b.folder_name = folderName
        }
        await this.fetchFolders()
        return true
      } catch (e) {
        console.error('Batch move bookmarks failed:', e)
        useToast().error('フォルダの一括変更に失敗しました', (e as any)?.data?.detail || (e as any)?.message)
        return false
      }
    },

    async deleteBookmark(bookmarkId: string) {
      try {
        await $fetch(this.api(`/bookmarks/${bookmarkId}`), { method: 'DELETE' })
        this.bookmarks = this.bookmarks.filter(b => b.id !== bookmarkId)
        await this.fetchFolders()
        return true
      } catch (e) {
        console.error('Delete bookmark failed:', e)
        useToast().error('ブックマークの削除に失敗しました', (e as any)?.data?.detail || (e as any)?.message)
        return false
      }
    },

    async updateBookmarkTags(bookmarkId: string, tags: string[]) {
      try {
        const res = await $fetch<{ success: boolean; tags: string[] }>(
          this.api(`/bookmarks/${bookmarkId}/tags`),
          {
            method: 'PUT',
            body: { tags },
          }
        )
        const b = this.bookmarks.find(item => item.id === bookmarkId)
        if (b) {
          if (!b.ai_analysis) {
            b.ai_analysis = {
              composition: '',
              lighting: '',
              pose_anatomy: '',
              costume_structure: '',
              palette: [],
              tags: res.tags,
            }
          } else {
            b.ai_analysis.tags = res.tags
          }
        }
        if (this.quickLookItem && this.quickLookItem.id === bookmarkId) {
          if (!this.quickLookItem.ai_analysis) {
            this.quickLookItem.ai_analysis = {
              composition: '',
              lighting: '',
              pose_anatomy: '',
              costume_structure: '',
              palette: [],
              tags: res.tags,
            }
          } else {
            this.quickLookItem.ai_analysis.tags = res.tags
          }
        }
        return res.tags
      } catch (e: any) {
        console.error('Update bookmark tags failed:', e)
        useToast().error('タグの更新に失敗しました', e?.data?.detail || e?.message)
        return null
      }
    },

    async addBookmarkTag(bookmarkId: string, tag: string) {
      try {
        const res = await $fetch<{ success: boolean; tags: string[] }>(
          this.api(`/bookmarks/${bookmarkId}/tags`),
          {
            method: 'POST',
            body: { tag },
          }
        )
        const b = this.bookmarks.find(item => item.id === bookmarkId)
        if (b) {
          if (!b.ai_analysis) {
            b.ai_analysis = {
              composition: '',
              lighting: '',
              pose_anatomy: '',
              costume_structure: '',
              palette: [],
              tags: res.tags,
            }
          } else {
            b.ai_analysis.tags = res.tags
          }
        }
        if (this.quickLookItem && this.quickLookItem.id === bookmarkId) {
          if (!this.quickLookItem.ai_analysis) {
            this.quickLookItem.ai_analysis = {
              composition: '',
              lighting: '',
              pose_anatomy: '',
              costume_structure: '',
              palette: [],
              tags: res.tags,
            }
          } else {
            this.quickLookItem.ai_analysis.tags = res.tags
          }
        }
        return res.tags
      } catch (e: any) {
        console.error('Add bookmark tag failed:', e)
        useToast().error('タグの追加に失敗しました', e?.data?.detail || e?.message)
        return null
      }
    },

    async removeBookmarkTag(bookmarkId: string, tag: string) {
      try {
        const res = await $fetch<{ success: boolean; tags: string[] }>(
          this.api(`/bookmarks/${bookmarkId}/tags/${encodeURIComponent(tag)}`),
          {
            method: 'DELETE',
          }
        )
        const b = this.bookmarks.find(item => item.id === bookmarkId)
        if (b && b.ai_analysis) {
          b.ai_analysis.tags = res.tags
        }
        if (this.quickLookItem && this.quickLookItem.id === bookmarkId && this.quickLookItem.ai_analysis) {
          this.quickLookItem.ai_analysis.tags = res.tags
        }
        return res.tags
      } catch (e: any) {
        console.error('Delete bookmark tag failed:', e)
        useToast().error('タグの削除に失敗しました', e?.data?.detail || e?.message)
        return null
      }
    },

    async triggerAiAnalysis(bookmarkId: string) {
      try {
        await $fetch(this.api(`/bookmarks/${bookmarkId}/analyze`), { method: 'POST' })
        useToast().success('AI解析を開始しました', '完了後に自動でタグが反映されます')
        setTimeout(async () => {
          await this.fetchBookmarks()
          if (this.quickLookItem && this.quickLookItem.id === bookmarkId) {
            const updated = this.bookmarks.find(b => b.id === bookmarkId)
            if (updated) this.quickLookItem = updated
          }
        }, 3000)
        return true
      } catch (e: any) {
        useToast().error('AI解析の開始に失敗しました', e?.data?.detail || e?.message)
        return false
      }
    },

    toggleBrowser() {
      this.isBrowserOpen = !this.isBrowserOpen
    },

    openQuickLook(item: BookmarkItem) {
      this.quickLookItem = item
    },

    closeQuickLook() {
      this.quickLookItem = null
    },

    // -------------------------------------------------------------
    // 選択
    // -------------------------------------------------------------
    selectItem(id: string, multi = false) {
      if (multi) {
        this.selectedItemIds = this.selectedItemIds.includes(id)
          ? this.selectedItemIds.filter(i => i !== id)
          : [...this.selectedItemIds, id]
      } else {
        this.selectedItemIds = [id]
      }
    },

    selectAll() {
      this.selectedItemIds = this.items.map(i => i.id)
    },

    clearSelection() {
      this.selectedItemIds = []
    },

    // -------------------------------------------------------------
    // アイテム操作
    // -------------------------------------------------------------
    updateItem(id: string, partial: Partial<CanvasItem>, record = true) {
      const idx = this.items.findIndex(it => it.id === id)
      if (idx === -1) return
      this.items[idx] = { ...this.items[idx], ...partial }
      if (record) this.recordHistory()
    },

    toggleGrayscale(id?: string) {
      for (const tid of id ? [id] : this.selectedItemIds) {
        const item = this.items.find(i => i.id === tid)
        if (item) item.is_grayscale = !item.is_grayscale
      }
      this.recordHistory()
    },

    flipHorizontal(id?: string) {
      for (const tid of id ? [id] : this.selectedItemIds) {
        const item = this.items.find(i => i.id === tid)
        if (item) item.is_flipped_h = !item.is_flipped_h
      }
      this.recordHistory()
    },

    flipVertical(id?: string) {
      for (const tid of id ? [id] : this.selectedItemIds) {
        const item = this.items.find(i => i.id === tid)
        if (item) item.is_flipped_v = !item.is_flipped_v
      }
      this.recordHistory()
    },

    rotateSelection(degrees = 90) {
      for (const item of this.selectedItems) {
        item.rotation = (item.rotation + degrees) % 360
      }
      this.recordHistory()
    },

    alignSelected(alignment: 'left' | 'center' | 'right' | 'top' | 'middle' | 'bottom') {
      const targets = this.selectedItems.filter(it => !it.is_locked)
      if (targets.length < 2) return

      const minX = Math.min(...targets.map(it => it.pos_x))
      const maxX = Math.max(...targets.map(it => it.pos_x + it.width))
      const minY = Math.min(...targets.map(it => it.pos_y))
      const maxY = Math.max(...targets.map(it => it.pos_y + it.height))

      for (const item of targets) {
        if (alignment === 'left') {
          item.pos_x = minX
        } else if (alignment === 'center') {
          item.pos_x = Math.round((minX + maxX) / 2 - item.width / 2)
        } else if (alignment === 'right') {
          item.pos_x = maxX - item.width
        } else if (alignment === 'top') {
          item.pos_y = minY
        } else if (alignment === 'middle') {
          item.pos_y = Math.round((minY + maxY) / 2 - item.height / 2)
        } else if (alignment === 'bottom') {
          item.pos_y = maxY - item.height
        }
      }
      this.recordHistory()
      useToast().success(`資料を${alignment === 'left' ? '左' : alignment === 'right' ? '右' : alignment === 'top' ? '上' : alignment === 'bottom' ? '下' : '中央'}揃えにしました`)
    },

    distributeSelected(axis: 'horizontal' | 'vertical') {
      const targets = [...this.selectedItems.filter(it => !it.is_locked)]
      if (targets.length < 3) {
        useToast().info('等間隔配置には3つ以上の資料を選択してください')
        return
      }

      if (axis === 'horizontal') {
        targets.sort((a, b) => a.pos_x - b.pos_x)
        const first = targets[0]
        const last = targets[targets.length - 1]
        const totalSpan = (last.pos_x + last.width) - first.pos_x
        const itemsWidthSum = targets.reduce((sum, it) => sum + it.width, 0)
        const totalGap = totalSpan - itemsWidthSum
        const gap = totalGap / (targets.length - 1)

        let currX = first.pos_x
        for (const item of targets) {
          item.pos_x = Math.round(currX)
          currX += item.width + gap
        }
      } else {
        targets.sort((a, b) => a.pos_y - b.pos_y)
        const first = targets[0]
        const last = targets[targets.length - 1]
        const totalSpan = (last.pos_y + last.height) - first.pos_y
        const itemsHeightSum = targets.reduce((sum, it) => sum + it.height, 0)
        const totalGap = totalSpan - itemsHeightSum
        const gap = totalGap / (targets.length - 1)

        let currY = first.pos_y
        for (const item of targets) {
          item.pos_y = Math.round(currY)
          currY += item.height + gap
        }
      }
      this.recordHistory()
      useToast().success(`資料を${axis === 'horizontal' ? '水平均等' : '垂直均等'}に配置しました`)
    },

    arrangeSelectedGrid() {
      const targets = [...this.selectedItems.filter(it => !it.is_locked)]
      if (!targets.length) return

      targets.sort((a, b) => (a.pos_y - b.pos_y) || (a.pos_x - b.pos_x))
      const cols = Math.ceil(Math.sqrt(targets.length))
      const minX = Math.min(...targets.map(it => it.pos_x))
      const minY = Math.min(...targets.map(it => it.pos_y))
      const gap = 24

      let currX = minX
      let currY = minY
      let rowMaxH = 0

      targets.forEach((item, idx) => {
        if (idx > 0 && idx % cols === 0) {
          currX = minX
          currY += rowMaxH + gap
          rowMaxH = 0
        }
        item.pos_x = Math.round(currX)
        item.pos_y = Math.round(currY)
        item.rotation = 0
        currX += item.width + gap
        rowMaxH = Math.max(rowMaxH, item.height)
      })

      this.recordHistory()
      useToast().success(`${targets.length}件の資料をグリッド整列しました`)
    },

    async duplicateSelected() {
      if (!this.currentBoard || !this.selectedItemIds.length) return
      try {
        const res = await $fetch<{ items: CanvasItem[] }>(
          this.api(`/boards/${this.currentBoard.id}/items/duplicate`),
          {
            method: 'POST',
            body: { item_ids: this.selectedItemIds, offset_x: 36, offset_y: 36 },
          }
        )
        if (res?.items?.length) {
          this.items.push(...res.items)
          this.selectedItemIds = res.items.map(i => i.id)
          this.recordHistory()
          useToast().success(`${res.items.length}件の資料を複製しました`)
        }
      } catch (e: any) {
        console.error('Duplicate failed:', e)
        useToast().error('資料の複製に失敗しました', e?.data?.detail || e?.message)
      }
    },

    async saveCanvasItemsToFolder(itemIds: string[], folderName: string) {
      if (!this.currentBoard) return false
      const trimmed = folderName.trim() || 'All References'
      try {
        const res = await $fetch<{ success: boolean; count: number; folder_name: string; media_ids: string[] }>(
          this.api(`/boards/${this.currentBoard.id}/save-to-folder`),
          {
            method: 'POST',
            body: { folder_name: trimmed, item_ids: itemIds.length ? itemIds : undefined },
          }
        )
        if (res?.success) {
          const mediaIdSet = new Set(res.media_ids || [])
          for (const item of this.items) {
            if (item.media && mediaIdSet.has(item.media.id)) {
              item.media.folder_name = trimmed
            }
          }
          for (const b of this.bookmarks) {
            if (mediaIdSet.has(b.id)) {
              b.folder_name = trimmed
            }
          }
          await this.fetchFolders()
          await this.fetchBookmarks()
          const label = trimmed === 'All References' ? 'すべての資料' : `「${trimmed}」`
          useToast().success(`${res.count} 件の資料を${label}に保存しました`)
          return true
        }
        return false
      } catch (e: any) {
        console.error('Save to folder failed:', e)
        useToast().error('フォルダへの保存に失敗しました', e?.data?.detail || e?.message)
        return false
      }
    },

    async saveAllCanvasToFolder(folderName: string) {
      return this.saveCanvasItemsToFolder([], folderName)
    },

    bringToFront(id?: string) {
      const targets = id ? [id] : this.selectedItemIds
      const maxZ = Math.max(...this.items.map(i => i.z_index), 0)
      targets.forEach((tid, idx) => {
        const item = this.items.find(i => i.id === tid)
        if (item) item.z_index = maxZ + 1 + idx
      })
      this.recordHistory()
    },

    sendToBack(id?: string) {
      const targets = id ? [id] : this.selectedItemIds
      const minZ = Math.min(...this.items.map(i => i.z_index), 1)
      targets.forEach((tid, idx) => {
        const item = this.items.find(i => i.id === tid)
        if (item) item.z_index = Math.max(1, minZ - 1 - idx)
      })
      this.recordHistory()
    },

    async deleteItem(id: string) {
      if (!this.currentBoard) return
      const boardId = this.currentBoard.id

      this.items = this.items.filter(i => i.id !== id)
      this.selectedItemIds = this.selectedItemIds.filter(i => i !== id)
      this.recordHistory()

      try {
        await $fetch(this.api(`/boards/${boardId}/items/${id}`), { method: 'DELETE' })
      } catch (e) {
        console.error('Delete item error:', e)
      }
    },

    async deleteSelected() {
      const ids = [...this.selectedItemIds]
      for (const id of ids) {
        await this.deleteItem(id)
      }
    },

    async uploadImages(files: File[], worldX = 0, worldY = 0, folderName?: string) {
      if (!files.length) return 0
      if (!this.currentBoard) {
        await this.loadFirstBoard()
      }
      if (!this.currentBoard) return 0
      const toast = useToast()

      let uploaded = 0
      for (let i = 0; i < files.length; i++) {
        const formData = new FormData()
        formData.append('board_id', this.currentBoard.id)
        formData.append('pos_x', String(worldX + i * 380))
        formData.append('pos_y', String(worldY))
        if (folderName && folderName !== 'All References') {
          formData.append('folder_name', folderName)
        }
        formData.append('file', files[i])

        try {
          const res = await $fetch<{ item: CanvasItem }>(this.api('/media/upload'), {
            method: 'POST',
            body: formData,
          })
          if (res?.item) {
            this.items.push(res.item)
            this.selectedItemIds = [res.item.id]
            uploaded++
          }
        } catch (e: any) {
          toast.error('画像を追加できませんでした', e?.data?.detail || e?.message)
        }
      }

      if (uploaded) {
        this.recordHistory()
        await this.fetchBookmarks()
        await this.fetchFolders()
        toast.success(`${uploaded} 枚の画像を追加しました`, 'AI解析をバックグラウンドで実行中です')
      }
      return uploaded
    },

    async reanalyzeActiveItem() {
      const active = this.activeItem
      if (!active?.media_item_id) return false

      try {
        const res = await $fetch<AIAnalysis>(this.api(`/media/${active.media_item_id}/reanalyze`), {
          method: 'POST',
        })
        active.ai_analysis = res
        if (active.media?.source_type === 'pixiv') active.media.ai_analysis_policy = 'allowed'
        this.recordHistory()
        return true
      } catch (e: any) {
        useToast().error('AI解析に失敗しました', (e as any)?.data?.detail || (e as any)?.message)
        return false
      }
    },

    async arrange(layoutType: 'grid' | 'horizontal' | 'vertical') {
      if (!this.currentBoard) return
      try {
        await $fetch(this.api(`/boards/${this.currentBoard.id}/arrange?layout_type=${layoutType}`), {
          method: 'POST',
        })
        await this.loadBoard(this.currentBoard.id)
        useToast().success('整列しました')
      } catch (e) {
        console.error('Arrange failed:', e)
      }
    },

    async updateBoardTitle(title: string) {
      if (!this.currentBoard) return
      const trimmed = title.trim()
      if (!trimmed) return

      this.currentBoard.title = trimmed
      try {
        await $fetch(this.api(`/boards/${this.currentBoard.id}`), {
          method: 'PUT',
          body: { title: trimmed },
        })
      } catch (e: any) {
        useToast().error('タイトルの保存に失敗しました', (e as any)?.message)
      }
    },
  },
})
