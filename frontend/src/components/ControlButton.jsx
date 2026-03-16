const ControlButton = ({ isActive, onClick, isLoading = false }) => {
  /**
   * Determine button text based on current state
   */
  const getButtonText = () => {
    if (isLoading) return 'Initializing...';
    if (isActive) return 'Matikan Webcam';
    return 'Aktifkan Webcam';
  };

  /**
   * Determine button styling based on current state
   */
  const getButtonClasses = () => {
    const baseClasses = 'px-6! py-3! mb-2! text-lg font-semibold rounded-lg transition-all duration-300 shadow-lg hover:shadow-xl transform hover:scale-105';
    
    if (isLoading) {
      return `${baseClasses} bg-gray-400 text-white cursor-not-allowed`;
    }
    
    if (isActive) {
      return `${baseClasses} bg-red-500 text-white hover:bg-red-600`;
    }
    
    return `${baseClasses} bg-blue-500 text-white hover:bg-blue-600`;
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
        <span className="flex items-center gap-2">
          <svg
            className="w-6 h-6"
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
                d="M6 18L18 6M6 6l12 12"
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
