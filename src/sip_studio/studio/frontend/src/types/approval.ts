//Approval types matching backend job_state.py models (camelCase from serialization_alias)
export type ApprovalAction='approve'|'reject'|'edit'|'approve_all'|'auto_approved'
export interface ApprovalRequest{
id:string
runId:string
toolName:string
prompt:string
previewUrl:string|null
createdAt:string
expiresAt:string|null}
export interface ApprovalResult{
action:ApprovalAction
modifiedPrompt:string|null}
//Event payloads (from state.py _push_event calls)
export interface ApprovalRequestEvent extends ApprovalRequest{}
export interface ApprovalClearedEvent{
runId:string
requestId:string}
export interface AutonomyChangedEvent{enabled:boolean}
