import { useState } from 'react';
    import CollapsibleSection from './components/CollapsibleSection';
    import MusicPlayer from './components/MusicPlayer';
    import LiveChat from './components/LiveChat';
    import DataDashboard from './components/DataDashboard';
    import './App.css';

    function App() {
      const [musicPlayerOpen, setMusicPlayerOpen] = useState(true);
      const [liveChatOpen, setLiveChatOpen] = useState(true);
      const [dashboardOpen, setDashboardOpen] = useState(true);

      return (
        <div className="bg-gray-900 min-h-screen text-white font-sans p-4">
          <div className="container mx-auto">
            <header className="text-center mb-8">
              <h1 className="text-4xl font-bold text-green-400">My Interactive Dashboard</h1>
              <p className="text-gray-400">Collapsible sections for a dynamic experience</p>
            </header>

            <div className="flex flex-col lg:flex-row gap-4">
              {/* Main content area */}
              <main className="flex-grow lg:w-3/4">
                <CollapsibleSection
                  title="Data Dashboard"
                  isOpen={dashboardOpen}
                  onToggle={() => setDashboardOpen(!dashboardOpen)}
                >
                  <DataDashboard />
                </CollapsibleSection>

                <CollapsibleSection
                  title="Music Player"
                  isOpen={musicPlayerOpen}
                  onToggle={() => setMusicPlayerOpen(!musicPlayerOpen)}
                >
                  <MusicPlayer />
                </CollapsibleSection>
              </main>

              {/* Sidebar */}
              <aside className="lg:w-1/4">
                <CollapsibleSection
                  title="Live Chat"
                  isOpen={liveChatOpen}
                  onToggle={() => setLiveChatOpen(!liveChatOpen)}
                >
                  <LiveChat />
                </CollapsibleSection>
              </aside>
            </div>
          </div>
        </div>
      );
    }

    export default App;
