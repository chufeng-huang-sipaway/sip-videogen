//PromptDiff component - shows what was ADDED to the original prompt in diff-style
interface Props {originalPrompt:string;finalPrompt:string}
function tr(s:string,max:number):string{return s.length>max?s.slice(0,max)+'...':s}
export function PromptDiff({originalPrompt,finalPrompt}:Props){
const oT=(originalPrompt||'').trim(),fT=(finalPrompt||'').trim()
//Edge case: both empty/whitespace
if(!oT&&!fT)return null
//Edge case: no final prompt
if(!fT)return <div className="text-xs text-muted-foreground">No prompt generated</div>
//Edge case: no original prompt (treat whitespace-only as missing)
if(!oT)return <div className="text-xs"><span className="text-success">+ {tr(fT,400)}</span></div>
//Edge case: identical prompts (no additions)
if(oT===fT)return(<div className="text-xs"><div className="text-muted-foreground">No modifications made to prompt</div><div className="mt-1">{tr(oT,200)}</div></div>)
//Check if original is contained in final (common case)
if(fT.startsWith(oT)){const adds=fT.slice(oT.length).trim()
return(<div className="text-xs space-y-2"><div><span className="text-muted-foreground">Original:</span><span className="ml-2">{tr(oT,200)}</span></div>{adds&&(<div className="text-success whitespace-pre-wrap"><span className="font-medium">+ Added:</span><div className="pl-4">{tr(adds,500)}</div></div>)}</div>)}
//Prompts don't overlap (rewritten case) - show both
return(<div className="text-xs space-y-2"><div><span className="text-muted-foreground">Original:</span><div className="pl-4">{tr(oT,200)}</div></div><div><span className="text-muted-foreground">Final (rewritten):</span><div className="pl-4">{tr(fT,300)}</div></div></div>)}
