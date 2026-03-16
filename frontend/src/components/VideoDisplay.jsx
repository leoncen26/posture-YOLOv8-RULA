/**
 * VideoDisplay Component
 * 
 * Purpose:
 * Container component that displays the video stream from Flask backend.
 * The backend processes one camera feed with complete RULA pose analysis.
 * 
 * Props:
 * @param {string|null} videoUrl - The backend video stream URL
 * @param {boolean} isActive - Whether the video stream is active
 * 
 * @returns {JSX.Element} The rendered video display container
 */

import VideoPanel from './VideoPanel';

const VideoDisplay = ({ videoUrl, isActive }) => {
  return (
    <div className="w-full max-w-5xl mx-auto mb-8">
      {/* Single video panel displaying backend-processed stream */}
      <VideoPanel
        videoUrl={videoUrl}
        isActive={isActive}
      />
      
      {/* Info Panel - Shows what the backend is analyzing */}
      {isActive && (
        <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <h3 className="font-semibold text-blue-900 mb-2">📊 Real-Time Analysis Active</h3>
          <div className="text-sm text-blue-800 space-y-1">
            <p>✓ Pose detection with YOLOv8</p>
            <p>✓ Joint angle calculations (elbow, upper arm, wrist, neck, trunk)</p>
            <p>✓ Official RULA scoring (Tables A, B, C)</p>
            <p>✓ Risk classification with recommendations</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default VideoDisplay;
