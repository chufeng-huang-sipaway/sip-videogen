import { useCallback, useEffect, useRef } from 'react'

interface ResizeHandleProps {
  onResize: (delta: number) => void
  onResizeEnd?: () => void
}

export function ResizeHandle({ onResize, onResizeEnd }: ResizeHandleProps) {
  const isDragging = useRef(false)
  const startX = useRef(0)

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    isDragging.current = true
    startX.current = e.clientX
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }, [])

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging.current) return
      const delta = e.clientX - startX.current
      startX.current = e.clientX
      onResize(delta)
    }

    const handleMouseUp = () => {
      if (isDragging.current) {
        isDragging.current = false
        document.body.style.cursor = ''
        document.body.style.userSelect = ''
        onResizeEnd?.()
      }
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [onResize, onResizeEnd])

  return (
    <div
      onMouseDown={handleMouseDown}
      className="w-1 hover:w-1.5 bg-transparent hover:bg-brand-500/50 cursor-col-resize transition-all duration-150 flex-shrink-0 group"
      title="Drag to resize"
    >
      <div className="w-full h-full group-hover:bg-brand-500/30" />
    </div>
  )
}
