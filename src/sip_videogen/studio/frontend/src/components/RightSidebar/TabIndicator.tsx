import{cn}from'@/lib/utils'

interface TabIndicatorProps{
isGenerating:boolean
newCount:number
}

export function TabIndicator({isGenerating,newCount}:TabIndicatorProps){
//Nothing to show
if(!isGenerating&&newCount<=0)return null
//Generating: pulsing dot
if(isGenerating){
return(
<span className="relative flex h-2 w-2">
<span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"/>
<span className="relative inline-flex rounded-full h-2 w-2 bg-primary"/>
</span>
)
}
//New inspirations: solid dot with count badge
return(
<span className={cn("inline-flex items-center justify-center min-w-[16px] h-4 px-1 text-[10px] font-semibold rounded-full bg-primary text-primary-foreground")}>
{newCount>9?'9+':newCount}
</span>
)
}
