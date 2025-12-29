//Tab types for IDE-like tabbed interface
export type TabType='project'|'product'|'template'
export interface Tab{id:string;type:TabType;slug:string;title:string;isDirty:boolean}
//Create unique tab ID: brand|type|slug (using | since slugs can't contain it)
export function makeTabId(brand:string,type:TabType,slug:string):string{return`${brand}|${type}|${slug}`}
//Parse tab ID back to components
export function parseTabId(id:string):{brand:string;type:TabType;slug:string}|null{const parts=id.split('|');if(parts.length!==3)return null;return{brand:parts[0],type:parts[1]as TabType,slug:parts[2]}}
