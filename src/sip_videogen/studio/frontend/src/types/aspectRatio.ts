//Aspect ratio type definitions for video generation
export type AspectRatio='1:1'|'16:9'|'9:16'|'4:3'|'3:4'
export const ASPECT_RATIOS:Record<AspectRatio,{label:string,w:number,h:number}>={
'1:1':{label:'Square',w:1,h:1},
'16:9':{label:'Landscape',w:16,h:9},
'9:16':{label:'Portrait',w:9,h:16},
'4:3':{label:'Classic',w:4,h:3},
'3:4':{label:'Portrait Classic',w:3,h:4}}
export const DEFAULT_ASPECT_RATIO:AspectRatio='1:1'
//Safe type guard using Object.hasOwn (avoids prototype chain)
export function isValidAspectRatio(v:string):v is AspectRatio{
return Object.prototype.hasOwnProperty.call(ASPECT_RATIOS,v)}
