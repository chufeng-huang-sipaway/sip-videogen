import {useState,useEffect} from 'react'
import {Package,Palette,ChevronRight,ChevronDown,Plus,Library} from 'lucide-react'
import {Button} from '@/components/ui/button'
import {useProducts} from '@/context/ProductContext'
import {useTemplates} from '@/context/TemplateContext'
import {useBrand} from '@/context/BrandContext'
import {ProductsSection} from './ProductsSection'
import {TemplatesSection} from './TemplatesSection'
import {cn} from '@/lib/utils'
const STORAGE_KEY='brand-studio-library-collapsed'
const SUBSECTION_KEY='brand-studio-library-subsection'
type LibSubSection='products'|'templates'|null
interface LibrarySectionProps{onCreateProduct:()=>void;onCreateTemplate:()=>void;createTemplateOpen?:boolean;onCreateTemplateChange?:(open:boolean)=>void}
//Load from localStorage with error handling for Safari private mode
function loadLibraryState():{collapsed:boolean;subSection:LibSubSection}{
try{const collapsed=localStorage.getItem(STORAGE_KEY)==='true'
const subSection=localStorage.getItem(SUBSECTION_KEY) as LibSubSection
return {collapsed,subSection:subSection==='products'||subSection==='templates'?subSection:null}}
catch{return {collapsed:true,subSection:null}}}
function saveLibraryState(collapsed:boolean,subSection:LibSubSection){
try{localStorage.setItem(STORAGE_KEY,String(collapsed))
if(subSection)localStorage.setItem(SUBSECTION_KEY,subSection)
else localStorage.removeItem(SUBSECTION_KEY)}catch{/*Ignore in private mode*/}}
export function LibrarySection({onCreateProduct,onCreateTemplate,createTemplateOpen,onCreateTemplateChange}:LibrarySectionProps){
const {activeBrand}=useBrand()
const {products}=useProducts()
const {templates}=useTemplates()
const [isOpen,setIsOpen]=useState(()=>!loadLibraryState().collapsed)
const [subSection,setSubSection]=useState<LibSubSection>(()=>loadLibraryState().subSection)
//Persist state changes
useEffect(()=>{saveLibraryState(!isOpen,subSection)},[isOpen,subSection])
const toggleOpen=()=>{setIsOpen(prev=>!prev)}
const toggleSubSection=(section:LibSubSection)=>{setSubSection(prev=>prev===section?null:section)}
return(
<div className="mb-2">
{/*Library header*/}
<div className="flex items-center gap-1 group mb-1 px-2">
<button onClick={toggleOpen} className={cn("flex-1 flex items-center gap-3 px-2 py-1.5 rounded-lg text-sm font-medium transition-all duration-200",isOpen?"text-foreground bg-secondary/50":"text-muted-foreground/80 hover:text-foreground hover:bg-secondary/30")}>
<div className={cn("transition-colors",isOpen?"text-foreground":"text-muted-foreground")}>
<Library className="w-4 h-4"/></div>
<span className="flex-1 text-left">Library</span>
<ChevronRight className={cn("w-3.5 h-3.5 transition-transform duration-200 opacity-0 group-hover:opacity-50",isOpen&&"rotate-90 opacity-100")}/></button>
</div>
{/*Library content*/}
<div className={cn("grid transition-all duration-200 ease-in-out pl-2",isOpen?"grid-rows-[1fr] opacity-100 mb-4":"grid-rows-[0fr] opacity-0")}>
<div className="overflow-hidden pb-1">
<div className="space-y-1 pl-2">
{/*Products subsection*/}
<SubNavGroup title="Products" icon={<Package className="w-3.5 h-3.5"/>} count={products.length} isOpen={subSection==='products'} onToggle={()=>toggleSubSection('products')} onAdd={onCreateProduct} disabled={!activeBrand}>
<ProductsSection/></SubNavGroup>
{/*Templates subsection*/}
<SubNavGroup title="Templates" icon={<Palette className="w-3.5 h-3.5"/>} count={templates.length} isOpen={subSection==='templates'} onToggle={()=>toggleSubSection('templates')} onAdd={onCreateTemplate} disabled={!activeBrand}>
<TemplatesSection createDialogOpen={createTemplateOpen} onCreateDialogChange={onCreateTemplateChange}/></SubNavGroup>
</div>
</div>
</div>
</div>)}
//Nested nav group for subsections
interface SubNavGroupProps{title:string;icon:React.ReactNode;count:number;isOpen:boolean;onToggle:()=>void;onAdd:()=>void;disabled?:boolean;children:React.ReactNode}
function SubNavGroup({title,icon,count,isOpen,onToggle,onAdd,disabled,children}:SubNavGroupProps){
return(
<div className="mb-1">
<div className="flex items-center gap-1 group">
<button onClick={onToggle} disabled={disabled} className={cn("flex-1 flex items-center gap-2 px-2 py-1 rounded-md text-xs font-medium transition-all duration-200",isOpen?"text-foreground bg-secondary/40":"text-muted-foreground/70 hover:text-foreground hover:bg-secondary/20",disabled&&"opacity-50 pointer-events-none")}>
{isOpen?<ChevronDown className="w-3 h-3 shrink-0"/>:<ChevronRight className="w-3 h-3 shrink-0"/>}
<div className={cn("transition-colors",isOpen?"text-foreground":"text-muted-foreground")}>{icon}</div>
<span className="flex-1 text-left">{title}</span>
<span className="text-[10px] text-muted-foreground/60">{count}</span></button>
<Button variant="ghost" size="icon" className="h-6 w-6 rounded-md opacity-0 group-hover:opacity-100 transition-opacity hover:bg-secondary" onClick={(e)=>{e.stopPropagation();onAdd()}} disabled={disabled}>
<Plus className="w-3 h-3 text-muted-foreground"/></Button>
</div>
<div className={cn("grid transition-all duration-200 ease-in-out",isOpen?"grid-rows-[1fr] opacity-100":"grid-rows-[0fr] opacity-0")}>
<div className="overflow-hidden">{children}</div>
</div>
</div>)}
