/**
 * HelpButton Component
 * 
 * Purpose:
 * A floating help button that provides information about the system.
 * Positioned in the top-right corner of the application.
 * Opens a modal or tooltip with usage instructions when clicked.
 * 
 * Props:
 * @param {Function} onClick - Callback function to handle help button clicks
 * 
 * @returns {JSX.Element} The rendered help button
 */

const HelpButton = ({ onClick }) => {
  return (
    <button
      onClick={onClick}
      className="fixed top-6 right-6 w-12 h-12 bg-gray-200 hover:bg-gray-300 rounded-full shadow-lg transition-all duration-300 hover:shadow-xl flex items-center justify-center group"
      aria-label="Help"
      title="Help and Information"
    >
      {/* Question Mark Icon */}
      <span className="text-2xl font-bold text-gray-600 group-hover:text-gray-800">
        ?
      </span>
    </button>
  );
};

export default HelpButton;
