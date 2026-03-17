const ControlButton = ({ isActive, onClick, isLoading = false, fullWidth = false }) => {
  /**
   * Determine button text based on current state
   */
  const getButtonText = () => {
    if (isLoading) return 'Initializing...';
    if (isActive) return 'STOP CAMERA';
    return 'START CAMERA';
  };

  /**
   * Determine button styling based on current state
   */
  const getButtonClasses = () => {
    const widthClass = fullWidth ? 'w-full' : 'min-w-[260px]';
    const baseClasses = `${widthClass} px-6 py-3 text-sm font-semibold rounded-xl transition-all duration-200 shadow-sm border`;
    
    if (isLoading) {
      return `${baseClasses} bg-gray-300 border-gray-300 text-white cursor-not-allowed`;
    }
    
    if (isActive) {
      return `${baseClasses} bg-blue-600 border-blue-700 text-white hover:bg-blue-700`;
    }
    
    return `${baseClasses} bg-emerald-600 border-emerald-700 text-white hover:bg-emerald-700`;
  };

  return (
    <div className="flex justify-center">
      <button
        onClick={onClick}
        disabled={isLoading}
        className={getButtonClasses()}
        aria-label={getButtonText()}
      >
        {/* Button Icon (optional camera icon) */}
        <span className="flex items-center justify-center gap-2">
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            {isActive ? (
              // Stop icon
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 6l12 12M6 18L18 6"
              />
            ) : (
              // Camera icon
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
              />
            )}
          </svg>
          {getButtonText()}
        </span>
      </button>
    </div>
  );
};

export default ControlButton;
