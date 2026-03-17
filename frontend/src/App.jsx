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
  const latencyMs = rulaData?.fps ? Math.round(1000 / rulaData.fps) : null;

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
    <div className="min-h-screen bg-gray-100">
      {/* Help Button - Fixed position in top-right */}
      <HelpButton onClick={handleHelpClick} />

      {/* Help Modal - Overlay */}
      <HelpModal isOpen={isHelpModalOpen} onClose={handleCloseHelpModal} />

      {/* Main Content Container - Uses flexbox with gaps for proper spacing */}
      <div className="max-w-350 mx-auto px-4 py-4 flex flex-col gap-4 min-h-screen">
        {/* Application Header/Title */}
        <Header />

        {/* Error Message Display */}
        {error && (
          <div className="flex justify-center w-full">
            <div className="flex items-center justify-center gap-3 max-w-md mx-auto w-full p-4 bg-red-50 border border-red-200 rounded-lg">
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

        {/* Video Display and RULA Assessment Section */}
        <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_380px] gap-4 items-start flex-1">
          {/* Video Display - Shows Flask backend processed stream */}
          <div className="min-w-0">
            <VideoDisplay videoUrl={videoUrl} isActive={isActive} />
          </div>

          {/* RULA Assessment + Control */}
          <div className="xl:sticky xl:top-4 space-y-3">
            {isActive && (
              <div className="max-h-[72vh] overflow-y-auto">
                <RulaDisplay rulaData={rulaData} />
              </div>
            )}
            <div className="bg-white border border-blue-200 rounded-2xl p-3 shadow-sm">
              <ControlButton
                isActive={isActive}
                isLoading={isLoading}
                onClick={toggleWebcam}
                fullWidth
              />
            </div>
          </div>
        </div>

        {/* Bottom Status Bar */}
        <div className="mt-auto bg-white border border-gray-200 rounded-xl px-4 py-3 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-gray-600">
            <div className="flex items-center gap-4">
              <div className="inline-flex items-center gap-2">
                <span className={`w-2.5 h-2.5 rounded-full ${isActive ? "bg-green-500" : "bg-gray-300"}`} />
                <span>{isActive ? "CONNECTED TO BACKEND" : "BACKEND IDLE"}</span>
              </div>
              <div>FPS: {rulaData?.fps ?? "--"}</div>
              <div>LATENCY: {latencyMs ?? "--"}ms</div>
            </div>
            <div className="font-medium tracking-wide text-gray-500">
              {isActive ? "REAL-TIME ANALYSIS ACTIVE" : "READY"}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
