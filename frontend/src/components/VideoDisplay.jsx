/**
 * VideoDisplay Component
 * 
 * Purpose:
 * Container component that displays the video stream from Flask backend.
 * The backend processes one camera feed with complete RULA pose analysis.
 */

import VideoPanel from './VideoPanel';

const VideoDisplay = ({ videoUrl, isActive }) => {
  return (
    <div className="w-full">
      {/* Single video panel displaying backend-processed stream */}
      <VideoPanel
        videoUrl={videoUrl}
        isActive={isActive}
      />
      
      {/* Info Panel - Shows what the backend is analyzing */}
      {isActive && (
        <div className="mt-3 p-3 bg-white border border-blue-100 rounded-xl shadow-sm">
          <h3 className="font-semibold text-blue-900 text-sm mb-2">Real-Time Analysis Active</h3>
          <div className="text-xs text-blue-800 space-y-1">
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
