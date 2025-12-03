import { Play, Pause, SkipBack, SkipForward } from 'lucide-react';

    const MusicPlayer = () => {
      return (
        <div className="text-white flex flex-col items-center">
          <img
            src="/images/image_42.jpg"
            alt="Album Art"
            className="w-48 h-48 rounded-lg shadow-lg mb-4 object-cover"
          />
          <div className="text-center mb-4">
            <p className="font-bold text-xl">Midnight City</p>
            <p className="text-gray-400">M83</p>
          </div>
          <div className="w-full max-w-xs mb-4">
            <div className="h-1 bg-gray-600 rounded-full">
              <div className="h-1 bg-green-500 rounded-full w-3/4"></div>
            </div>
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>2:45</span>
              <span>4:03</span>
            </div>
          </div>
          <div className="flex items-center space-x-6">
            <button className="text-gray-400 hover:text-white transition-colors">
              <SkipBack size={28} />
            </button>
            <button className="bg-green-500 text-black rounded-full p-3 hover:bg-green-400 transition-colors shadow-lg">
              <Play size={32} />
            </button>
            <button className="text-gray-400 hover:text-white transition-colors">
              <SkipForward size={28} />
            </button>
          </div>
        </div>
      );
    };

    export default MusicPlayer;
