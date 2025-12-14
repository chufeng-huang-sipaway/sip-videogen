import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'

function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 flex flex-col items-center justify-center p-8">
      <div className="flex gap-8 mb-8">
        <a href="https://vite.dev" target="_blank" className="hover:opacity-75 transition-opacity">
          <img src={viteLogo} className="h-24 w-24" alt="Vite logo" />
        </a>
        <a href="https://react.dev" target="_blank" className="hover:opacity-75 transition-opacity">
          <img src={reactLogo} className="h-24 w-24 animate-spin" style={{ animationDuration: '20s' }} alt="React logo" />
        </a>
      </div>
      <h1 className="text-4xl font-bold mb-8">Brand Studio</h1>
      <div className="glass bg-sidebar-light dark:bg-sidebar-dark p-8 rounded-2xl shadow-lg">
        <button
          onClick={() => setCount((count) => count + 1)}
          className="bg-purple-600 hover:bg-purple-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
        >
          count is {count}
        </button>
        <p className="mt-4 text-gray-600 dark:text-gray-400">
          Tailwind CSS is working!
        </p>
      </div>
    </div>
  )
}

export default App
