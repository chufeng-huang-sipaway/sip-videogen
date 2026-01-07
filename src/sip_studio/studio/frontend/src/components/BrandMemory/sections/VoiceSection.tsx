import{useState,useCallback}from'react'
import{Save,AlertCircle,CheckCircle2}from'lucide-react'
import{Button}from'@/components/ui/button'
import{Input}from'@/components/ui/input'
import{Alert,AlertDescription}from'@/components/ui/alert'
import{Spinner}from'@/components/ui/spinner'
import{MemorySection}from'../MemorySection'
import{useBrand}from'@/context/BrandContext'
import{toast}from'@/components/ui/toaster'
import type{VoiceGuidelines}from'@/types/brand-identity'
interface VoiceSectionProps{
/** Current voice guidelines data */
data:VoiceGuidelines}
/**
 * VoiceSection - Displays and edits voice and messaging guidelines.
 *
 * Fields:
 * - personality: Brand personality description
 * - tone_attributes: List of tone descriptors (e.g., "warm", "professional")
 * - key_messages: Core messaging themes
 * - messaging_do: Do's for brand messaging
 * - messaging_dont: Don'ts for brand messaging
 * - example_headlines: Example headline copy
 * - example_taglines: Example tagline copy
 *
 * Uses MemorySection wrapper for collapse/expand and edit mode toggle.
 */
export function VoiceSection({data}:VoiceSectionProps){
const{updateIdentitySection}=useBrand()
//Edit state - local copy of data being edited
const[editData,setEditData]=useState<VoiceGuidelines|null>(null)
const[isEditing,setIsEditing]=useState(false)
const[isSaving,setIsSaving]=useState(false)
const[saveError,setSaveError]=useState<string|null>(null)
const[saveSuccess,setSaveSuccess]=useState(false)
//Deep copy helper for nested arrays
const deepCopy=useCallback((source:VoiceGuidelines):VoiceGuidelines=>{return{personality:source.personality,tone_attributes:[...source.tone_attributes],key_messages:[...source.key_messages],messaging_do:[...source.messaging_do],messaging_dont:[...source.messaging_dont],example_headlines:[...source.example_headlines],example_taglines:[...source.example_taglines]}},[])
//Handle entering edit mode
const handleEditModeChange=useCallback((editing:boolean)=>{setIsEditing(editing)
if(editing){setEditData(deepCopy(data));setSaveError(null);setSaveSuccess(false)}else{setEditData(null);setSaveError(null);setSaveSuccess(false)}},[data,deepCopy])
//Handle save
const handleSave=useCallback(async()=>{if(!editData)return
setIsSaving(true);setSaveError(null);setSaveSuccess(false)
try{await updateIdentitySection('voice',editData);setSaveSuccess(true);setEditData(null);setIsEditing(false);toast.success('Voice guidelines saved')}catch(err){console.error('[VoiceSection] Save failed:',err);setSaveError(err instanceof Error?err.message:'Failed to save changes')}finally{setIsSaving(false)}},[editData,updateIdentitySection])
//Generic string list update helpers
const updateListItem=(field:keyof Pick<VoiceGuidelines,'tone_attributes'|'key_messages'|'messaging_do'|'messaging_dont'|'example_headlines'|'example_taglines'>,index:number,value:string)=>{if(!editData)return;const newList=[...editData[field]];newList[index]=value;setEditData({...editData,[field]:newList})}
const addListItem=(field:keyof Pick<VoiceGuidelines,'tone_attributes'|'key_messages'|'messaging_do'|'messaging_dont'|'example_headlines'|'example_taglines'>)=>{if(!editData)return;setEditData({...editData,[field]:[...editData[field],'']})}
const removeListItem=(field:keyof Pick<VoiceGuidelines,'tone_attributes'|'key_messages'|'messaging_do'|'messaging_dont'|'example_headlines'|'example_taglines'>,index:number)=>{if(!editData)return;const newList=editData[field].filter((_,i)=>i!==index);setEditData({...editData,[field]:newList})}
//Reusable badge list renderer for view mode
const renderBadgeList=(items:string[],colorClass:string)=>(<div className="mt-2 flex flex-wrap gap-2">{items.length>0?(items.map((item,index)=>(<span key={index} className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${colorClass}`}>{item}</span>))):(<span className="text-xs text-muted-foreground italic">None specified</span>)}</div>)
//Reusable string list editor for edit mode
const renderStringListEditor=(label:string,field:keyof Pick<VoiceGuidelines,'tone_attributes'|'key_messages'|'messaging_do'|'messaging_dont'|'example_headlines'|'example_taglines'>,placeholder:string)=>{if(!editData)return null;const items=editData[field]
return(<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{label}</label><div className="mt-1 space-y-2">{items.map((item,index)=>(<div key={index} className="flex gap-2"><Input value={item} onChange={(e)=>updateListItem(field,index,e.target.value)} placeholder={placeholder} disabled={isSaving} className="flex-1"/><Button type="button" variant="ghost" size="sm" onClick={()=>removeListItem(field,index)} disabled={isSaving||items.length<=0} className="px-2 text-muted-foreground hover:text-destructive">&times;</Button></div>))}<Button type="button" variant="outline" size="sm" onClick={()=>addListItem(field)} disabled={isSaving} className="w-full">+ Add {label.replace(/s$/,'')}</Button></div></div>)}
//View mode content
const viewContent=(<div className="space-y-4 max-w-prose">{/* Success message */}{saveSuccess&&(<Alert className="bg-success-a10 border-success/20"><CheckCircle2 className="h-4 w-4 text-success"/><AlertDescription className="text-success">Changes saved. AI context refreshed automatically.</AlertDescription></Alert>)}
<div className="grid gap-5">{/* Personality */}<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Brand Personality</label><p className="mt-1 text-sm leading-relaxed whitespace-pre-wrap">{data.personality||'Not specified'}</p></div>
{/* Tone Attributes */}<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Tone Attributes</label>{renderBadgeList(data.tone_attributes,'bg-muted text-muted-foreground')}</div>
{/* Key Messages */}<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Key Messages</label>{renderBadgeList(data.key_messages,'bg-muted text-muted-foreground')}</div>
{/* Messaging Do's & Don'ts - side by side */}<div className="grid grid-cols-2 gap-4"><div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Do</label>{renderBadgeList(data.messaging_do,'bg-success-a10 text-success')}</div><div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Avoid</label>{renderBadgeList(data.messaging_dont,'bg-brand-a10 text-brand-600 dark:text-brand-500')}</div></div>
{/* Example Headlines */}{data.example_headlines.length>0&&(<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Example Headlines</label><ul className="mt-2 space-y-1">{data.example_headlines.map((headline,index)=>(<li key={index} className="text-sm italic text-muted-foreground">"{headline}"</li>))}</ul></div>)}
{/* Example Taglines */}{data.example_taglines.length>0&&(<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Example Taglines</label><ul className="mt-2 space-y-1">{data.example_taglines.map((tagline,index)=>(<li key={index} className="text-sm italic text-muted-foreground">"{tagline}"</li>))}</ul></div>)}</div></div>)
//Edit mode content
const editContent=editData&&(<div className="space-y-4">{/* Error message */}{saveError&&(<Alert variant="destructive"><AlertCircle className="h-4 w-4"/><AlertDescription>{saveError}</AlertDescription></Alert>)}
<div className="grid gap-4">{/* Personality */}<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Brand Personality</label><textarea value={editData.personality} onChange={(e)=>setEditData({...editData,personality:e.target.value})} className="mt-1 w-full min-h-[100px] rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50" placeholder="Describe the brand's personality..." disabled={isSaving}/></div>
{/* Tone Attributes */}{renderStringListEditor('Tone Attributes','tone_attributes','e.g., warm, professional')}
{/* Key Messages */}{renderStringListEditor('Key Messages','key_messages','Enter a key message')}
{/* Messaging Do's */}{renderStringListEditor('Messaging Do\'s','messaging_do','e.g., Use inclusive language')}
{/* Messaging Don'ts */}{renderStringListEditor('Messaging Don\'ts','messaging_dont','e.g., Avoid jargon')}
{/* Example Headlines */}{renderStringListEditor('Example Headlines','example_headlines','Enter an example headline')}
{/* Example Taglines */}{renderStringListEditor('Example Taglines','example_taglines','Enter an example tagline')}</div>
{/* Save button */}<div className="flex justify-end pt-2 border-t border-border"><Button onClick={handleSave} disabled={isSaving} className="gap-1.5">{isSaving?(<><Spinner className="h-4 w-4"/>Saving...</>):(<><Save className="h-4 w-4"/>Save Changes</>)}</Button></div></div>)
//Build subtitle from tone attributes
const subtitle=data.tone_attributes.length>0?data.tone_attributes.slice(0,3).join(', ')+(data.tone_attributes.length>3?'...':''):data.personality?.substring(0,50)||'Voice guidelines'
return(<MemorySection id="voice" title="Voice Guidelines" subtitle={subtitle} editable isEditing={isEditing} isSaving={isSaving} onEditModeChange={handleEditModeChange} editContent={editContent}>{viewContent}</MemorySection>)}
