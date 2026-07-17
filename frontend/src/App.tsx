import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from '@/context/AuthContext'
import ProtectedRoute from '@/components/ProtectedRoute'
import LoginPage from '@/pages/LoginPage'
import SignUpPage from '@/pages/SignUpPage'
import ChatLayout from '@/pages/chat/ChatLayout'
import ThreadPage from '@/pages/chat/ThreadPage'
import ChatLanding from '@/pages/chat/ChatLanding'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignUpPage />} />

          {/* Protected — unauthenticated users are sent to /login */}
          <Route element={<ProtectedRoute />}>
            <Route path="/chat" element={<ChatLayout />}>
              <Route index element={<ChatLanding />} />
              <Route path=":threadId" element={<ThreadPage />} />
            </Route>
          </Route>

          {/* Default */}
          <Route path="*" element={<Navigate to="/chat" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
