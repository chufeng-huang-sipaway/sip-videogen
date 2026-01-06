//Aspect ratio type definitions for video generation
export type AspectRatio='1:1'|'16:9'|'9:16'|'5:3'|'3:5'|'4:3'|'3:4'|'3:2'|'2:3'
//Generation mode for image vs video
export type GenerationMode='image'|'video'
export const DEFAULT_GENERATION_MODE:GenerationMode='image'
//Video provider ratio support
export const VIDEO_PROVIDER_RATIOS:Record<string,AspectRatio[]>={
veo:['16:9','9:16'],//VEO: landscape/portrait only
kling:['1:1','16:9','9:16'],
sora:['16:9','9:16']}
export const DEFAULT_VIDEO_PROVIDER='veo'
export const ASPECT_RATIOS:Record<AspectRatio,{label:string,w:number,h:number,hint:string}>={
'1:1':{label:'Square',w:1,h:1,hint:'Instagram, Feed'},
'16:9':{label:'Landscape',w:16,h:9,hint:'YouTube, Web'},
'9:16':{label:'Portrait',w:9,h:16,hint:'TikTok, Reels'},
'5:3':{label:'Cinematic',w:5,h:3,hint:'Film'},
'3:5':{label:'Portrait Cinematic',w:3,h:5,hint:'Stories'},
'4:3':{label:'Classic',w:4,h:3,hint:'Presentation'},
'3:4':{label:'Portrait Classic',w:3,h:4,hint:'Social'},
'3:2':{label:'Photo',w:3,h:2,hint:'Photography'},
'2:3':{label:'Portrait Photo',w:2,h:3,hint:'Portrait'}}
export const DEFAULT_ASPECT_RATIO:AspectRatio='16:9'
//Safe type guard using Object.hasOwn (avoids prototype chain)
export function isValidAspectRatio(v:string):v is AspectRatio{
return Object.prototype.hasOwnProperty.call(ASPECT_RATIOS,v)}
//Base ratios (bigger number first, used for UI selector)
export const BASE_RATIOS=['16:9','5:3','4:3','3:2'] as const
export type BaseRatio=typeof BASE_RATIOS[number]
export type Orientation='landscape'|'portrait'
//Get actual ratio from base+orientation
export function getActualRatio(base:BaseRatio,o:Orientation):AspectRatio{
if(o==='landscape')return base
const[w,h]=base.split(':')
return `${h}:${w}` as AspectRatio}
//Parse ratio to determine orientation (returns null for 1:1)
export function parseRatioOrientation(r:AspectRatio):{base:BaseRatio,orientation:Orientation}|null{
if(r==='1:1')return null
const[w,h]=r.split(':').map(Number)
const isL=w>h
const base=(isL?r:`${h}:${w}`) as BaseRatio
return{base,orientation:isL?'landscape':'portrait'}}
//Get allowed ratios for generation mode
export function getVideoSupportedRatios(provider:string=DEFAULT_VIDEO_PROVIDER):AspectRatio[]{
return VIDEO_PROVIDER_RATIOS[provider]||VIDEO_PROVIDER_RATIOS.veo}
//Get all ratios as array
export const ALL_RATIOS:AspectRatio[]=['1:1','16:9','9:16','5:3','3:5','4:3','3:4','3:2','2:3']
//Validate ratio for mode, return valid ratio (same or fallback)
export function getValidRatioForMode(current:AspectRatio,mode:GenerationMode,provider:string=DEFAULT_VIDEO_PROVIDER):AspectRatio{
const allowed=mode==='video'?getVideoSupportedRatios(provider):ALL_RATIOS
if(!allowed||allowed.length===0)return'16:9'
if(allowed.includes(current))return current
//Fallback: prefer same orientation
const isL=['16:9','5:3','4:3','3:2'].includes(current)
const fallback=isL?'16:9':'9:16'
return allowed.includes(fallback)?fallback:allowed[0]}
//Persistence helpers for aspect ratio (per-brand localStorage)
const STORAGE_KEY_PREFIX='sip-aspect-ratio-'
export function saveAspectRatioPreference(brandSlug:string,ratio:AspectRatio):void{
if(!brandSlug)return
try{localStorage.setItem(`${STORAGE_KEY_PREFIX}${brandSlug}`,ratio)}catch{}}
export function loadAspectRatioPreference(brandSlug:string):AspectRatio|null{
if(!brandSlug)return null
try{const s=localStorage.getItem(`${STORAGE_KEY_PREFIX}${brandSlug}`)
if(s&&isValidAspectRatio(s))return s}catch{}
return null}
//Persistence helpers for generation mode (per-brand localStorage)
const MODE_STORAGE_KEY_PREFIX='sip-gen-mode-'
export function saveGenerationModePreference(brandSlug:string,mode:GenerationMode):void{
if(!brandSlug)return
try{localStorage.setItem(`${MODE_STORAGE_KEY_PREFIX}${brandSlug}`,mode)}catch{}}
export function loadGenerationModePreference(brandSlug:string):GenerationMode|null{
if(!brandSlug)return null
try{const s=localStorage.getItem(`${MODE_STORAGE_KEY_PREFIX}${brandSlug}`)
if(s==='image'||s==='video')return s}catch{}
return null}
