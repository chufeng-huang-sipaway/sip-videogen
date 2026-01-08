import type {
  BrandIdentityFull,
  BackupEntry,
  IdentitySection,
  SectionDataMap,
} from '../types/brand-identity'
import type{ApprovalRequestData}from'./types/approval'
import { initConstants, type ConstantsPayload } from './constants'

interface BridgeResponse<T> {
  success: boolean
  data?: T
  error?: string
}

export type ActivityEventType = 'thinking' | 'tool_start' | 'tool_end' | 'skill_loaded' | 'thinking_step' | ''

export interface ExecutionEvent {
  type: ActivityEventType
  timestamp: number
  message: string
  detail: string
}

//ThinkingStep - matches backend ThinkingStep schema (snake_case -> camelCase)
export interface ThinkingStep {
  id: string
  runId?: string
  seq?: number
  step: string
  detail?: string
  expertise?: string
  status?: 'pending' | 'complete' | 'failed'
  source?: 'agent' | 'auto'
  timestamp?: string | number
}

export interface ProgressStatus {
  status: string
  type: ActivityEventType
  skills: string[]
  thinking_steps: ThinkingStep[]
}

export interface BrandEntry {
  slug: string
  name: string
  category: string
}

export interface AssetNode {
  name: string
  path: string
  type: 'folder' | 'image' | 'video'
  children?: AssetNode[]
  size?: number
}

export interface DocumentEntry {
  name: string
  path: string
  size: number
}

//Product types
export interface ProductAttribute {key:string;value:string;category:string}
export interface PackagingTextElement {text:string;notes:string;role:string;typography:string;size:string;color:string;position:string;emphasis:string}
export interface PackagingTextDescription {summary:string;elements:PackagingTextElement[];layout_notes:string;source_image:string;generated_at:string|null;is_human_edited:boolean}
export interface ProductEntry {
  slug: string
  name: string
  description: string
  primary_image: string
  attribute_count: number
  created_at: string
  updated_at: string
}

export interface ProductFull {
  slug:string
  name:string
  description:string
  images:string[]
  primary_image:string
  attributes:ProductAttribute[]
  packaging_text:PackagingTextDescription|null
  created_at:string
  updated_at:string
}

// Project types
export type ProjectStatus = 'active' | 'archived'

export interface ProjectEntry {
  slug: string
  name: string
  status: ProjectStatus
  asset_count: number
  created_at: string
  updated_at: string
}

export interface ProjectFull {
  slug: string
  name: string
  status: ProjectStatus
  instructions: string
  assets: string[]
  asset_count: number
  created_at: string
  updated_at: string
}

//Style Reference types
export interface CanvasSpec {
  aspect_ratio: string
  background: string
  width?: number | null
  height?: number | null
}
export interface MessageSpec {
  intent: string
  audience: string
  key_claims: string[]
}
export interface StyleSpec {
  palette: string[]
  lighting: string
  mood: string
  materials: string[]
}
export interface GeometrySpec {
  x: number
  y: number
  width: number
  height: number
  rotation: number
  z_index: number
}
export interface AppearanceSpec {
  fill: string
  stroke: string
  opacity: number
  blur: number
  shadow: string
}
export interface ContentSpec {
  text: string
  font_family: string
  font_size: string
  font_weight: string
  alignment: string
  image_description: string
}
export interface ConstraintSpec {
  locked_position: boolean
  locked_size: boolean
  locked_aspect: boolean
  min_margin: number
  semantic_role: string
}
export interface LayoutElement {
  id: string
  type: string
  role: string
  geometry: GeometrySpec
  appearance: AppearanceSpec
  content: ContentSpec
  constraints: ConstraintSpec
}
export interface InteractionSpec {
  replacement_mode: string
  preserve_shadow: boolean
  preserve_reflection: boolean
  scale_mode: string
}
export interface ProductSlot {
  id: string
  geometry: GeometrySpec
  appearance: AppearanceSpec
  interaction: InteractionSpec
}
//V1 Style Reference Analysis (geometry-focused, deprecated)
export interface StyleReferenceAnalysisV1 {
  version: string
  canvas: CanvasSpec
  message: MessageSpec
  style: StyleSpec
  elements: LayoutElement[]
  product_slot: ProductSlot | null
}
//V2 Style Reference Analysis (semantic-focused)
export interface VisualSceneSpec {
  scene_description: string
  product_placement: string
  lifestyle_elements: string[]
  visual_treatments: string[]
  photography_style: string
}
export interface LayoutStructureSpec {
  structure: string
  zones: string[]
  hierarchy: string
  alignment: string
}
export interface StyleReferenceConstraintsSpec {
  non_negotiables: string[]
  creative_freedom: string[]
  product_integration: string
}
export interface StyleReferenceAnalysisV2 {
  version: string
  canvas: CanvasSpec
  style: StyleSpec
  layout: LayoutStructureSpec
  visual_scene: VisualSceneSpec
  constraints: StyleReferenceConstraintsSpec
}
//V3 Style Reference Analysis (color grading focused)
export interface ColorGradingSpec {
  color_temperature: string
  shadow_tint: string
  black_point: string
  highlight_rolloff: string
  highlight_tint: string
  saturation_level: string
  contrast_character: string
  film_stock_reference: string
  signature_elements: string[]
}
export interface StyleSuggestionsSpec {
  environment_tendency: string
  mood: string
  lighting_setup: string
}
export interface StyleReferenceAnalysisV3 {
  version: string
  canvas: CanvasSpec
  color_grading: ColorGradingSpec
  style_suggestions: StyleSuggestionsSpec
}
//Union type for all versions
export type StyleReferenceAnalysis = StyleReferenceAnalysisV1 | StyleReferenceAnalysisV2 | StyleReferenceAnalysisV3
//Type guards
export function isV2StyleReferenceAnalysis(analysis: StyleReferenceAnalysis): analysis is StyleReferenceAnalysisV2 {
  return analysis.version === '2.0'
}
export function isV3StyleReferenceAnalysis(analysis: StyleReferenceAnalysis): analysis is StyleReferenceAnalysisV3 {
  return analysis.version === '3.0'
}
export interface StyleReferenceSummary {
  slug: string
  name: string
  description: string
  primary_image: string
  default_strict: boolean
  created_at: string
  updated_at: string
}
export interface StyleReferenceFull {
  slug: string
  name: string
  description: string
  images: string[]
  primary_image: string
  default_strict: boolean
  analysis: StyleReferenceAnalysis | null
  created_at: string
  updated_at: string
}
export interface AttachedStyleReference {
  style_reference_slug: string
  strict: boolean
}
//Chat context types
import type { AspectRatio,VideoAspectRatio } from '../types/aspectRatio'
export interface ChatContext {
  project_slug?: string | null
  attached_products?: string[]
  attached_style_references?: AttachedStyleReference[]
  image_aspect_ratio?: AspectRatio
  video_aspect_ratio?: VideoAspectRatio
}

interface ApiKeyStatus {
  openai: boolean
  gemini: boolean
  firecrawl: boolean
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

export interface ReferenceImageDetail {
  path: string
  product_slug?: string | null
  role?: string | null
  used_for?: string | null
}

export interface GenerationAttemptMetadata {
  attempt_number: number
  prompt: string
  api_call_code?: string
  request_payload?: Record<string, unknown> | null
  validation?: Record<string, unknown> | null
  validation_passed?: boolean | null
  image_path?: string
  error?: string
}

// Image generation metadata for debugging visibility
export interface ImageGenerationMetadata {
  prompt: string
  original_prompt?: string
  model: string
  aspect_ratio: string
  image_size: string
  reference_image: string | null
  reference_images?: string[]
  reference_images_detail?: ReferenceImageDetail[]
  product_slugs: string[]
  validate_identity: boolean
  validation_passed?: boolean | null
  validation_warning?: string | null
  validation_attempts?: number | null
  final_attempt_number?: number | null
  attempts?: GenerationAttemptMetadata[] | null
  request_payload?: Record<string, unknown> | null
  generated_at: string
  generation_time_ms: number
  api_call_code: string
}

export interface GeneratedImage {
  url: string
  path?: string
  id?: string
  sourceStyleReferencePath?: string
  metadata?: ImageGenerationMetadata | null
}
//Image status types for workstation curation
export type ImageStatusType = 'unsorted'
export interface ImageStatusEntry {
  id: string
  status: ImageStatusType
  originalPath: string
  currentPath: string
  prompt?: string | null
  sourceStyleReferencePath?: string | null
  timestamp: string
  viewedAt?: string | null
}
export interface RegisterImageInput {
  path: string
  prompt?: string
  sourceStyleReferencePath?: string
}

//Video generation metadata
export interface VideoGenerationMetadata {
  prompt: string
  concept_image_path?: string | null
  aspect_ratio: string
  duration: number
  provider: string
  project_slug?: string | null
  generated_at: string
  generation_time_ms: number
  source_image_metadata?: ImageGenerationMetadata | null
}

export interface GeneratedVideo {
  url: string
  path: string
  filename: string
  metadata?: VideoGenerationMetadata | null
}

interface ChatResponse {
  response: string
  images: GeneratedImage[]
  videos?: GeneratedVideo[]
  style_references?: string[]
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
  get_constants(): Promise<BridgeResponse<ConstantsPayload>>
  check_api_keys(): Promise<BridgeResponse<ApiKeyStatus>>
  save_api_keys(openai: string, gemini: string, firecrawl?: string): Promise<BridgeResponse<void>>
  get_chat_prefs(brand_slug: string): Promise<BridgeResponse<{ image_aspect_ratio?: string; video_aspect_ratio?: string; aspect_ratio?: string }>>
  save_chat_prefs(brand_slug: string, image_aspect_ratio?: string, video_aspect_ratio?: string): Promise<BridgeResponse<void>>
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

  // Assets (images/video)
  get_assets(slug?: string): Promise<BridgeResponse<{ tree: AssetNode[] }>>
  get_asset_thumbnail(path: string): Promise<BridgeResponse<{ dataUrl: string }>>
  get_asset_full(path: string): Promise<BridgeResponse<{ dataUrl: string }>>
  get_image_thumbnail(image_path: string): Promise<BridgeResponse<{ dataUrl: string }>>
  get_image_data(image_path: string): Promise<BridgeResponse<{ dataUrl: string }>>
  open_asset_in_finder(path: string): Promise<BridgeResponse<void>>
  delete_asset(path: string): Promise<BridgeResponse<void>>
  rename_asset(path: string, newName: string): Promise<BridgeResponse<{ newPath: string }>>
  upload_asset(filename: string, data: string, category: string): Promise<BridgeResponse<{ path: string }>>
  get_video_path(path: string): Promise<BridgeResponse<{ path: string; filename: string; file_url: string }>>
  replace_asset(original_path: string, new_path: string): Promise<BridgeResponse<{ path: string }>>
  get_video_data(path: string): Promise<BridgeResponse<{ dataUrl: string; path: string; filename: string }>>
  get_image_metadata(path: string): Promise<BridgeResponse<ImageGenerationMetadata | null>>
  get_progress(): Promise<BridgeResponse<ProgressStatus>>
  chat(
    message: string,
    attachments?: ChatAttachment[],
    project_slug?: string | null,
    attached_products?: string[],
    attached_style_references?: AttachedStyleReference[],
    image_aspect_ratio?: string,
    video_aspect_ratio?: string
  ): Promise<BridgeResponse<ChatResponse>>
  clear_chat(): Promise<BridgeResponse<void>>
  refresh_brand_memory(): Promise<BridgeResponse<{ message: string }>>

  // Product methods
  get_products(brand_slug?: string): Promise<BridgeResponse<{ products: ProductEntry[] }>>
  get_product(product_slug: string): Promise<BridgeResponse<ProductFull>>
  create_product(
    name: string,
    description: string,
    images?: Array<{ filename: string; data: string }>,
    attributes?: Array<{ key: string; value: string; category: string }>
  ): Promise<BridgeResponse<{ slug: string }>>
  update_product(
    product_slug: string,
    name?: string,
    description?: string,
    attributes?: Array<{ key: string; value: string; category: string }>
  ): Promise<BridgeResponse<{ slug: string; name: string; description: string }>>
  delete_product(product_slug: string): Promise<BridgeResponse<void>>
  get_product_images(product_slug: string): Promise<BridgeResponse<{ images: string[] }>>
  upload_product_image(
    product_slug: string,
    filename: string,
    data_base64: string
  ): Promise<BridgeResponse<{ path: string }>>
  delete_product_image(product_slug: string, filename: string): Promise<BridgeResponse<void>>
  set_primary_product_image(product_slug: string, filename: string): Promise<BridgeResponse<void>>
  get_product_image_thumbnail(path: string): Promise<BridgeResponse<{ dataUrl: string }>>
  get_product_image_full(path: string): Promise<BridgeResponse<{ dataUrl: string }>>
  analyze_product_packaging(product_slug:string,force:boolean):Promise<BridgeResponse<{result:string}>>
  //Style Reference methods
  get_style_references(brand_slug?: string): Promise<BridgeResponse<{ style_references: StyleReferenceSummary[] }>>
  get_style_reference(style_reference_slug: string): Promise<BridgeResponse<StyleReferenceFull>>
  create_style_reference(name: string, description: string, images?: Array<{ filename: string; data: string }>, default_strict?: boolean): Promise<BridgeResponse<{ slug: string }>>
  update_style_reference(style_reference_slug: string, name?: string, description?: string, default_strict?: boolean): Promise<BridgeResponse<{ slug: string; name: string; description: string }>>
  delete_style_reference(style_reference_slug: string): Promise<BridgeResponse<void>>
  get_style_reference_images(style_reference_slug: string): Promise<BridgeResponse<{ images: string[] }>>
  upload_style_reference_image(style_reference_slug: string, filename: string, data_base64: string): Promise<BridgeResponse<{ path: string }>>
  delete_style_reference_image(style_reference_slug: string, filename: string): Promise<BridgeResponse<void>>
  set_primary_style_reference_image(style_reference_slug: string, filename: string): Promise<BridgeResponse<void>>
  get_style_reference_image_thumbnail(path: string): Promise<BridgeResponse<{ dataUrl: string }>>
  get_style_reference_image_full(path: string): Promise<BridgeResponse<{ dataUrl: string }>>
  reanalyze_style_reference(style_reference_slug: string): Promise<BridgeResponse<{ analysis: StyleReferenceAnalysis }>>

  // Project methods
  get_projects(brand_slug?: string): Promise<BridgeResponse<{ projects: ProjectEntry[]; active_project: string | null }>>
  get_project(project_slug: string): Promise<BridgeResponse<ProjectFull>>
  create_project(name: string, instructions?: string): Promise<BridgeResponse<{ slug: string }>>
  update_project(
    project_slug: string,
    name?: string,
    instructions?: string,
    status?: string
  ): Promise<BridgeResponse<{ slug: string; name: string; status: string }>>
  delete_project(project_slug: string): Promise<BridgeResponse<void>>
  set_active_project(project_slug: string | null): Promise<BridgeResponse<{ active_project: string | null }>>
  get_active_project(): Promise<BridgeResponse<{ active_project: string | null }>>
  get_project_assets(project_slug: string): Promise<BridgeResponse<{ assets: string[] }>>
  get_general_assets(brand_slug?: string): Promise<BridgeResponse<{ assets: string[]; count: number }>>

  // App updates
  get_app_version(): Promise<BridgeResponse<AppVersionInfo>>
  check_for_updates(): Promise<BridgeResponse<UpdateCheckResult>>
  download_and_install_update(download_url: string, version: string): Promise<BridgeResponse<{ message: string }>>
  get_update_progress(): Promise<BridgeResponse<UpdateProgress>>
  skip_update_version(version: string): Promise<BridgeResponse<void>>
  get_update_settings(): Promise<BridgeResponse<UpdateSettings>>
  set_update_check_on_startup(enabled: boolean): Promise<BridgeResponse<void>>

  // Brand Identity methods
  get_brand_identity(): Promise<BridgeResponse<BrandIdentityFull>>
  update_brand_identity_section(
    section: IdentitySection,
    data: SectionDataMap[IdentitySection]
  ): Promise<BridgeResponse<BrandIdentityFull>>
  regenerate_brand_identity(confirm: boolean): Promise<BridgeResponse<BrandIdentityFull>>
  list_identity_backups(): Promise<BridgeResponse<{ backups: BackupEntry[] }>>
  restore_identity_backup(filename: string): Promise<BridgeResponse<BrandIdentityFull>>
  //Image status methods (workstation curation)
  get_unsorted_images(brand_slug?: string): Promise<BridgeResponse<ImageStatusEntry[]>>
  mark_image_viewed(image_id: string, brand_slug?: string): Promise<BridgeResponse<ImageStatusEntry>>
  register_image(image_path: string, brand_slug?: string, prompt?: string, source_style_reference_path?: string): Promise<BridgeResponse<ImageStatusEntry>>
  register_generated_images(images: RegisterImageInput[], brand_slug?: string): Promise<BridgeResponse<ImageStatusEntry[]>>
  cancel_generation(brand_slug?: string): Promise<BridgeResponse<{ cancelled: boolean }>>
  backfill_images(brand_slug?: string): Promise<BridgeResponse<{ added: ImageStatusEntry[]; count: number }>>
  copy_image_to_clipboard(image_path: string): Promise<BridgeResponse<{ copied: boolean; path: string }>>
  share_image(image_path: string): Promise<BridgeResponse<{ shared: boolean; path: string }>>
  //Todo list interrupt/resume methods
  interrupt_task(action: string, new_message?: string): Promise<BridgeResponse<{ interrupted: boolean; action: string; note: string }>>
  resume_task(): Promise<BridgeResponse<{ resumed: boolean }>>
  //Quick generator method
  quick_generate(prompt:string,product_slug?:string,style_reference_slug?:string,aspect_ratio?:string,count?:number):Promise<BridgeResponse<QuickGenerateResult>>
  //Autonomy mode and approval methods
  set_autonomy_mode(enabled:boolean):Promise<BridgeResponse<{autonomy_mode:boolean}>>
  get_pending_approval():Promise<BridgeResponse<ApprovalRequestData|null>>
  respond_to_approval(approval_id:string,action:string,modified_prompt?:string):Promise<BridgeResponse<{responded:boolean}>>
}
//Quick generate result type
export interface QuickGenerateResult {
  success:boolean
  images:Array<{path:string;data?:string;prompt:string}>
  errors?:Array<{index:number;error:string}>
  generated:number
  requested:number
  error?:string
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

//Fetch and initialize constants from Python API (call once at app startup)
export async function fetchAndInitConstants(): Promise<boolean> {
  try {
    const ready = await waitForPyWebViewReady()
    if (!ready || !isPyWebView()) return false
    const resp = await window.pywebview!.api.get_constants()
    if (resp.success && resp.data) { initConstants(resp.data); return true }
    return false
  } catch { return false }
}

export const bridge = {
  checkApiKeys: () => callBridge(() => window.pywebview!.api.check_api_keys()),
  saveApiKeys: (o: string, g: string, f?: string) => callBridge(() => window.pywebview!.api.save_api_keys(o, g, f || '')),
  getChatPrefs: (brandSlug: string) => callBridge(() => window.pywebview!.api.get_chat_prefs(brandSlug)),
  saveChatPrefs: (brandSlug: string, imageAspectRatio?: string, videoAspectRatio?: string) => callBridge(() => window.pywebview!.api.save_chat_prefs(brandSlug, imageAspectRatio, videoAspectRatio)),
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
  getImageThumbnail: async (p: string) => (await callBridge(() => window.pywebview!.api.get_image_thumbnail(p))).dataUrl,
  getImageData: async (p: string) => (await callBridge(() => window.pywebview!.api.get_image_data(p))).dataUrl,
  openAssetInFinder: (p: string) => callBridge(() => window.pywebview!.api.open_asset_in_finder(p)),
  deleteAsset: (p: string) => callBridge(() => window.pywebview!.api.delete_asset(p)),
  renameAsset: async (p: string, n: string) => (await callBridge(() => window.pywebview!.api.rename_asset(p, n))).newPath,
  uploadAsset: async (f: string, d: string, c: string) => (await callBridge(() => window.pywebview!.api.upload_asset(f, d, c))).path,
  getVideoPath: async (p: string) => (await callBridge(() => window.pywebview!.api.get_video_path(p))).file_url,
  replaceAsset: async (orig: string, newPath: string) => (await callBridge(() => window.pywebview!.api.replace_asset(orig, newPath))).path,
  getVideoData: async (p: string) => (await callBridge(() => window.pywebview!.api.get_video_data(p))).dataUrl,
  getImageMetadata: async (p: string): Promise<ImageGenerationMetadata | null> => {
    try { return await callBridge(() => window.pywebview!.api.get_image_metadata(p)) }
    catch (e) { console.warn('[bridge.getImageMetadata] Error loading metadata:', p, e); return null }
  },
  getProgress: async () => await callBridge(() => window.pywebview!.api.get_progress()),
  chat: (m: string, attachments?: ChatAttachment[], context?: ChatContext) =>
    callBridge(() =>
      window.pywebview!.api.chat(
        m,
        attachments || [],
        context?.project_slug,
        context?.attached_products,
        context?.attached_style_references,
        context?.image_aspect_ratio || '16:9',
        context?.video_aspect_ratio || '16:9'
      )
    ),
  clearChat: () => callBridge(() => window.pywebview!.api.clear_chat()),
  refreshBrandMemory: () => callBridge(() => window.pywebview!.api.refresh_brand_memory()),

  // Products
  getProducts: async (brandSlug?: string) =>
    (await callBridge(() => window.pywebview!.api.get_products(brandSlug))).products,
  getProduct: (productSlug: string) => callBridge(() => window.pywebview!.api.get_product(productSlug)),
  createProduct: async (
    name: string,
    description: string,
    images?: Array<{ filename: string; data: string }>,
    attributes?: Array<{ key: string; value: string; category: string }>
  ) => (await callBridge(() => window.pywebview!.api.create_product(name, description, images, attributes))).slug,
  updateProduct: (
    productSlug: string,
    name?: string,
    description?: string,
    attributes?: Array<{ key: string; value: string; category: string }>
  ) => callBridge(() => window.pywebview!.api.update_product(productSlug, name, description, attributes)),
  deleteProduct: (productSlug: string) => callBridge(() => window.pywebview!.api.delete_product(productSlug)),
  getProductImages: async (productSlug: string) =>
    (await callBridge(() => window.pywebview!.api.get_product_images(productSlug))).images,
  uploadProductImage: async (productSlug: string, filename: string, dataBase64: string) =>
    (await callBridge(() => window.pywebview!.api.upload_product_image(productSlug, filename, dataBase64))).path,
  deleteProductImage: (productSlug: string, filename: string) =>
    callBridge(() => window.pywebview!.api.delete_product_image(productSlug, filename)),
  setPrimaryProductImage: (productSlug: string, filename: string) =>
    callBridge(() => window.pywebview!.api.set_primary_product_image(productSlug, filename)),
  getProductImageThumbnail: async (path: string) =>
    (await callBridge(() => window.pywebview!.api.get_product_image_thumbnail(path))).dataUrl,
  getProductImageFull: async (path: string) =>
    (await callBridge(() => window.pywebview!.api.get_product_image_full(path))).dataUrl,
  analyzeProductPackaging: async (productSlug:string,force:boolean=false) =>
    (await callBridge(()=>window.pywebview!.api.analyze_product_packaging(productSlug,force))).result,
  //Style References
  getStyleReferences: async (brandSlug?: string) =>
    (await callBridge(() => window.pywebview!.api.get_style_references(brandSlug))).style_references,
  getStyleReference: (slug: string) => callBridge(() => window.pywebview!.api.get_style_reference(slug)),
  createStyleReference: async (name: string, description: string, images?: Array<{ filename: string; data: string }>, defaultStrict?: boolean) =>
    (await callBridge(() => window.pywebview!.api.create_style_reference(name, description, images, defaultStrict))).slug,
  updateStyleReference: (slug: string, name?: string, description?: string, defaultStrict?: boolean) =>
    callBridge(() => window.pywebview!.api.update_style_reference(slug, name, description, defaultStrict)),
  deleteStyleReference: (slug: string) => callBridge(() => window.pywebview!.api.delete_style_reference(slug)),
  getStyleReferenceImages: async (slug: string) =>
    (await callBridge(() => window.pywebview!.api.get_style_reference_images(slug))).images,
  uploadStyleReferenceImage: async (slug: string, filename: string, dataBase64: string) =>
    (await callBridge(() => window.pywebview!.api.upload_style_reference_image(slug, filename, dataBase64))).path,
  deleteStyleReferenceImage: (slug: string, filename: string) =>
    callBridge(() => window.pywebview!.api.delete_style_reference_image(slug, filename)),
  setPrimaryStyleReferenceImage: (slug: string, filename: string) =>
    callBridge(() => window.pywebview!.api.set_primary_style_reference_image(slug, filename)),
  getStyleReferenceImageThumbnail: async (path: string) =>
    (await callBridge(() => window.pywebview!.api.get_style_reference_image_thumbnail(path))).dataUrl,
  getStyleReferenceImageFull: async (path: string) =>
    (await callBridge(() => window.pywebview!.api.get_style_reference_image_full(path))).dataUrl,
  reanalyzeStyleReference: async (slug: string) =>
    (await callBridge(() => window.pywebview!.api.reanalyze_style_reference(slug))).analysis,

  // Projects
  getProjects: async (brandSlug?: string) => {
    const result = await callBridge(() => window.pywebview!.api.get_projects(brandSlug))
    return { projects: result.projects, activeProject: result.active_project }
  },
  getProject: (projectSlug: string) => callBridge(() => window.pywebview!.api.get_project(projectSlug)),
  createProject: async (name: string, instructions?: string) =>
    (await callBridge(() => window.pywebview!.api.create_project(name, instructions))).slug,
  updateProject: (projectSlug: string, name?: string, instructions?: string, status?: string) =>
    callBridge(() => window.pywebview!.api.update_project(projectSlug, name, instructions, status)),
  deleteProject: (projectSlug: string) => callBridge(() => window.pywebview!.api.delete_project(projectSlug)),
  setActiveProject: async (projectSlug: string | null) =>
    (await callBridge(() => window.pywebview!.api.set_active_project(projectSlug))).active_project,
  getActiveProject: async () =>
    (await callBridge(() => window.pywebview!.api.get_active_project())).active_project,
  getProjectAssets: async (projectSlug: string) =>
    (await callBridge(() => window.pywebview!.api.get_project_assets(projectSlug))).assets,
  getGeneralAssets: async (brandSlug?: string) =>
    await callBridge(() => window.pywebview!.api.get_general_assets(brandSlug)),

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

  // Brand Identity
  getBrandIdentity: () => callBridge(() => window.pywebview!.api.get_brand_identity()),
  updateBrandIdentitySection: <S extends IdentitySection>(section: S, data: SectionDataMap[S]) =>
    callBridge(() => window.pywebview!.api.update_brand_identity_section(section, data)),
  regenerateBrandIdentity: (confirm: boolean) =>
    callBridge(() => window.pywebview!.api.regenerate_brand_identity(confirm)),
  listIdentityBackups: async () =>
    (await callBridge(() => window.pywebview!.api.list_identity_backups())).backups,
  restoreIdentityBackup: (filename: string) =>
    callBridge(() => window.pywebview!.api.restore_identity_backup(filename)),
  //Image status (workstation curation)
  getUnsortedImages: (brandSlug?: string) => callBridge(() => window.pywebview!.api.get_unsorted_images(brandSlug)),
  markImageViewed: (imageId: string, brandSlug?: string) => callBridge(() => window.pywebview!.api.mark_image_viewed(imageId, brandSlug)),
  registerImage: (imagePath: string, brandSlug?: string, prompt?: string, sourceStyleReferencePath?: string) => callBridge(() => window.pywebview!.api.register_image(imagePath, brandSlug, prompt, sourceStyleReferencePath)),
  registerGeneratedImages: (images: RegisterImageInput[], brandSlug?: string) => callBridge(() => window.pywebview!.api.register_generated_images(images, brandSlug)),
  cancelGeneration: (brandSlug?: string) => callBridge(() => window.pywebview!.api.cancel_generation(brandSlug)),
  backfillImages: (brandSlug?: string) => callBridge(() => window.pywebview!.api.backfill_images(brandSlug)),
  copyImageToClipboard: (imagePath: string) => callBridge(() => window.pywebview!.api.copy_image_to_clipboard(imagePath)),
  shareImage: (imagePath: string) => callBridge(() => window.pywebview!.api.share_image(imagePath)),
  //Todo list interrupt/resume
  interruptTask: (action:'pause'|'stop'|'new_direction',newMessage?:string)=>callBridge(()=>window.pywebview!.api.interrupt_task(action,newMessage)),
  resumeTask: ()=>callBridge(()=>window.pywebview!.api.resume_task()),
  //Quick generator
  quickGenerate: (prompt:string,productSlug?:string,styleReferenceSlug?:string,aspectRatio:string='1:1',count:number=1)=>callBridge(()=>window.pywebview!.api.quick_generate(prompt,productSlug,styleReferenceSlug,aspectRatio,count)),
  //Autonomy mode and approval
  setAutonomyMode: (enabled:boolean)=>callBridge(()=>window.pywebview!.api.set_autonomy_mode(enabled)),
  getPendingApproval: async()=>callBridge(()=>window.pywebview!.api.get_pending_approval()),
  respondToApproval: (approvalId:string,action:'approve'|'approve_all'|'modify'|'skip',modifiedPrompt?:string)=>callBridge(()=>window.pywebview!.api.respond_to_approval(approvalId,action,modifiedPrompt)),
}
