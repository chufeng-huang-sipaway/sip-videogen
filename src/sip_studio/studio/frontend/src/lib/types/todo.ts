//Todo item data from backend
export interface TodoItemData {
  id:string
  description:string
  status:'pending'|'in_progress'|'done'|'error'|'paused'
  outputs?:Array<{path?:string;data?:string;type:string}>
  error?:string
}
//Todo list data from backend
export interface TodoListData {
  id:string
  title:string
  items:TodoItemData[]
  createdAt:string
  completedAt?:string
  interruptedAt?:string
  interruptReason?:string
}
//Todo update event data
export interface TodoUpdateData {
  itemId:string
  status:string
  outputs?:Array<{path?:string;data?:string;type:string}>
  error?:string
}
