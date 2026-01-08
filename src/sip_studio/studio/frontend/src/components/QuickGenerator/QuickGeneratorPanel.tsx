//QuickGeneratorPanel - main container for quick generator dialog
import{useCallback}from'react'
import{X}from'lucide-react'
import{Dialog,DialogContent,DialogHeader,DialogTitle}from'@/components/ui/dialog'
import{Button}from'@/components/ui/button'
import{Progress}from'@/components/ui/progress'
import{GeneratorForm,type Product,type StyleReference}from'./GeneratorForm'
import{ResultsGrid}from'./ResultsGrid'
import type{UseQuickGeneratorResult}from'@/hooks/useQuickGenerator'
interface QuickGeneratorPanelProps{
generator:UseQuickGeneratorResult
onSendToChat:(paths:string[])=>void
disabled?:boolean
products?:Array<{slug:string;name:string}>
styleReferences?:Array<{slug:string;name:string}>}
export function QuickGeneratorPanel({generator,onSendToChat,disabled,products=[],styleReferences=[]}:QuickGeneratorPanelProps){
const{status,progress,generatedImages,errors,isOpen,close,generate,cancel,clear,downloadAll}=generator
const isGenerating=status==='running'
const progressPercent=progress?(progress.completed/progress.total)*100:0
//Wrap generate to pass product/style ref from form
const handleGenerate=useCallback(async(prompts:string[],aspectRatio:string,productSlug?:string,styleRefSlug?:string)=>{
await generate(prompts,aspectRatio,productSlug,styleRefSlug)
},[generate])
return(<Dialog open={isOpen} onOpenChange={(open)=>{if(!open)close()}}>
<DialogContent className="sm:max-w-md">
<DialogHeader>
<DialogTitle className="flex items-center justify-between">
<span>Quick Generate</span>
<Button variant="ghost" size="icon" onClick={close} className="h-8 w-8">
<X className="h-4 w-4"/>
</Button>
</DialogTitle>
</DialogHeader>
<div className="py-2">
<GeneratorForm onGenerate={handleGenerate} onCancel={cancel} isGenerating={isGenerating} disabled={disabled} products={products as Product[]} styleReferences={styleReferences as StyleReference[]}/>
{isGenerating&&progress&&(<div className="mt-4 space-y-2">
<div className="flex items-center justify-between text-xs text-muted-foreground">
<span>Generating {progress.completed+1} of {progress.total}...</span>
<span>{Math.round(progressPercent)}%</span>
</div>
<Progress value={progressPercent} className="h-1.5"/>
{progress.currentPrompt&&(<p className="text-xs text-muted-foreground/70 truncate">"{progress.currentPrompt}"</p>)}
</div>)}
<ResultsGrid images={generatedImages} errors={errors} onDownloadAll={downloadAll} onSendToChat={onSendToChat} isGenerating={isGenerating}/>
{generatedImages.length>0&&!isGenerating&&(<div className="mt-3 pt-3 border-t">
<Button variant="ghost" size="sm" onClick={clear} className="w-full text-muted-foreground">
Clear Results
</Button>
</div>)}
</div>
</DialogContent>
</Dialog>)}
