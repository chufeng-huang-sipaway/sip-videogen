import {cn} from "@/lib/utils"
//Skeleton component with pulse animation that respects prefers-reduced-motion
function Skeleton({className,...props}:React.HTMLAttributes<HTMLDivElement>){return <div className={cn("animate-pulse rounded-md bg-primary/10",className)} {...props}/>}
export {Skeleton}
