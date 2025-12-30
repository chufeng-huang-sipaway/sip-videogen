import{useState,useCallback}from'react'
import{Save,AlertCircle,CheckCircle2}from'lucide-react'
import{Button}from'@/components/ui/button'
import{Input}from'@/components/ui/input'
import{Alert,AlertDescription}from'@/components/ui/alert'
import{Spinner}from'@/components/ui/spinner'
import{MemorySection}from'../MemorySection'
import{useBrand}from'@/context/BrandContext'
import{toast}from'@/components/ui/toaster'
import type{BrandCoreIdentity}from'@/types/brand-identity'
interface CoreSectionProps{data:BrandCoreIdentity}
export function CoreSection({data}:CoreSectionProps){
const{updateIdentitySection}=useBrand()
const[editData,setEditData]=useState<BrandCoreIdentity|null>(null)
const[isEditing,setIsEditing]=useState(false)
const[isSaving,setIsSaving]=useState(false)
const[saveError,setSaveError]=useState<string|null>(null)
const[saveSuccess,setSaveSuccess]=useState(false)
const handleEditModeChange=useCallback((editing:boolean)=>{setIsEditing(editing)
if(editing){setEditData({...data,values:[...data.values]});setSaveError(null);setSaveSuccess(false)}else{setEditData(null);setSaveError(null);setSaveSuccess(false)}},[data])
const handleSave=useCallback(async()=>{if(!editData)return
setIsSaving(true);setSaveError(null);setSaveSuccess(false)
try{await updateIdentitySection('core',editData);setSaveSuccess(true);toast.success('Core identity saved');setEditData(null);setIsEditing(false)
}catch(err){setSaveError(err instanceof Error?err.message:'Failed to save changes')
}finally{setIsSaving(false)}},[editData,updateIdentitySection])
const updateField=<K extends keyof BrandCoreIdentity>(field:K,value:BrandCoreIdentity[K])=>{if(!editData)return;setEditData({...editData,[field]:value})}
const updateValue=(index:number,newValue:string)=>{if(!editData)return;const newValues=[...editData.values];newValues[index]=newValue;setEditData({...editData,values:newValues})}
const addValue=()=>{if(!editData)return;setEditData({...editData,values:[...editData.values,'']})}
const removeValue=(index:number)=>{if(!editData)return;const newValues=editData.values.filter((_,i)=>i!==index);setEditData({...editData,values:newValues})}
const viewContent=(<div className="space-y-4 max-w-prose">
{saveSuccess&&(<Alert className="bg-success-a10 border-success/20"><CheckCircle2 className="h-4 w-4 text-success"/><AlertDescription className="text-success">Changes saved. AI context refreshed automatically.</AlertDescription></Alert>)}
<div className="grid gap-5">
<div className="flex flex-wrap gap-x-8 gap-y-3">
<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Brand Name</label><p className="mt-1 text-sm font-medium">{data.name}</p></div>
<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Tagline</label><p className="mt-1 text-sm italic text-muted-foreground">{data.tagline}</p></div>
</div>
<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Mission</label><p className="mt-1 text-sm leading-relaxed whitespace-pre-wrap">{data.mission}</p></div>
<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Brand Story</label><p className="mt-1 text-sm leading-relaxed whitespace-pre-wrap text-muted-foreground">{data.brand_story}</p></div>
<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Values</label>
<div className="mt-2 flex flex-wrap gap-2">{data.values.map((value,index)=>(<span key={index} className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-muted text-muted-foreground">{value}</span>))}</div>
</div>
</div>
</div>)
const editContent=editData&&(<div className="space-y-4">
{saveError&&(<Alert variant="destructive"><AlertCircle className="h-4 w-4"/><AlertDescription>{saveError}</AlertDescription></Alert>)}
<div className="grid gap-4">
<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Brand Name</label><Input value={editData.name} onChange={(e)=>updateField('name',e.target.value)} className="mt-1" disabled={isSaving}/></div>
<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Tagline</label><Input value={editData.tagline} onChange={(e)=>updateField('tagline',e.target.value)} className="mt-1" disabled={isSaving}/></div>
<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Mission</label><textarea value={editData.mission} onChange={(e)=>updateField('mission',e.target.value)} className="mt-1 w-full min-h-[80px] rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50" disabled={isSaving}/></div>
<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Brand Story</label><textarea value={editData.brand_story} onChange={(e)=>updateField('brand_story',e.target.value)} className="mt-1 w-full min-h-[120px] rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50" disabled={isSaving}/></div>
<div><label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Values</label>
<div className="mt-1 space-y-2">{editData.values.map((value,index)=>(<div key={index} className="flex gap-2"><Input value={value} onChange={(e)=>updateValue(index,e.target.value)} placeholder={`Value ${index+1}`} disabled={isSaving} className="flex-1"/><Button type="button" variant="ghost" size="sm" onClick={()=>removeValue(index)} disabled={isSaving||editData.values.length<=1} className="px-2 text-muted-foreground hover:text-destructive">&times;</Button></div>))}
<Button type="button" variant="outline" size="sm" onClick={addValue} disabled={isSaving} className="w-full">+ Add Value</Button>
</div>
</div>
</div>
<div className="flex justify-end pt-2 border-t border-border"><Button onClick={handleSave} disabled={isSaving} className="gap-1.5">{isSaving?(<><Spinner className="h-4 w-4"/>Saving...</>):(<><Save className="h-4 w-4"/>Save Changes</>)}</Button></div>
</div>)
return(<MemorySection id="core" title="Core Identity" subtitle={`${data.name} - ${data.tagline}`} editable isEditing={isEditing} isSaving={isSaving} onEditModeChange={handleEditModeChange} editContent={editContent}>{viewContent}</MemorySection>)}
