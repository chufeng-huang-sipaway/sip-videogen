interface BridgeResponse<T> {
  success: boolean
  data?: T
  error?: string
}

export interface ExecutionEvent {
  type: 'thinking' | 'tool_start' | 'tool_end'
  timestamp: number
  message: string
  detail: string
}

export interface BrandEntry {
  slug: string
  name: string
  category: string
}

export interface AssetNode {
  name: string
  path: string
  type: 'folder' | 'image'
  children?: AssetNode[]
  size?: number
}

export interface DocumentEntry {
  name: string
  path: string
  size: number
}

interface ApiKeyStatus {
  openai: boolean
  gemini: boolean
  all_configured: boolean
}

export interface ChoiceInteraction {
  type: 'choices'
  question: string
  choices: string[]
  allow_custom: boolean
}

export interface ImageSelectInteraction {
  type: 'image_select'
  question: string
  image_paths: string[]
  labels: string[]
}

export type Interaction = ChoiceInteraction | ImageSelectInteraction

export interface ChatAttachment {
  name: string
  data?: string
  path?: string
  mime?: string
  source?: 'upload' | 'asset'
}

interface ChatResponse {
  response: string
  images: string[]
  execution_trace: ExecutionEvent[]
  interaction?: Interaction | null
  memory_update?: { message: string } | null
}

// Update system types
export interface AppVersionInfo {
  version: string
  is_bundled: boolean
}

export interface UpdateCheckResult {
  has_update: boolean
  current_version: string
  new_version?: string
  changelog?: string
  release_url?: string
  download_url?: string
  file_size?: number
}

export interface UpdateProgress {
  status: 'idle' | 'downloading' | 'installing' | 'restarting' | 'error'
  percent: number
  downloaded?: number
  total?: number
  error?: string
}

export interface UpdateSettings {
  check_on_startup: boolean
  last_check?: number
  skipped_version?: string
}

interface PyWebViewAPI {
  check_api_keys(): Promise<BridgeResponse<ApiKeyStatus>>
  save_api_keys(openai: string, gemini: string): Promise<BridgeResponse<void>>
  get_brands(): Promise<BridgeResponse<{ brands: BrandEntry[]; active: string | null }>>
  set_brand(slug: string): Promise<BridgeResponse<{ slug: string }>>
  get_brand_info(slug?: string): Promise<BridgeResponse<{ slug: string; name: string; tagline: string; category: string }>>
  delete_brand(slug: string): Promise<BridgeResponse<void>>
  create_brand_from_materials(
    description: string,
    images: Array<{ filename: string; data: string }>,
    documents: Array<{ filename: string; data: string }>
  ): Promise<BridgeResponse<{ slug: string; name: string }>>

  // Documents (text files)
  get_documents(slug?: string): Promise<BridgeResponse<{ documents: DocumentEntry[] }>>
  read_document(path: string): Promise<BridgeResponse<{ content: string }>>
  open_document_in_finder(path: string): Promise<BridgeResponse<void>>
  delete_document(path: string): Promise<BridgeResponse<void>>
  rename_document(path: string, newName: string): Promise<BridgeResponse<{ newPath: string }>>
  upload_document(filename: string, data: string): Promise<BridgeResponse<{ path: string }>>

  // Assets (images)
  get_assets(slug?: string): Promise<BridgeResponse<{ tree: AssetNode[] }>>
  get_asset_thumbnail(path: string): Promise<BridgeResponse<{ dataUrl: string }>>
  get_asset_full(path: string): Promise<BridgeResponse<{ dataUrl: string }>>
  open_asset_in_finder(path: string): Promise<BridgeResponse<void>>
  delete_asset(path: string): Promise<BridgeResponse<void>>
  rename_asset(path: string, newName: string): Promise<BridgeResponse<{ newPath: string }>>
  upload_asset(filename: string, data: string, category: string): Promise<BridgeResponse<{ path: string }>>
  get_progress(): Promise<BridgeResponse<{ status: string }>>
  chat(message: string, attachments?: ChatAttachment[]): Promise<BridgeResponse<ChatResponse>>
  clear_chat(): Promise<BridgeResponse<void>>
  refresh_brand_memory(): Promise<BridgeResponse<{ message: string }>>

  // App updates
  get_app_version(): Promise<BridgeResponse<AppVersionInfo>>
  check_for_updates(): Promise<BridgeResponse<UpdateCheckResult>>
  download_and_install_update(download_url: string, version: string): Promise<BridgeResponse<{ message: string }>>
  get_update_progress(): Promise<BridgeResponse<UpdateProgress>>
  skip_update_version(version: string): Promise<BridgeResponse<void>>
  get_update_settings(): Promise<BridgeResponse<UpdateSettings>>
  set_update_check_on_startup(enabled: boolean): Promise<BridgeResponse<void>>
}

declare global {
  interface Window {
    pywebview?: { api: PyWebViewAPI }
  }
}

export function isPyWebView(): boolean {
  return typeof window !== 'undefined' && window.pywebview !== undefined
}

async function callBridge<T>(method: () => Promise<BridgeResponse<T>>): Promise<T> {
  const ready = await waitForPyWebViewReady()
  if (!ready || !isPyWebView()) throw new Error('Not running in PyWebView')
  const response = await method()
  if (!response.success) throw new Error(response.error || 'Unknown error')
  return response.data as T
}

export function waitForPyWebViewReady(timeoutMs = 800): Promise<boolean> {
  return new Promise((resolve) => {
    if (isPyWebView()) return resolve(true)

    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      controller.abort()
      resolve(false)
    }, timeoutMs)
    window.addEventListener(
      'pywebviewready',
      () => {
        window.clearTimeout(timer)
        resolve(true)
      },
      { once: true, signal: controller.signal }
    )
  })
}

export const bridge = {
  checkApiKeys: () => callBridge(() => window.pywebview!.api.check_api_keys()),
  saveApiKeys: (o: string, g: string) => callBridge(() => window.pywebview!.api.save_api_keys(o, g)),
  getBrands: () => callBridge(() => window.pywebview!.api.get_brands()),
  setBrand: (s: string) => callBridge(() => window.pywebview!.api.set_brand(s)),
  getBrandInfo: (s?: string) => callBridge(() => window.pywebview!.api.get_brand_info(s)),
  deleteBrand: (slug: string) => callBridge(() => window.pywebview!.api.delete_brand(slug)),
  createBrandFromMaterials: (
    description: string,
    images: Array<{ filename: string; data: string }>,
    documents: Array<{ filename: string; data: string }>
  ) => callBridge(() => window.pywebview!.api.create_brand_from_materials(description, images, documents)),

  // Documents
  getDocuments: async (s?: string) => (await callBridge(() => window.pywebview!.api.get_documents(s))).documents,
  readDocument: async (p: string) => (await callBridge(() => window.pywebview!.api.read_document(p))).content,
  openDocumentInFinder: (p: string) => callBridge(() => window.pywebview!.api.open_document_in_finder(p)),
  deleteDocument: (p: string) => callBridge(() => window.pywebview!.api.delete_document(p)),
  renameDocument: async (p: string, n: string) => (await callBridge(() => window.pywebview!.api.rename_document(p, n))).newPath,
  uploadDocument: async (f: string, d: string) => (await callBridge(() => window.pywebview!.api.upload_document(f, d))).path,

  getAssets: async (s?: string) => (await callBridge(() => window.pywebview!.api.get_assets(s))).tree,
  getAssetThumbnail: async (p: string) => (await callBridge(() => window.pywebview!.api.get_asset_thumbnail(p))).dataUrl,
  getAssetFull: async (p: string) => (await callBridge(() => window.pywebview!.api.get_asset_full(p))).dataUrl,
  openAssetInFinder: (p: string) => callBridge(() => window.pywebview!.api.open_asset_in_finder(p)),
  deleteAsset: (p: string) => callBridge(() => window.pywebview!.api.delete_asset(p)),
  renameAsset: async (p: string, n: string) => (await callBridge(() => window.pywebview!.api.rename_asset(p, n))).newPath,
  uploadAsset: async (f: string, d: string, c: string) => (await callBridge(() => window.pywebview!.api.upload_asset(f, d, c))).path,
  getProgress: async () => (await callBridge(() => window.pywebview!.api.get_progress())).status,
  chat: (m: string, attachments?: ChatAttachment[]) => callBridge(() => window.pywebview!.api.chat(m, attachments || [])),
  clearChat: () => callBridge(() => window.pywebview!.api.clear_chat()),
  refreshBrandMemory: () => callBridge(() => window.pywebview!.api.refresh_brand_memory()),

  // App updates
  getAppVersion: () => callBridge(() => window.pywebview!.api.get_app_version()),
  checkForUpdates: () => callBridge(() => window.pywebview!.api.check_for_updates()),
  downloadAndInstallUpdate: (url: string, version: string) =>
    callBridge(() => window.pywebview!.api.download_and_install_update(url, version)),
  getUpdateProgress: () => callBridge(() => window.pywebview!.api.get_update_progress()),
  skipUpdateVersion: (version: string) => callBridge(() => window.pywebview!.api.skip_update_version(version)),
  getUpdateSettings: () => callBridge(() => window.pywebview!.api.get_update_settings()),
  setUpdateCheckOnStartup: (enabled: boolean) =>
    callBridge(() => window.pywebview!.api.set_update_check_on_startup(enabled)),
}
