import { Sidebar } from '@/components/Sidebar'
import { ChatPanel } from '@/components/ChatPanel'

function App() {
  return (
    <div className="flex h-screen bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      <Sidebar />
      <ChatPanel />
    </div>
  )
}

export default App
