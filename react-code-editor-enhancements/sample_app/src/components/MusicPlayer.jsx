import { useState } from 'react'
import { Play, Pause, SkipForward, SkipBack, Volume2 } from 'lucide-react'

function MusicPlayer({ playlist }) {
  const [currentTrack, setCurrentTrack] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [volume, setVolume] = useState(70)

  const handlePlay = () => {
    setIsPlaying(true)
  }

  const handlePause = () => {
    setIsPlaying(false)
  }

  const handleNext = () => {
    setCurrentTrack((prev) => (prev + 1) % playlist.length)
  }

  const handlePrevious = () => {
    setCurrentTrack((prev) => (prev - 1 + playlist.length) % playlist.length)
  }

  const track = playlist[currentTrack]

  return (
    <div className="bg-white/10 backdrop-blur-lg rounded-3xl p-8 shadow-2xl">
      {/* Album Art */}
      <div className="mb-8">
        <div className="aspect-square bg-gradient-to-br from-pink-500 to-purple-600 rounded-2xl flex items-center justify-center">
          <div className="text-white text-8xl">🎵</div>
        </div>
      </div>

      {/* Track Info */}
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-white mb-2">{track.title}</h2>
        <p className="text-gray-300 text-lg">{track.artist}</p>
        <p className="text-gray-400 mt-1">{track.duration}</p>
      </div>

      {/* Progress Bar */}
      <div className="mb-8">
        <div className="w-full bg-gray-700 rounded-full h-2">
          <div className="bg-blue-500 h-2 rounded-full" style={{ width: '45%' }}></div>
        </div>
        <div className="flex justify-between text-gray-400 text-sm mt-2">
          <span>1:42</span>
          <span>{track.duration}</span>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-center gap-6 mb-8">
        <button
          onClick={handlePrevious}
          className="p-3 rounded-full bg-white/20 hover:bg-white/30 transition"
        >
          <SkipBack className="w-6 h-6 text-white" />
        </button>

        {!isPlaying ? (
          <button
            onClick={handlePlay}
            className="p-5 rounded-full bg-blue-500 hover:bg-blue-600 transition shadow-lg"
          >
            <Play className="w-8 h-8 text-white" />
          </button>
        ) : (
          <button
            onClick={handlePause}
            className="p-5 rounded-full bg-blue-500 hover:bg-blue-600 transition shadow-lg"
          >
            <Pause className="w-8 h-8 text-white" />
          </button>
        )}

        <button
          onClick={handleNext}
          className="p-3 rounded-full bg-white/20 hover:bg-white/30 transition"
        >
          <SkipForward className="w-6 h-6 text-white" />
        </button>
      </div>

      {/* Volume Control */}
      <div className="flex items-center gap-4">
        <Volume2 className="w-5 h-5 text-gray-300" />
        <input
          type="range"
          min="0"
          max="100"
          value={volume}
          onChange={(e) => setVolume(e.target.value)}
          className="flex-1 h-2 bg-gray-700 rounded-full appearance-none cursor-pointer"
        />
        <span className="text-gray-300 text-sm w-12">{volume}%</span>
      </div>

      {/* Playlist */}
      <div className="mt-8 pt-8 border-t border-white/10">
        <h3 className="text-white text-xl font-semibold mb-4">Playlist</h3>
        <div className="space-y-2">
          {playlist.map((item, index) => (
            <button
              key={item.id}
              onClick={() => setCurrentTrack(index)}
              className={`w-full text-left p-3 rounded-lg transition ${
                index === currentTrack
                  ? 'bg-blue-500/30 text-white'
                  : 'text-gray-300 hover:bg-white/10'
              }`}
            >
              <div className="flex justify-between items-center">
                <div>
                  <p className="font-medium">{item.title}</p>
                  <p className="text-sm opacity-75">{item.artist}</p>
                </div>
                <span className="text-sm">{item.duration}</span>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

export default MusicPlayer
