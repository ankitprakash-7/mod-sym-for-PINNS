import { useState, useRef } from 'react';

    // A mock summarization function
    const generateMockSummary = (text) => {
      if (!text) return "";
      const sentences = text.split('. ');
      // Take the first 3 sentences or less if the text is shorter
      const summarySentences = sentences.slice(0, 3);
      let summary = summarySentences.join('. ');
      if (sentences.length > 3) {
        summary += '...';
      }
      return summary;
    };

    export default function TextSummarizer() {
      const [fileName, setFileName] = useState('');
      const [textContent, setTextContent] = useState('');
      const [summary, setSummary] = useState('');
      const [isLoading, setIsLoading] = useState(false);
      const [error, setError] = useState('');
      const fileInputRef = useRef(null);

      const handleFileChange = (event) => {
        const file = event.target.files[0];
        if (!file) return;

        if (file.type !== 'text/plain') {
          setError('Invalid file type. Please upload a .txt file.');
          setFileName('');
          setTextContent('');
          setSummary('');
          return;
        }

        setError('');
        setFileName(file.name);
        setSummary(''); // Reset summary on new file upload

        const reader = new FileReader();
        reader.onload = (e) => {
          setTextContent(e.target.result);
        };
        reader.readAsText(file);
      };

      const handleUploadClick = () => {
        fileInputRef.current.click();
      };

      const handleSummarize = () => {
        if (!textContent) {
          setError('Please upload a file first.');
          return;
        }
        setIsLoading(true);
        setError('');
        
        // Simulate API call delay
        setTimeout(() => {
          const generatedSummary = generateMockSummary(textContent);
          setSummary(generatedSummary);
          setIsLoading(false);
        }, 1500);
      };

      return (
        <div className="bg-gray-50 min-h-screen flex flex-col items-center justify-center p-4 sm:p-6 lg:p-8">
          <div className="w-full max-w-4xl bg-white rounded-2xl shadow-lg p-6 md:p-10 space-y-8">
            <header className="text-center">
              <h1 className="text-3xl sm:text-4xl font-bold text-gray-800">
                Text File Summarizer
              </h1>
              <p className="mt-2 text-md text-gray-600">
                Upload a text file and get a quick summary.
              </p>
            </header>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <input
                type="file"
                accept=".txt"
                ref={fileInputRef}
                onChange={handleFileChange}
                className="hidden"
              />
              <button
                onClick={handleUploadClick}
                className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-3 bg-indigo-600 text-white font-semibold rounded-lg shadow-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-all"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
                </svg>
                Upload .txt file
              </button>

              <button
                onClick={handleSummarize}
                disabled={!textContent || isLoading}
                className="w-full sm:w-auto px-8 py-3 bg-green-600 text-white font-semibold rounded-lg shadow-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-all disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Summarizing...' : 'Summarize'}
              </button>
            </div>
            
            {error && <p className="text-center text-red-500 font-medium">{error}</p>}
            {fileName && !error && <p className="text-center text-gray-700">File: <span className="font-semibold">{fileName}</span></p>}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
              <div className="space-y-4">
                <h2 className="text-xl font-semibold text-gray-700">Original Text</h2>
                <div className="prose prose-sm max-w-none h-80 bg-gray-100 rounded-lg p-4 overflow-y-auto border border-gray-200">
                  <p className='whitespace-pre-wrap'>{textContent || "Your file's content will appear here..."}</p>
                </div>
              </div>
              <div className="space-y-4">
                <h2 className="text-xl font-semibold text-gray-700">Summary</h2>
                <div className="prose prose-sm max-w-none h-80 bg-gray-100 rounded-lg p-4 overflow-y-auto border border-gray-200">
                  {isLoading ? (
                     <div className="space-y-3 animate-pulse">
                        <div className="h-4 bg-gray-300 rounded w-5/6"></div>
                        <div className="h-4 bg-gray-300 rounded w-full"></div>
                        <div className="h-4 bg-gray-300 rounded w-4/6"></div>
                        <div className="h-4 bg-gray-300 rounded w-3/4"></div>
                     </div>
                  ) : (
                    <p className='whitespace-pre-wrap'>{summary || 'Your summary will appear here...'}</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      );
    }
