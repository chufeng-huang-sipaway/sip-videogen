import * as React from "react"
import * as ScrollAreaPrimitive from "@radix-ui/react-scroll-area"
import {cn} from "@/lib/utils"
//ScrollArea with macOS Monterey+ auto-hide scrollbar behavior
const ScrollArea = React.forwardRef<React.ComponentRef<typeof ScrollAreaPrimitive.Root>,React.ComponentPropsWithoutRef<typeof ScrollAreaPrimitive.Root>>(({className,children,...props},ref)=>(<ScrollAreaPrimitive.Root ref={ref} className={cn("relative overflow-hidden group/scroll",className)} {...props}><ScrollAreaPrimitive.Viewport className="h-full w-full rounded-[inherit]">{children}</ScrollAreaPrimitive.Viewport><ScrollBar/><ScrollAreaPrimitive.Corner/></ScrollAreaPrimitive.Root>))
ScrollArea.displayName = ScrollAreaPrimitive.Root.displayName
//ScrollBar - hidden by default, visible on hover/scroll (macOS native behavior)
const ScrollBar = React.forwardRef<React.ComponentRef<typeof ScrollAreaPrimitive.ScrollAreaScrollbar>,React.ComponentPropsWithoutRef<typeof ScrollAreaPrimitive.ScrollAreaScrollbar>>(({className,orientation="vertical",...props},ref)=>(<ScrollAreaPrimitive.ScrollAreaScrollbar ref={ref} orientation={orientation} className={cn("flex touch-none select-none transition-opacity duration-300 opacity-0 group-hover/scroll:opacity-100 data-[state=visible]:opacity-100",orientation==="vertical"&&"h-full w-1.5 border-l border-l-transparent p-[1px]",orientation==="horizontal"&&"h-1.5 flex-col border-t border-t-transparent p-[1px]",className)} {...props}><ScrollAreaPrimitive.ScrollAreaThumb className="relative flex-1 rounded-full bg-black/20 dark:bg-white/20 transition-colors hover:bg-black/30 dark:hover:bg-white/30"/></ScrollAreaPrimitive.ScrollAreaScrollbar>))
ScrollBar.displayName = ScrollAreaPrimitive.ScrollAreaScrollbar.displayName
export {ScrollArea,ScrollBar}
