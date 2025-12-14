import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ChevronDown, CheckCircle } from 'lucide-react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'

function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col items-center justify-center p-8">
      <div className="flex gap-8 mb-8">
        <a href="https://vite.dev" target="_blank" className="hover:opacity-75 transition-opacity">
          <img src={viteLogo} className="h-24 w-24" alt="Vite logo" />
        </a>
        <a href="https://react.dev" target="_blank" className="hover:opacity-75 transition-opacity">
          <img src={reactLogo} className="h-24 w-24 animate-spin" style={{ animationDuration: '20s' }} alt="React logo" />
        </a>
      </div>
      <h1 className="text-4xl font-bold mb-8">Brand Studio</h1>
      <div className="glass bg-sidebar-light dark:bg-sidebar-dark p-8 rounded-2xl shadow-lg space-y-6 max-w-md w-full">
        <Alert>
          <CheckCircle className="h-4 w-4" />
          <AlertDescription>
            shadcn/ui components are working!
          </AlertDescription>
        </Alert>

        <div className="flex gap-2">
          <Button onClick={() => setCount((count) => count + 1)}>
            Count: {count}
          </Button>
          <Button variant="outline">Outline</Button>
          <Button variant="secondary">Secondary</Button>
        </div>

        <Separator />

        <div className="space-y-2">
          <label className="text-sm font-medium">Sample Input</label>
          <Input placeholder="Type something..." />
        </div>

        <Separator />

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" className="w-full justify-between">
              Select an option
              <ChevronDown className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56">
            <DropdownMenuItem>Option 1</DropdownMenuItem>
            <DropdownMenuItem>Option 2</DropdownMenuItem>
            <DropdownMenuItem>Option 3</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <p className="text-sm text-muted-foreground text-center">
          Tailwind CSS + shadcn/ui configured
        </p>
      </div>
    </div>
  )
}

export default App
