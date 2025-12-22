import{useState,useCallback}from'react'
import{Save,AlertCircle,CheckCircle2}from'lucide-react'
import{Button}from'@/components/ui/button'
import{Input}from'@/components/ui/input'
import{Alert,AlertDescription}from'@/components/ui/alert'
import{Spinner}from'@/components/ui/spinner'
import{MemorySection}from'../MemorySection'
import{useBrand}from'@/context/BrandContext'
import{toast}from'@/components/ui/toaster'
import type{ConstraintsAvoidData}from'@/types/brand-identity'
interface ConstraintsAvoidSectionProps{
/** Current constraints and avoid data */
data:ConstraintsAvoidData}
/**
 * Deep copy helper for ConstraintsAvoidData.
 * Ensures all arrays are properly cloned when entering edit mode.
 */
function deepCopyConstraintsAvoid(data:ConstraintsAvoidData):ConstraintsAvoidData{return{constraints:[...data.constraints],avoid:[...data.avoid]}}
/**
 * ConstraintsAvoidSection - Displays and edits brand constraints and things to avoid.
 *
 * Fields:
 * - constraints: Things the brand must always adhere to (brand rules, requirements)
 * - avoid: Things the brand should never do (prohibited content, messaging to avoid)
 *
 * Uses MemorySection wrapper for collapse/expand and edit mode toggle.
 */
export function ConstraintsAvoidSection({data}:ConstraintsAvoidSectionProps){
const{updateIdentitySection}=useBrand()
//Edit state - local copy of data being edited
const[editData,setEditData]=useState<ConstraintsAvoidData|null>(null)
const[isEditing,setIsEditing]=useState(false)
const[isSaving,setIsSaving]=useState(false)
const[saveError,setSaveError]=useState<string|null>(null)
const[saveSuccess,setSaveSuccess]=useState(false)
//Handle entering edit mode
const handleEditModeChange=useCallback((editing:boolean)=>{setIsEditing(editing)
if(editing){setEditData(deepCopyConstraintsAvoid(data));setSaveError(null);setSaveSuccess(false)}else{setEditData(null);setSaveError(null);setSaveSuccess(false)}},[data])
//Handle save
const handleSave=useCallback(async()=>{if(!editData)return
setIsSaving(true);setSaveError(null);setSaveSuccess(false)
try{await updateIdentitySection('constraints_avoid',editData);setSaveSuccess(true);setEditData(null);setIsEditing(false);toast.success('Constraints saved')}catch(err){console.error('[ConstraintsAvoidSection] Save failed:',err);setSaveError(err instanceof Error?err.message:'Failed to save changes')}finally{setIsSaving(false)}},[editData,updateIdentitySection])
//Helper to render a string list editor for constraints or avoid
const renderStringListEditor=(field:'constraints'|'avoid',label:string,placeholder:string)=>{if(!editData)return null;const items=editData[field]
const updateItem=(index:number,newValue:string)=>{const newItems=[...items];newItems[index]=newValue;setEditData({...editData,[field]:newItems})}
const addItem=()=>{setEditData({...editData,[field]:[...items,'']})}
const removeItem=(index:number)=>{const newItems=items.filter((_,i)=>i!==index);setEditData({...editData,[field]:newItems})}
return(<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{label}</label><div className="mt-1 space-y-2">{items.map((item,index)=>(<div key={index} className="flex gap-2"><Input value={item} onChange={(e)=>updateItem(index,e.target.value)} placeholder={placeholder} disabled={isSaving} className="flex-1"/><Button type="button" variant="ghost" size="sm" onClick={()=>removeItem(index)} disabled={isSaving} className="px-2 text-muted-foreground hover:text-destructive">&times;</Button></div>))}<Button type="button" variant="outline" size="sm" onClick={addItem} disabled={isSaving} className="w-full">+ Add {label.replace(/s$/,'')}</Button></div></div>)}
//Generate subtitle - summary of constraints and avoid counts
const constraintsCount=data.constraints.length
const avoidCount=data.avoid.length
const subtitle=constraintsCount>0||avoidCount>0?`${constraintsCount} constraint${constraintsCount!==1?'s':''}, ${avoidCount} to avoid`:'No constraints defined'
//View mode content
const viewContent=(<div className="space-y-4">{/* Success message */}{saveSuccess&&(<Alert className="bg-green-500/10 border-green-500/20"><CheckCircle2 className="h-4 w-4 text-green-500"/><AlertDescription className="text-green-700 dark:text-green-400">Changes saved. AI context refreshed automatically.</AlertDescription></Alert>)}
<div className="grid gap-4">{/* Constraints */}<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Brand Constraints</label><p className="text-xs text-muted-foreground mb-2">Rules and requirements the brand must always follow</p><div className="mt-1 flex flex-wrap gap-2">{data.constraints.length>0?(data.constraints.map((constraint,index)=>(<span key={index} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300">{constraint}</span>))):(<span className="text-sm text-muted-foreground italic">No constraints defined</span>)}</div></div>
{/* Avoid */}<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Things to Avoid</label><p className="text-xs text-muted-foreground mb-2">Content, messaging, or approaches the brand should never use</p><div className="mt-1 flex flex-wrap gap-2">{data.avoid.length>0?(data.avoid.map((item,index)=>(<span key={index} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300">{item}</span>))):(<span className="text-sm text-muted-foreground italic">No items to avoid defined</span>)}</div></div></div></div>)
//Edit mode content
const editContent=editData&&(<div className="space-y-4">{/* Error message */}{saveError&&(<Alert variant="destructive"><AlertCircle className="h-4 w-4"/><AlertDescription>{saveError}</AlertDescription></Alert>)}
<div className="grid gap-4">{/* Constraints */}{renderStringListEditor('constraints','Brand Constraints','e.g., Always use eco-friendly messaging')}
{/* Avoid */}{renderStringListEditor('avoid','Things to Avoid','e.g., Never use aggressive sales language')}</div>
{/* Save button */}<div className="flex justify-end pt-2 border-t border-border"><Button onClick={handleSave} disabled={isSaving} className="gap-1.5">{isSaving?(<><Spinner className="h-4 w-4"/>Saving...</>):(<><Save className="h-4 w-4"/>Save Changes</>)}</Button></div></div>)
return(<MemorySection id="constraints_avoid" title="Constraints & Avoid" subtitle={subtitle} editable isEditing={isEditing} isSaving={isSaving} onEditModeChange={handleEditModeChange} editContent={editContent}>{viewContent}</MemorySection>)}
