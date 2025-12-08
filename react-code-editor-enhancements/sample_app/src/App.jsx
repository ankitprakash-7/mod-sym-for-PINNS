import { useState } from 'react'
import MusicPlayer from './components/MusicPlayer'

function App() {
  const [playlist] = useState([
    { id: 1, title: 'Summer Vibes', artist: 'The Chill Band', duration: '3:45' },
    { id: 2, title: 'Midnight Dreams', artist: 'Jazz Collective', duration: '4:20' },
    { id: 3, title: 'Electric Pulse', artist: 'DJ Groove', duration: '5:12' },
  ])

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900">
      <div className="container mx-auto px-4 py-12">
        <header className="text-center mb-12">
          <h1 className="text-5xl font-bold text-white mb-4">
            🎵 Music Player
          </h1>
          <p className="text-gray-300 text-lg">
            Your personal music companion
          </p>
        </header>

        <div className="max-w-4xl mx-auto">
          <MusicPlayer playlist={playlist} />
        </div>

        <footer className="text-center mt-16 text-gray-400">
          <p>Built with React + Vite + Tailwind</p>
        </footer>
      </div>
    </div>
  )
}

export default App
