import{useState,useCallback}from'react'
import{Save,AlertCircle,CheckCircle2}from'lucide-react'
import{Button}from'@/components/ui/button'
import{Input}from'@/components/ui/input'
import{Alert,AlertDescription}from'@/components/ui/alert'
import{Spinner}from'@/components/ui/spinner'
import{MemorySection}from'../MemorySection'
import{useBrand}from'@/context/BrandContext'
import{toast}from'@/components/ui/toaster'
import type{CompetitivePositioning}from'@/types/brand-identity'
interface PositioningSectionProps{
/** Current competitive positioning data */
data:CompetitivePositioning}
/**
 * Deep copy helper for CompetitivePositioning.
 * Ensures all arrays are properly cloned when entering edit mode.
 */
function deepCopyPositioning(data:CompetitivePositioning):CompetitivePositioning{return{market_category:data.market_category,unique_value_proposition:data.unique_value_proposition,primary_competitors:[...data.primary_competitors],differentiation:data.differentiation,positioning_statement:data.positioning_statement}}
/**
 * PositioningSection - Displays and edits competitive positioning.
 *
 * Fields:
 * - market_category: Market/industry category
 * - unique_value_proposition: Unique value proposition (UVP)
 * - primary_competitors: List of primary competitors
 * - differentiation: What makes the brand different
 * - positioning_statement: Full positioning statement
 *
 * Uses MemorySection wrapper for collapse/expand and edit mode toggle.
 */
export function PositioningSection({data}:PositioningSectionProps){
const{updateIdentitySection}=useBrand()
//Edit state - local copy of data being edited
const[editData,setEditData]=useState<CompetitivePositioning|null>(null)
const[isEditing,setIsEditing]=useState(false)
const[isSaving,setIsSaving]=useState(false)
const[saveError,setSaveError]=useState<string|null>(null)
const[saveSuccess,setSaveSuccess]=useState(false)
//Handle entering edit mode
const handleEditModeChange=useCallback((editing:boolean)=>{setIsEditing(editing)
if(editing){setEditData(deepCopyPositioning(data));setSaveError(null);setSaveSuccess(false)}else{setEditData(null);setSaveError(null);setSaveSuccess(false)}},[data])
//Handle save
const handleSave=useCallback(async()=>{if(!editData)return
setIsSaving(true);setSaveError(null);setSaveSuccess(false)
try{await updateIdentitySection('positioning',editData);setSaveSuccess(true);setEditData(null);setIsEditing(false);toast.success('Market positioning saved')}catch(err){console.error('[PositioningSection] Save failed:',err);setSaveError(err instanceof Error?err.message:'Failed to save changes')}finally{setIsSaving(false)}},[editData,updateIdentitySection])
//Handle field changes
const updateField=<K extends keyof CompetitivePositioning>(field:K,value:CompetitivePositioning[K])=>{if(!editData)return;setEditData({...editData,[field]:value})}
//Helper to render a string list editor
const renderStringListEditor=(field:'primary_competitors',label:string,placeholder:string)=>{if(!editData)return null;const items=editData[field]
const updateItem=(index:number,newValue:string)=>{const newItems=[...items];newItems[index]=newValue;setEditData({...editData,[field]:newItems})}
const addItem=()=>{setEditData({...editData,[field]:[...items,'']})}
const removeItem=(index:number)=>{const newItems=items.filter((_,i)=>i!==index);setEditData({...editData,[field]:newItems})}
return(<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{label}</label><div className="mt-1 space-y-2">{items.map((item,index)=>(<div key={index} className="flex gap-2"><Input value={item} onChange={(e)=>updateItem(index,e.target.value)} placeholder={placeholder} disabled={isSaving} className="flex-1"/><Button type="button" variant="ghost" size="sm" onClick={()=>removeItem(index)} disabled={isSaving} className="px-2 text-muted-foreground hover:text-destructive">&times;</Button></div>))}<Button type="button" variant="outline" size="sm" onClick={addItem} disabled={isSaving} className="w-full">+ Add {label.replace(/s$/,'')}</Button></div></div>)}
//View mode content
const viewContent=(<div className="space-y-4">{/* Success message */}{saveSuccess&&(<Alert className="bg-success-a10 border-success/20"><CheckCircle2 className="h-4 w-4 text-success"/><AlertDescription className="text-success">Changes saved. AI context refreshed automatically.</AlertDescription></Alert>)}
<div className="grid gap-4">{/* Market Category */}<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Market Category</label><p className="mt-1 text-sm">{data.market_category}</p></div>
{/* Unique Value Proposition */}<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Unique Value Proposition</label><p className="mt-1 text-sm whitespace-pre-wrap">{data.unique_value_proposition}</p></div>
{/* Primary Competitors */}<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Primary Competitors</label><div className="mt-1 flex flex-wrap gap-2">{data.primary_competitors.length>0?(data.primary_competitors.map((competitor,index)=>(<span key={index} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-muted text-muted-foreground">{competitor}</span>))):(<span className="text-sm text-muted-foreground italic">No competitors defined</span>)}</div></div>
{/* Differentiation */}<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Differentiation</label><p className="mt-1 text-sm whitespace-pre-wrap">{data.differentiation}</p></div>
{/* Positioning Statement */}<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Positioning Statement</label><p className="mt-1 text-sm whitespace-pre-wrap italic">"{data.positioning_statement}"</p></div></div></div>)
//Edit mode content
const editContent=editData&&(<div className="space-y-4">{/* Error message */}{saveError&&(<Alert variant="destructive"><AlertCircle className="h-4 w-4"/><AlertDescription>{saveError}</AlertDescription></Alert>)}
<div className="grid gap-4">{/* Market Category */}<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Market Category</label><Input value={editData.market_category} onChange={(e)=>updateField('market_category',e.target.value)} placeholder="e.g., Premium Coffee & Lifestyle" className="mt-1" disabled={isSaving}/></div>
{/* Unique Value Proposition */}<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Unique Value Proposition</label><textarea value={editData.unique_value_proposition} onChange={(e)=>updateField('unique_value_proposition',e.target.value)} placeholder="What makes your brand uniquely valuable to customers?" className="mt-1 w-full min-h-[80px] rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50" disabled={isSaving}/></div>
{/* Primary Competitors */}{renderStringListEditor('primary_competitors','Primary Competitors','Competitor name')}
{/* Differentiation */}<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Differentiation</label><textarea value={editData.differentiation} onChange={(e)=>updateField('differentiation',e.target.value)} placeholder="What differentiates your brand from competitors?" className="mt-1 w-full min-h-[80px] rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50" disabled={isSaving}/></div>
{/* Positioning Statement */}<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Positioning Statement</label><textarea value={editData.positioning_statement} onChange={(e)=>updateField('positioning_statement',e.target.value)} placeholder="For [target audience] who [need], [brand name] is the [category] that [key benefit] because [reasons to believe]." className="mt-1 w-full min-h-[100px] rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50" disabled={isSaving}/></div></div>
{/* Save button */}<div className="flex justify-end pt-2 border-t border-border"><Button onClick={handleSave} disabled={isSaving} className="gap-1.5">{isSaving?(<><Spinner className="h-4 w-4"/>Saving...</>):(<><Save className="h-4 w-4"/>Save Changes</>)}</Button></div></div>)
return(<MemorySection id="positioning" title="Market Positioning" subtitle={data.market_category} editable isEditing={isEditing} isSaving={isSaving} onEditModeChange={handleEditModeChange} editContent={editContent}>{viewContent}</MemorySection>)}
