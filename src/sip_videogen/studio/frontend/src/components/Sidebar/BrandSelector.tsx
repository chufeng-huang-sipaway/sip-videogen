import { Button } from '@/components/ui/button'
import { ChevronDown } from 'lucide-react'

export function BrandSelector() {
  return (
    <Button variant="outline" className="w-full justify-between">
      <span>Select Brand...</span>
      <ChevronDown className="h-4 w-4" />
    </Button>
  )
}
