//Centralized constants for Brand Studio frontend
//These are fallback values - runtime values are fetched from Python API via get_constants()
//Fallback asset categories (compile-time type safety)
const DEFAULT_ASSET_CATEGORIES=['logo','packaging','lifestyle','mascot','marketing','generated','video']as const
const DEFAULT_ALLOWED_IMAGE_EXTS:readonly string[]=['.gif','.jpeg','.jpg','.png','.svg','.webp']
const DEFAULT_ALLOWED_TEXT_EXTS:readonly string[]=['.json','.md','.txt','.yaml','.yml']
const DEFAULT_ALLOWED_VIDEO_EXTS:readonly string[]=['.mov','.mp4','.webm']
//Runtime constants (populated by initConstants, fallback to defaults)
let _assetCategories:readonly string[]=DEFAULT_ASSET_CATEGORIES
let _allowedImageExts:readonly string[]=DEFAULT_ALLOWED_IMAGE_EXTS
let _allowedTextExts:readonly string[]=DEFAULT_ALLOWED_TEXT_EXTS
let _allowedVideoExts:readonly string[]=DEFAULT_ALLOWED_VIDEO_EXTS
let _mimeTypes:Record<string,string>={}
let _videoMimeTypes:Record<string,string>={}
let _initialized=false
//API response shape from Python get_constants()
export interface ConstantsPayload{asset_categories:string[];allowed_image_exts:string[];allowed_video_exts:string[];allowed_text_exts:string[];mime_types:Record<string,string>;video_mime_types:Record<string,string>}
//Initialize constants from API response
export function initConstants(payload:ConstantsPayload):void{
  _assetCategories=payload.asset_categories
  _allowedImageExts=payload.allowed_image_exts
  _allowedTextExts=payload.allowed_text_exts
  _allowedVideoExts=payload.allowed_video_exts
  _mimeTypes=payload.mime_types
  _videoMimeTypes=payload.video_mime_types
  _initialized=true
}
export function constantsInitialized():boolean{return _initialized}
//Exported constants (use getters to return runtime values)
export const ASSET_CATEGORIES=DEFAULT_ASSET_CATEGORIES
export const ALLOWED_IMAGE_EXTS:readonly string[]=DEFAULT_ALLOWED_IMAGE_EXTS
export const ALLOWED_TEXT_EXTS:readonly string[]=DEFAULT_ALLOWED_TEXT_EXTS
export const ALLOWED_VIDEO_EXTS:readonly string[]=DEFAULT_ALLOWED_VIDEO_EXTS
//Getters for runtime values (prefer these over direct exports for dynamic access)
export function getAssetCategories():readonly string[]{return _assetCategories}
export function getAllowedImageExts():readonly string[]{return _allowedImageExts}
export function getAllowedTextExts():readonly string[]{return _allowedTextExts}
export function getAllowedVideoExts():readonly string[]{return _allowedVideoExts}
export function getMimeTypes():Record<string,string>{return _mimeTypes}
export function getVideoMimeTypes():Record<string,string>{return _videoMimeTypes}
//Derived sets for quick lookup (regenerated after init)
export const ALLOWED_ATTACHMENT_EXTS:Set<string>=new Set([...ALLOWED_IMAGE_EXTS,...ALLOWED_TEXT_EXTS])
export function getAllowedAttachmentExts():Set<string>{return new Set([..._allowedImageExts,..._allowedTextExts])}
//Type for asset categories (compile-time safety)
export type AssetCategory=typeof ASSET_CATEGORIES[number]
