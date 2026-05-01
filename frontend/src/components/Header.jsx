const Header = ({ onHelpClick }) => {
  return (
    <header className="bg-white border border-gray-200 rounded-2xl px-5 py-3 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-md bg-blue-600 text-white flex items-center justify-center">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
          </div>
          <div>
            <h1 className="text-[30px] font-bold text-gray-900 leading-tight">
              Table Manner Posture Detection & RULA Assessment
            </h1>
          </div>
        </div>
        
        {/* Help Button */}
        <button
          onClick={onHelpClick}
          className="w-10 h-10 bg-gray-200 hover:bg-gray-300 rounded-full border border-gray-300 shadow-sm transition-all duration-200 flex items-center justify-center group flex-shrink-0 ml-4"
          aria-label="Help"
          title="Help and Information"
        >
          <span className="text-base font-bold text-gray-600 group-hover:text-gray-800">
            ?
          </span>
        </button>
      </div>
    </header>
  );
};

export default Header;
