//Centralized media type detection and path normalization utilities
import type{GeneratedImage}from'../context/WorkstationContext'
//Determine media type from GeneratedMedia object
//Explicit type field takes precedence, fallback to extension inference
export function getMediaType(item:GeneratedImage):'image'|'video'{
if(item.type)return item.type
const path=item.originalPath||''
if(!path||path.startsWith('data:')||path.startsWith('blob:'))return'image'
const clean=path.split('?')[0].split('#')[0]
return/\.(mp4|mov|webm)$/i.test(clean)?'video':'image'}
//Normalize asset path for lookups (strip protocols, decode URI)
export function normalizeAssetPath(path:string):string{
let n=path
if(n.startsWith('file://'))n=n.slice(7)
n=decodeURIComponent(n)
n=n.replace(/\\/g,'/')
return n}
//Check if path is hidden (concept images for video)
export function isHiddenAssetPath(path:string):boolean{
const n=normalizeAssetPath(path).toLowerCase()
return n.includes('/video/concepts/')||n.includes('/video/concepts\\')}
