/**
 * Header Component
 * 
 * Purpose:
 * Displays the main title and subtitle of the Posture Analysis System.
 * This component provides the application branding and brief description.
 * 
 * Props: None
 * 
 * @returns {JSX.Element} The rendered header section
 */

const Header = () => {
  return (
    <header className="bg-white border border-gray-200 rounded-2xl px-5 py-3 shadow-sm">
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
    </header>
  );
};

export default Header;
