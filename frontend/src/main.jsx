import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import axios from 'axios'
import './index.css'
import App from './App.jsx'

// 빌드(운영) 환경일 경우 백엔드 주소를 Render 서버로 고정
if (import.meta.env.PROD) {
  axios.defaults.baseURL = 'https://instr-cxzs.onrender.com';
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
