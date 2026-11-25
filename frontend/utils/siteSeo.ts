export const SITE_NAME = 'RefLens.io'
export const SITE_URL = 'https://art.wawa-app.me/RefLens.io/'
export const HOME_TITLE = 'RefLens.io｜イラストの参考資料を整理できる無限キャンバス'
export const HOME_DESCRIPTION =
  'RefLens.ioは、イラストやデザインの参考資料を集めて整理できるWebツールです。画像やWebリンクをフォルダ・タグで管理し、無限キャンバスに並べて見比べられます。'

export function publicSiteUrl(path: string) {
  return new URL(path.replace(/^\/+/, ''), SITE_URL).href
}
