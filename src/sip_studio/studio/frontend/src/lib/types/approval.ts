//Approval request data from backend
export interface ApprovalRequestData {
  id:string
  actionType:string
  description:string
  prompt?:string
  details?:Record<string,unknown>
}
