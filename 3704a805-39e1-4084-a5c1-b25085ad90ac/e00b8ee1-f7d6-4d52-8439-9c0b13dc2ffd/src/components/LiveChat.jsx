const LiveChat = () => {
      const messages = [
        { user: 'Alice', text: 'Hey everyone! Excited for the stream.' },
        { user: 'Bob', text: 'Me too! This is going to be great.' },
        { user: 'Charlie', text: 'What a dashboard! 🤩' },
        { user: 'Dave', text: 'The music player is a nice touch.' },
      ];

      return (
        <div className="text-white flex flex-col h-[500px]">
          <div className="flex-grow overflow-y-auto pr-2 space-y-4">
            {messages.map((msg, index) => (
              <div key={index} className="flex flex-col">
                <span className="font-semibold text-sm text-green-400">{msg.user}</span>
                <p className="text-gray-300 bg-gray-700/80 p-2 rounded-lg backdrop-blur-sm">{msg.text}</p>
              </div>
            ))}
          </div>
          <div className="mt-4 flex">
            <input
              type="text"
              placeholder="Send a message..."
              className="flex-grow bg-gray-900 border border-gray-600 rounded-l-md p-2 text-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
            <button className="bg-green-500 text-black font-bold px-4 rounded-r-md hover:bg-green-400 transition-colors">
              Send
            </button>
          </div>
        </div>
      );
    };

    export default LiveChat;
