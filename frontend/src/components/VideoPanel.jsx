/**
 * VideoPanel Component
 * 
 * Purpose:
 * Displays the video stream from Flask backend with pose analysis overlay.
 * The backend processes the video and adds all pose detection visualizations,
 * so this component simply displays the processed stream.
 * 
 * Props:
 * @param {string|null} videoUrl - The backend video stream URL
 * @param {boolean} isActive - Whether the video stream is active
 * 
 * @returns {JSX.Element} The rendered video panel
 */

const VideoPanel = ({ videoUrl, isActive }) => {
  return (
    <div className="relative w-full bg-white border border-gray-200 rounded-2xl overflow-hidden shadow-sm">
      {/* Placeholder/Inactive State */}
      {!isActive ? (
        <div className="aspect-video bg-gray-100 flex items-center justify-center">
          <div className="text-center p-8">
            <div className="w-24 h-24 mx-auto mb-4 bg-gray-200 rounded-full flex items-center justify-center">
              <svg
                className="w-12 h-12 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                />
              </svg>
            </div>
            <p className="text-gray-700 font-semibold">
              Posture Analysis Camera
            </p>
            <p className="text-sm text-gray-400 mt-2">
              Click "Start Camera" to begin
            </p>
          </div>
        </div>
      ) : (
        <>
          {/* Video Stream from Backend - displays processed video with pose overlay */}
          <img
            src={videoUrl}
            alt="Pose Analysis Stream"
            className="w-full h-auto object-contain bg-gray-900"
            style={{ maxHeight: '69vh' }}
          />
          
          {/* Live Indicator */}
          <div className="absolute top-4 left-4 flex items-center gap-2 bg-black/80 text-white px-3 py-1.5 rounded-full text-xs font-semibold tracking-wide border border-white/20">
            <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
            REC • LIVE WEBCAM FEED
          </div>

          {/* Backend Connection Indicator */}
          <div className="absolute top-4 right-4 bg-green-500/90 text-white px-2.5 py-1 rounded-md text-[11px] font-semibold border border-green-300/60">
            BACKEND ONLINE
          </div>
        </>
      )}
    </div>
  );
};

export default VideoPanel;
