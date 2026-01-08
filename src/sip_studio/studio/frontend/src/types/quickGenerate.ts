//Quick generate types matching backend quick_generate_job.py models
export interface QuickGenerateProgress{
total:number
completed:number
currentPrompt:string
generatedPaths:string[]
errors:string[]
runId:string}
export interface QuickGenerateResult{
runId:string
generatedPaths:string[]
errors:string[]
total:number
completed:number
cancelled:boolean
interruptType?:'pause'|'stop'|'new_direction'
error?:string}
export interface QuickGenerateErrorEvent{
runId:string
error:string}
//Job status helpers
export type QuickGenerateStatus='idle'|'running'|'completed'|'cancelled'|'error'
export function getQuickGenerateStatus(progress:QuickGenerateProgress|null,result:QuickGenerateResult|null):QuickGenerateStatus{
if(result){
if(result.error)return'error'
if(result.cancelled)return'cancelled'
return'completed'}
if(progress&&progress.total>0)return'running'
return'idle'}
