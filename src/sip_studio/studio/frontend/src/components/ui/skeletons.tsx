//Compound skeleton components for loading states - uses animate-pulse which respects prefers-reduced-motion
import{Skeleton}from'./skeleton'
import{cn}from'@/lib/utils'
//BrandCardSkeleton - for brand list items and cards
export function BrandCardSkeleton({className}:{className?:string}){return(<div className={cn("p-3 rounded-lg border border-border/60 bg-card/50",className)}><div className="flex items-center gap-2 mb-2"><Skeleton className="h-4 w-4 rounded"/><Skeleton className="h-4 flex-1"/></div><Skeleton className="h-3 w-24 mb-2"/><div className="flex gap-1">{[...Array(5)].map((_,i)=>(<Skeleton key={i} className="w-4 h-4 rounded-full"/>))}</div></div>)}
//ImageGridSkeleton - for asset grids with configurable count
export function ImageGridSkeleton({count=6,className}:{count?:number;className?:string}){return(<div className={cn("grid grid-cols-[repeat(auto-fill,minmax(120px,1fr))] gap-3",className)}>{Array.from({length:count}).map((_,i)=>(<Skeleton key={i} className="aspect-square rounded-lg"/>))}</div>)}
//AssetThumbnailSkeleton - individual thumbnail placeholder
export function AssetThumbnailSkeleton({className}:{className?:string}){return(<Skeleton className={cn("aspect-square rounded-md",className)}/>)}
//MessageSkeleton - for chat message loading placeholder
export function MessageSkeleton({isUser=false,className}:{isUser?:boolean;className?:string}){return(<div className={cn("flex w-full px-2 py-2",isUser?"justify-end":"justify-start",className)}><div className={cn("flex flex-col gap-2",isUser?"items-end max-w-[80%]":"items-start w-full")}><Skeleton className={cn("h-4 rounded",isUser?"w-32":"w-48")}/><Skeleton className={cn("h-4 rounded",isUser?"w-24":"w-64")}/>{!isUser&&<Skeleton className="h-4 w-40 rounded"/>}</div></div>)}
//ProjectCardSkeleton - for project list items
export function ProjectCardSkeleton({className}:{className?:string}){return(<div className={cn("flex items-center gap-2.5 py-2 px-2.5 rounded-lg",className)}><Skeleton className="h-4 w-4 rounded"/><div className="flex-1 min-w-0"><Skeleton className="h-4 w-24 mb-1"/><Skeleton className="h-3 w-16"/></div></div>)}
