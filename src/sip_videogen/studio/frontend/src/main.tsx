import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { BrandProvider } from '@/context/BrandContext'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrandProvider>
      <App />
    </BrandProvider>
  </React.StrictMode>,
)
