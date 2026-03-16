/**
 * HelpModal Component
 * 
 * Purpose:
 * Displays a modal with information about how to use the posture analysis system.
 * Provides instructions and guidelines for proper usage.
 * 
 * Props:
 * @param {boolean} isOpen - Whether the modal is currently open
 * @param {Function} onClose - Callback function to close the modal
 * 
 * @returns {JSX.Element|null} The rendered modal or null if closed
 */

const HelpModal = ({ isOpen, onClose }) => {
  // Don't render if modal is closed
  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop - darkened background */}
      <div
        className="fixed inset-0 bg-black/70 z-40 transition-opacity"
        onClick={onClose}
      />
      
      {/* Modal Content */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
          {/* Modal Header */}
          <div className="flex items-center justify-between px-4! py-2! border-b">
            <h2 className="text-2xl font-bold text-gray-800">
              Posture Analysis System - Help
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
              aria-label="Close"
            >
              <svg
                className="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
          
          {/* Modal Body */}
          <div className="p-4! space-y-4!">
            {/* Introduction */}
            <section>
              <h3 className="text-lg font-semibold text-gray-800 mb-2">
                What is this system?
              </h3>
              <p className="text-gray-600">
                The Posture Analysis System uses real-time video analysis to evaluate
                your sitting posture. It uses the RULA (Rapid Upper Limb Assessment)
                method to identify potentially harmful postures and provide feedback.
              </p>
            </section>
            
            {/* How to Use */}
            <section>
              <h3 className="text-lg font-semibold text-gray-800 mb-2">
                How to use:
              </h3>
              <ol className="list-decimal list-inside space-y-2 text-gray-600">
                <li>Click the "Aktifkan Webcam" button to start your camera</li>
                <li>Position yourself so you're visible in both front and side views</li>
                <li>Sit naturally at your desk or table</li>
                <li>The system will analyze your posture in real-time</li>
                <li>Follow the recommendations to improve your posture</li>
              </ol>
            </section>
            
            {/* Tips */}
            <section>
              <h3 className="text-lg font-semibold text-gray-800 mb-2">
                Tips for best results:
              </h3>
              <ul className="list-disc list-inside space-y-2 text-gray-600">
                <li>Ensure good lighting in your workspace</li>
                <li>Position your camera at desk level</li>
                <li>Keep your entire upper body visible</li>
                <li>Avoid wearing loose clothing that obscures your posture</li>
                <li>Maintain a neutral, natural sitting position</li>
              </ul>
            </section>
            
            {/* Privacy Notice */}
            <section className="bg-blue-50 p-4! rounded-lg">
              <h3 className="text-lg font-semibold text-blue-800 mb-2">
                Privacy Notice
              </h3>
              <p className="text-blue-700 text-sm">
                All video processing is done locally in your browser. No video data
                is stored or transmitted to external servers. Your privacy is protected.
              </p>
            </section>
          </div>
          
          {/* Modal Footer */}
          <div className="p-4! bg-gray-50">
            <button
              onClick={onClose}
              className="w-full px-6! py-3! bg-blue-500 text-white font-semibold rounded-lg! hover:bg-blue-600 transition-colors"
            >
              Got it!
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default HelpModal;
