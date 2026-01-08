//QuickGeneratorOverlay - combines FAB and Panel at app level
import{useQuickGeneratorContext}from'@/context/QuickGeneratorContext'
import{useActiveJob}from'@/hooks/useActiveJob'
import{QuickGeneratorFAB}from'./QuickGeneratorFAB'
import{QuickGeneratorPanel}from'./QuickGeneratorPanel'
interface QuickGeneratorOverlayProps{
disabled?:boolean}
export function QuickGeneratorOverlay({disabled}:QuickGeneratorOverlayProps){
const generator=useQuickGeneratorContext()
const{isGenerating:jobActive}=useActiveJob()
//FAB is disabled when any job is active (per A8 in implementation plan)
const fabDisabled=disabled||jobActive||generator.status==='running'
return(<>
<QuickGeneratorFAB onClick={generator.open} disabled={fabDisabled}/>
<QuickGeneratorPanel generator={generator} onSendToChat={generator.sendToChat} disabled={disabled}/>
</>)}
