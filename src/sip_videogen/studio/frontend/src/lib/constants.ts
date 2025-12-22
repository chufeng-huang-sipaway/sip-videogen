//Centralized constants for Brand Studio frontend
export const ASSET_CATEGORIES=['logo','packaging','lifestyle','mascot','marketing','generated']as const
export const ALLOWED_IMAGE_EXTS=['.png','.jpg','.jpeg','.gif','.webp','.svg']as const
export const ALLOWED_TEXT_EXTS=['.md','.txt','.json','.yaml','.yml']as const
export const ALLOWED_ATTACHMENT_EXTS:Set<string>=new Set([...ALLOWED_IMAGE_EXTS,...ALLOWED_TEXT_EXTS])
export type AssetCategory=typeof ASSET_CATEGORIES[number]
