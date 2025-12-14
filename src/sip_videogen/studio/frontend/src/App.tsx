import { Sidebar } from '@/components/Sidebar'
import { ChatPanel } from '@/components/ChatPanel'
import { useBrand } from '@/context/BrandContext'

function App() {
  const { activeBrand } = useBrand()

  return (
    <div className="flex h-screen bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      <Sidebar />
      <ChatPanel brandSlug={activeBrand} />
    </div>
  )
}

export default App
