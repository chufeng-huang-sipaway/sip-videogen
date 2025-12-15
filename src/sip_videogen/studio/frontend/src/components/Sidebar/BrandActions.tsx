import { useCallback, useRef, useState } from 'react'
import { Upload, Brain, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useBrand } from '@/context/BrandContext'
import { bridge, isPyWebView } from '@/lib/bridge'

const ALLOWED_DOC_EXTS = ['.md', '.txt', '.json', '.yaml', '.yml']
const ALLOWED_IMAGE_EXTS = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg']
const ALL_ALLOWED_EXTS = [...ALLOWED_DOC_EXTS, ...ALLOWED_IMAGE_EXTS]

export function BrandActions() {
  const { activeBrand } = useBrand()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [refreshSuccess, setRefreshSuccess] = useState(false)

  const handleUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !isPyWebView() || !activeBrand) return

    setIsUploading(true)
    try {
      for (const file of Array.from(e.target.files)) {
        const ext = file.name.toLowerCase().slice(file.name.lastIndexOf('.'))
        const isImage = ALLOWED_IMAGE_EXTS.includes(ext)
        const isDoc = ALLOWED_DOC_EXTS.includes(ext)

        if (!isImage && !isDoc) continue

        const reader = new FileReader()
        await new Promise<void>((resolve, reject) => {
          reader.onload = async () => {
            try {
              const base64 = (reader.result as string).split(',')[1]
              if (isImage) {
                await bridge.uploadAsset(file.name, base64, 'marketing')
              } else {
                await bridge.uploadDocument(file.name, base64)
              }
              resolve()
            } catch (err) {
              reject(err)
            }
          }
          reader.onerror = () => reject(reader.error)
          reader.readAsDataURL(file)
        })
      }
    } finally {
      setIsUploading(false)
      e.target.value = ''
    }
  }, [activeBrand])

  const handleRefreshMemory = useCallback(async () => {
    if (!isPyWebView()) return

    setIsRefreshing(true)
    setRefreshSuccess(false)
    try {
      await bridge.refreshBrandMemory()
      setRefreshSuccess(true)
      setTimeout(() => setRefreshSuccess(false), 2000)
    } finally {
      setIsRefreshing(false)
    }
  }, [])

  if (!activeBrand) return null

  return (
    <div className="px-4 py-2 space-y-2">
      <Button
        variant="outline"
        size="sm"
        className="w-full justify-start gap-2"
        onClick={() => fileInputRef.current?.click()}
        disabled={isUploading}
      >
        <Upload className={`h-4 w-4 ${isUploading ? 'animate-pulse' : ''}`} />
        {isUploading ? 'Uploading...' : 'Upload Files'}
      </Button>
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        multiple
        accept={ALL_ALLOWED_EXTS.join(',')}
        onChange={handleUpload}
      />

      <Button
        variant="outline"
        size="sm"
        className="w-full justify-start gap-2"
        onClick={handleRefreshMemory}
        disabled={isRefreshing}
      >
        {refreshSuccess ? (
          <Check className="h-4 w-4 text-green-500" />
        ) : (
          <Brain className={`h-4 w-4 ${isRefreshing ? 'animate-pulse' : ''}`} />
        )}
        {isRefreshing ? 'Refreshing...' : refreshSuccess ? 'Memory Updated!' : 'Refresh AI Memory'}
      </Button>
    </div>
  )
}
