import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Route, BrowserRouter as Router, Routes } from 'react-router-dom'
import { App } from './App.jsx'
import './index.css'
import { HouseInfo } from './pages/house-info.jsx'

createRoot(document.getElementById('root')).render(
	<StrictMode>
		<Router>
			<Routes>
				<Route path='/' element={<App />} />
				<Route path='/house-info' element={<HouseInfo />} />
			</Routes>
		</Router>
	</StrictMode>
)
