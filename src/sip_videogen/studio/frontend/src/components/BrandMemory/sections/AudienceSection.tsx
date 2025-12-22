import{useState,useCallback}from'react'
import{Save,AlertCircle,CheckCircle2}from'lucide-react'
import{Button}from'@/components/ui/button'
import{Input}from'@/components/ui/input'
import{Alert,AlertDescription}from'@/components/ui/alert'
import{Spinner}from'@/components/ui/spinner'
import{MemorySection}from'../MemorySection'
import{useBrand}from'@/context/BrandContext'
import{toast}from'@/components/ui/toaster'
import type{AudienceProfile}from'@/types/brand-identity'
interface AudienceSectionProps{
/** Current audience profile data */
data:AudienceProfile}
/**
 * AudienceSection - Displays and edits target audience profile.
 *
 * Fields:
 * - primary_summary: High-level audience description
 * - age_range: Target age range
 * - gender: Target gender demographics
 * - income_level: Target income level
 * - location: Target geographic location
 * - interests: List of audience interests
 * - values: List of audience values
 * - lifestyle: Lifestyle description
 * - pain_points: List of pain points
 * - desires: List of desires/goals
 *
 * Uses MemorySection wrapper for collapse/expand and edit mode toggle.
 */
export function AudienceSection({data}:AudienceSectionProps){
const{updateIdentitySection}=useBrand()
//Edit state - local copy of data being edited
const[editData,setEditData]=useState<AudienceProfile|null>(null)
const[isEditing,setIsEditing]=useState(false)
const[isSaving,setIsSaving]=useState(false)
const[saveError,setSaveError]=useState<string|null>(null)
const[saveSuccess,setSaveSuccess]=useState(false)
//Deep copy helper to ensure all arrays are properly cloned
const deepCopyAudienceProfile=(profile:AudienceProfile):AudienceProfile=>({...profile,interests:[...profile.interests],values:[...profile.values],pain_points:[...profile.pain_points],desires:[...profile.desires]})
//Handle entering edit mode
const handleEditModeChange=useCallback((editing:boolean)=>{setIsEditing(editing)
if(editing){setEditData(deepCopyAudienceProfile(data));setSaveError(null);setSaveSuccess(false)}else{setEditData(null);setSaveError(null);setSaveSuccess(false)}},[data])
//Handle save
const handleSave=useCallback(async()=>{if(!editData)return
setIsSaving(true);setSaveError(null);setSaveSuccess(false)
try{await updateIdentitySection('audience',editData);setSaveSuccess(true);setEditData(null);setIsEditing(false);toast.success('Audience profile saved')}catch(err){console.error('[AudienceSection] Save failed:',err);setSaveError(err instanceof Error?err.message:'Failed to save changes')}finally{setIsSaving(false)}},[editData,updateIdentitySection])
//Handle field changes
const updateField=<K extends keyof AudienceProfile>(field:K,value:AudienceProfile[K])=>{if(!editData)return;setEditData({...editData,[field]:value})}
//Generic string array helpers
const updateArrayItem=(field:'interests'|'values'|'pain_points'|'desires',index:number,newValue:string)=>{if(!editData)return;const newArray=[...editData[field]];newArray[index]=newValue;setEditData({...editData,[field]:newArray})}
const addArrayItem=(field:'interests'|'values'|'pain_points'|'desires')=>{if(!editData)return;setEditData({...editData,[field]:[...editData[field],'']})}
const removeArrayItem=(field:'interests'|'values'|'pain_points'|'desires',index:number)=>{if(!editData)return;const newArray=editData[field].filter((_,i)=>i!==index);setEditData({...editData,[field]:newArray})}
//Reusable string list editor
const renderStringListEditor=(field:'interests'|'values'|'pain_points'|'desires',label:string,placeholder:string)=>{if(!editData)return null
return(<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{label}</label><div className="mt-1 space-y-2">{editData[field].map((item,index)=>(<div key={index} className="flex gap-2"><Input value={item} onChange={(e)=>updateArrayItem(field,index,e.target.value)} placeholder={placeholder} disabled={isSaving} className="flex-1"/><Button type="button" variant="ghost" size="sm" onClick={()=>removeArrayItem(field,index)} disabled={isSaving} className="px-2 text-muted-foreground hover:text-destructive">&times;</Button></div>))}<Button type="button" variant="outline" size="sm" onClick={()=>addArrayItem(field)} disabled={isSaving} className="w-full">+ Add {label.replace(/s$/,'')}</Button></div></div>)}
//View mode content
const viewContent=(<div className="space-y-4">{/* Success message */}{saveSuccess&&(<Alert className="bg-green-500/10 border-green-500/20"><CheckCircle2 className="h-4 w-4 text-green-500"/><AlertDescription className="text-green-700 dark:text-green-400">Changes saved. AI context refreshed automatically.</AlertDescription></Alert>)}
<div className="grid gap-4">{/* Primary Summary */}<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Primary Summary</label><p className="mt-1 text-sm whitespace-pre-wrap">{data.primary_summary}</p></div>
{/* Demographics */}<div className="grid grid-cols-2 gap-4"><div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Age Range</label><p className="mt-1 text-sm">{data.age_range}</p></div>
<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Gender</label><p className="mt-1 text-sm">{data.gender}</p></div>
<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Income Level</label><p className="mt-1 text-sm">{data.income_level}</p></div>
<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Location</label><p className="mt-1 text-sm">{data.location}</p></div></div>
{/* Lifestyle */}<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Lifestyle</label><p className="mt-1 text-sm whitespace-pre-wrap">{data.lifestyle}</p></div>
{/* Interests */}<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Interests</label><div className="mt-1 flex flex-wrap gap-2">{data.interests.map((interest,index)=>(<span key={index} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">{interest}</span>))}</div></div>
{/* Values */}<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Values</label><div className="mt-1 flex flex-wrap gap-2">{data.values.map((value,index)=>(<span key={index} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300">{value}</span>))}</div></div>
{/* Pain Points */}<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Pain Points</label><div className="mt-1 flex flex-wrap gap-2">{data.pain_points.map((point,index)=>(<span key={index} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300">{point}</span>))}</div></div>
{/* Desires */}<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Desires</label><div className="mt-1 flex flex-wrap gap-2">{data.desires.map((desire,index)=>(<span key={index} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300">{desire}</span>))}</div></div></div></div>)
//Edit mode content
const editContent=editData&&(<div className="space-y-4">{/* Error message */}{saveError&&(<Alert variant="destructive"><AlertCircle className="h-4 w-4"/><AlertDescription>{saveError}</AlertDescription></Alert>)}
<div className="grid gap-4">{/* Primary Summary */}<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Primary Summary</label><textarea value={editData.primary_summary} onChange={(e)=>updateField('primary_summary',e.target.value)} className="mt-1 w-full min-h-[80px] rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50" disabled={isSaving}/></div>
{/* Demographics */}<div className="grid grid-cols-2 gap-4"><div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Age Range</label><Input value={editData.age_range} onChange={(e)=>updateField('age_range',e.target.value)} className="mt-1" disabled={isSaving} placeholder="e.g., 25-45"/></div>
<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Gender</label><Input value={editData.gender} onChange={(e)=>updateField('gender',e.target.value)} className="mt-1" disabled={isSaving} placeholder="e.g., All genders"/></div>
<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Income Level</label><Input value={editData.income_level} onChange={(e)=>updateField('income_level',e.target.value)} className="mt-1" disabled={isSaving} placeholder="e.g., Middle to upper-middle class"/></div>
<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Location</label><Input value={editData.location} onChange={(e)=>updateField('location',e.target.value)} className="mt-1" disabled={isSaving} placeholder="e.g., Urban areas, United States"/></div></div>
{/* Lifestyle */}<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Lifestyle</label><textarea value={editData.lifestyle} onChange={(e)=>updateField('lifestyle',e.target.value)} className="mt-1 w-full min-h-[60px] rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50" disabled={isSaving} placeholder="Describe the typical lifestyle of your target audience..."/></div>
{/* Interests */}{renderStringListEditor('interests','Interests','e.g., Technology, Travel')}
{/* Values */}{renderStringListEditor('values','Values','e.g., Sustainability, Quality')}
{/* Pain Points */}{renderStringListEditor('pain_points','Pain Points','e.g., Time constraints')}
{/* Desires */}{renderStringListEditor('desires','Desires','e.g., Convenience, Status')}</div>
{/* Save button */}<div className="flex justify-end pt-2 border-t border-border"><Button onClick={handleSave} disabled={isSaving} className="gap-1.5">{isSaving?(<><Spinner className="h-4 w-4"/>Saving...</>):(<><Save className="h-4 w-4"/>Save Changes</>)}</Button></div></div>)
return(<MemorySection id="audience" title="Target Audience" subtitle={data.primary_summary.slice(0,80)+(data.primary_summary.length>80?'...':'')} editable isEditing={isEditing} isSaving={isSaving} onEditModeChange={handleEditModeChange} editContent={editContent}>{viewContent}</MemorySection>)}
