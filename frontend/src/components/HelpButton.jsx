const HelpButton = ({ onClick }) => {
  return (
    <button
      onClick={onClick}
      className="fixed top-6 right-6 w-10 h-10 bg-gray-200 hover:bg-gray-300 rounded-full border border-gray-300 shadow-sm transition-all duration-200 flex items-center justify-center group z-30"
      aria-label="Help"
      title="Help and Information"
    >
      {/* Question Mark Icon */}
      <span className="text-base font-bold text-gray-600 group-hover:text-gray-800">
        ?
      </span>
    </button>
  );
};

export default HelpButton;
