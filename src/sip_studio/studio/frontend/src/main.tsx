import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import {BrandProvider} from '@/context/BrandContext'
import {ProductProvider} from '@/context/ProductContext'
import {ProjectProvider} from '@/context/ProjectContext'
import {StyleReferenceProvider} from '@/context/StyleReferenceContext'
import {WorkstationProvider} from '@/context/WorkstationContext'
import './index.css'
ReactDOM.createRoot(document.getElementById('root')!).render(
<React.StrictMode>
<BrandProvider>
<ProjectProvider>
<ProductProvider>
<StyleReferenceProvider>
<WorkstationProvider>
<App/>
</WorkstationProvider>
</StyleReferenceProvider>
</ProductProvider>
</ProjectProvider>
</BrandProvider>
</React.StrictMode>,)
