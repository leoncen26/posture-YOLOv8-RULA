/**
 * App Component - Main Application Entry Point
 *
 * Purpose:
 * The root component of the Posture Analysis System.
 * Orchestrates all child components and manages the global application state.
 * Connects to Flask backend for real-time pose analysis with RULA scoring.
 *
 * Architecture:
 * - Uses custom hooks for backend connection management (useWebcam, useRulaData)
 * - Implements component composition for clean separation of concerns
 * - Manages modal states for help/info display
 *
 * Component Hierarchy:
 * App
 *  ├── HelpButton
 *  ├── HelpModal
 *  ├── Header
 *  ├── VideoDisplay
 *  │    └── VideoPanel (Flask backend stream with pose overlay)
 *  ├── RulaDisplay (Real-time RULA assessment from JSON API)
 *  └── ControlButton
 *
 * @returns {JSX.Element} The complete application UI
 */

import { useState } from "react";
// import "./App.css";

// Component Imports
import Header from "./components/Header";
import VideoDisplay from "./components/VideoDisplay";
import ControlButton from "./components/ControlButton";
import HelpButton from "./components/HelpButton";
import HelpModal from "./components/HelpModal";
import RulaDisplay from "./components/RulaDisplay";

// Custom Hook Imports
import useWebcam from "./hooks/useWebcam";
import useRulaData from "./hooks/useRulaData";

function App() {
  // Backend connection state management via custom hook
  const { videoUrl, isActive, isLoading, error, toggleWebcam } = useWebcam();

  // RULA data fetching hook
  const rulaData = useRulaData(isActive);

  // Modal state management
  const [isHelpModalOpen, setIsHelpModalOpen] = useState(false);

  /**
   * Handler for help button click
   * Opens the help modal
   */
  const handleHelpClick = () => {
    setIsHelpModalOpen(true);
  };

  /**
   * Handler for closing help modal
   */
  const handleCloseHelpModal = () => {
    setIsHelpModalOpen(false);
  };

  return (
    <div className="min-h-screen bg-linear-to-br from-gray-50 to-gray-100">
      {/* Help Button - Fixed position in top-right */}
      <HelpButton onClick={handleHelpClick} />

      {/* Help Modal - Overlay */}
      <HelpModal isOpen={isHelpModalOpen} onClose={handleCloseHelpModal} />

      {/* Main Content Container - Uses flexbox with gaps for proper spacing */}
      <div className="container mx-auto px-4 py-8 flex flex-col gap-4 min-h-0">
        {/* Application Header/Title */}
        <Header />

        {/* Error Message Display */}
        {error && (
          <div className="flex justify-center w-full">
            <div className="flex items-center justify-center gap-3 max-w-md mx-auto w-full p-4! bg-red-50 border border-red-200 rounded-lg">
              <svg
                className="w-6 h-6 text-red-500 shrink-0 mt-0.5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <div>
                <h3 className="font-semibold text-red-800">Backend Connection Error</h3>
                <p className="text-red-700 text-sm mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Video Display and RULA Assessment Section - Adjusted for better visibility */}
        <div className="flex justify-center items-start gap-4 px-4">
          {/* Video Display - Shows Flask backend processed stream */}
          <div className="shrink-0 max-w-3xl">
            <VideoDisplay videoUrl={videoUrl} isActive={isActive} />
          </div>

          {/* RULA Assessment Display - Compact panel beside video with max height */}
          {isActive && (
            <div className="shrink-0 max-h-[70vh] overflow-y-auto">
              <RulaDisplay rulaData={rulaData} />
            </div>
          )}
        </div>

        {/* Control Button Section - Backend connection toggle */}
        <div className="mb-6">
          <ControlButton
            isActive={isActive}
            isLoading={isLoading}
            onClick={toggleWebcam}
          />
        </div>

        {/* Status Information Display */}
        {isActive && (
          <div className="text-center">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-green-50 border border-green-200 rounded-full">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-sm text-green-700 font-medium">
                Connected to Backend - Real-Time RULA Analysis Active
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="text-center py-4! text-gray-500 text-sm">
        <p>Posture Analysis System © 2026 | RULA Assessment Tool</p>
      </footer>
    </div>
  );
}

export default App;
