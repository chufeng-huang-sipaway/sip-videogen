//Mention parser for @product:slug and @style:slug syntax
import type {ProductEntry} from './bridge'
import type {StyleReferenceSummary} from './bridge'
export interface ParsedMention{type:'product'|'style';slug:string}
export interface MentionAttachments{products:string[];styleReferences:Array<{style_reference_slug:string;strict:boolean}>}
//Regex to match @type:slug mentions
const MENTION_REGEX=/@(product|style):([a-z0-9-]+)/gi
//Parse all mentions from text
export function parseMentions(text:string):ParsedMention[]{
const mentions:ParsedMention[]=[]
let match:RegExpExecArray|null
const regex=new RegExp(MENTION_REGEX.source,'gi')
while((match=regex.exec(text))!==null){
const type=match[1].toLowerCase() as 'product'|'style'
const slug=match[2].toLowerCase()
//Dedupe by type+slug
if(!mentions.some(m=>m.type===type&&m.slug===slug)){mentions.push({type,slug})}}
return mentions}
//Parse mentions and resolve to attachments using product/style reference lists
export function resolveMentions(text:string,products:ProductEntry[],styleReferences:StyleReferenceSummary[]):MentionAttachments{
const parsed=parseMentions(text)
const productSlugs=new Set(products.map(p=>p.slug))
const srMap=new Map(styleReferences.map(sr=>[sr.slug,sr]))
const result:MentionAttachments={products:[],styleReferences:[]}
for(const m of parsed){
if(m.type==='product'){
if(productSlugs.has(m.slug)){if(!result.products.includes(m.slug))result.products.push(m.slug)}
else console.warn(`[mention] Invalid product slug: @product:${m.slug}`)}
else if(m.type==='style'){
const sr=srMap.get(m.slug)
if(sr){if(!result.styleReferences.some(r=>r.style_reference_slug===m.slug))result.styleReferences.push({style_reference_slug:m.slug,strict:sr.default_strict??true})}
else console.warn(`[mention] Invalid style reference slug: @style:${m.slug}`)}}
return result}
//Check if @ is at a valid trigger position (token boundary)
export function isValidTriggerPosition(text:string,caretPos:number):boolean{
if(caretPos===0)return false
if(text[caretPos-1]!=='@')return false
if(caretPos===1)return true//@ at start of text
const charBefore=text[caretPos-2]
//Valid if after whitespace or punctuation
return/[\s,.;:!?()[\]{}'"<>]/.test(charBefore)}
//Get current mention being typed (for autocomplete)
export function getCurrentMention(text:string,caretPos:number):{start:number;query:string;type:'product'|'style'|'all'}|null{
//Look backwards from caret for @
let start=-1
for(let i=caretPos-1;i>=0;i--){
if(text[i]==='@'){
//Check if valid trigger position
if(i===0||/[\s,.;:!?()[\]{}'"<>]/.test(text[i-1])){start=i;break}
return null}
//Stop if we hit whitespace (not in a mention)
if(/\s/.test(text[i]))return null}
if(start===-1)return null
const afterAt=text.slice(start+1,caretPos)
//Check if typing @product: or @style:
const colonIdx=afterAt.indexOf(':')
if(colonIdx!==-1){
const prefix=afterAt.slice(0,colonIdx).toLowerCase()
if(prefix==='product')return{start,query:afterAt.slice(colonIdx+1).toLowerCase(),type:'product'}
if(prefix==='style')return{start,query:afterAt.slice(colonIdx+1).toLowerCase(),type:'style'}
//Invalid prefix, no autocomplete
return null}
//Just @ or @partial - show all, filter by query
return{start,query:afterAt.toLowerCase(),type:'all'}}
