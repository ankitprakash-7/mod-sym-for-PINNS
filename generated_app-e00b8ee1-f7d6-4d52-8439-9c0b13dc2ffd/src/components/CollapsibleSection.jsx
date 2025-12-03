import { ChevronDown } from 'lucide-react';

    const CollapsibleSection = ({ title, isOpen, onToggle, children }) => {
      return (
        <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden my-2 shadow-lg">
          <button
            onClick={onToggle}
            className="w-full flex justify-between items-center p-4 bg-gray-900/50 hover:bg-gray-700/50 focus:outline-none transition-colors duration-200"
          >
            <h2 className="text-lg font-semibold text-white">{title}</h2>
            <ChevronDown
              className={`transform transition-transform duration-300 text-white ${
                isOpen ? 'rotate-180' : ''
              }`}
              size={24}
            />
          </button>
          <div
            className={`grid transition-all duration-500 ease-in-out ${
              isOpen ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'
            }`}
          >
            <div className="overflow-hidden">
              <div className="p-4">{children}</div>
            </div>
          </div>
        </div>
      );
    };

    export default CollapsibleSection;
