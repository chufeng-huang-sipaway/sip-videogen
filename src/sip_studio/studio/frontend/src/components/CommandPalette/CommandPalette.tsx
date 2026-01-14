import{useState,useEffect,useCallback}from'react'
import{Command,CommandInput,CommandList,CommandEmpty,CommandGroup,CommandItem,CommandShortcut,CommandSeparator}from'@/components/ui/command'
import{Dialog,DialogContent,DialogTitle}from'@/components/ui/dialog'
import{useBrand}from'@/context/BrandContext'
import type{BrandEntry}from'@/lib/bridge'
import{FolderKanban,Settings,Building2,Check}from'lucide-react'
interface CommandPaletteProps{onNewProject?:()=>void;onOpenSettings?:()=>void}
//Check if active element is a text-editable input
function isTextEditableInput(el:Element|null):boolean{
if(!el)return false
if(el.tagName==='TEXTAREA')return true
if((el as HTMLElement).isContentEditable)return true
if(el.tagName==='INPUT'){const type=(el as HTMLInputElement).type
const textTypes=['text','search','email','password','url','tel','number']
return textTypes.includes(type)}
return false}
export function CommandPalette({onNewProject,onOpenSettings}:CommandPaletteProps){
const[open,setOpen]=useState(false)
const{brands,activeBrand,selectBrand}=useBrand()
//Keyboard handler for ⌘K / Ctrl+K
useEffect(()=>{
const handler=(e:KeyboardEvent)=>{
//Skip during IME composition or if already handled
if(e.isComposing||e.defaultPrevented||e.repeat)return
//Check if in text-editable element
if(isTextEditableInput(document.activeElement))return
//⌘K or Ctrl+K (case-insensitive)
if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();setOpen(true)}}
window.addEventListener('keydown',handler)
return()=>window.removeEventListener('keydown',handler)},[])
const handleSelect=useCallback((value:string)=>{
if(value.startsWith('brand:')){const slug=value.replace('brand:','');selectBrand(slug);setOpen(false)}
else if(value==='new-project'){onNewProject?.();setOpen(false)}
else if(value==='settings'){onOpenSettings?.();setOpen(false)}},[selectBrand,onNewProject,onOpenSettings])
const runCommand=useCallback((cmd:()=>void)=>{setOpen(false);cmd()},[])
return(<Dialog open={open} onOpenChange={setOpen}>
<DialogContent className="overflow-hidden p-0 max-w-[520px] bg-background/95 backdrop-blur-2xl border border-white/20 shadow-2xl rounded-2xl ring-1 ring-black/5 [&>button]:hidden">
<DialogTitle className="sr-only">Command Palette</DialogTitle>
<Command className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-muted-foreground [&_[cmdk-group]:not([hidden])_~[cmdk-group]]:pt-0 [&_[cmdk-group]]:px-2 [&_[cmdk-input-wrapper]_svg]:h-5 [&_[cmdk-input-wrapper]_svg]:w-5 [&_[cmdk-input]]:h-12 [&_[cmdk-item]]:px-2 [&_[cmdk-item]]:py-3 [&_[cmdk-item]_svg]:h-5 [&_[cmdk-item]_svg]:w-5">
<CommandInput placeholder="Search commands..."/>
<CommandList className="max-h-[400px]">
<CommandEmpty>No results found.</CommandEmpty>
{/* Actions group */}
<CommandGroup heading="Actions">
<CommandItem value="new-project" onSelect={()=>runCommand(()=>onNewProject?.())}>
<FolderKanban className="mr-2 h-4 w-4"/>
<span>New Project</span>
<CommandShortcut>⌘N</CommandShortcut>
</CommandItem>
<CommandItem value="settings" onSelect={()=>runCommand(()=>onOpenSettings?.())}>
<Settings className="mr-2 h-4 w-4"/>
<span>Preferences</span>
<CommandShortcut>⌘,</CommandShortcut>
</CommandItem>
</CommandGroup>
<CommandSeparator/>
{/* Brands group */}
{brands.length>0&&(<CommandGroup heading="Switch Brand">
{brands.map((brand:BrandEntry)=>(<CommandItem key={brand.slug} value={`brand:${brand.slug} ${brand.name}`} onSelect={()=>handleSelect(`brand:${brand.slug}`)}>
<Building2 className="mr-2 h-4 w-4"/>
<span className="flex-1">{brand.name}</span>
{activeBrand===brand.slug&&<Check className="ml-auto h-4 w-4 text-success"/>}
</CommandItem>))}
</CommandGroup>)}
</CommandList>
</Command>
</DialogContent>
</Dialog>)}
