import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import {BrandProvider} from '@/context/BrandContext'
import {ProductProvider} from '@/context/ProductContext'
import {ProjectProvider} from '@/context/ProjectContext'
import {TemplateProvider} from '@/context/TemplateContext'
import './index.css'
ReactDOM.createRoot(document.getElementById('root')!).render(
<React.StrictMode>
<BrandProvider>
<ProjectProvider>
<ProductProvider>
<TemplateProvider>
<App/>
</TemplateProvider>
</ProductProvider>
</ProjectProvider>
</BrandProvider>
</React.StrictMode>,)
