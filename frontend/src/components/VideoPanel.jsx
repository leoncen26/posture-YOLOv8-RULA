/**
 * VideoPanel Component
 * 
 * Purpose:
 * Displays the video stream from Flask backend with pose analysis overlay.
 * The backend processes the video and adds all pose detection visualizations,
 * so this component simply displays the processed stream.
 */

const getRiskColor = (color) => {
  if (!color || color.length !== 3) return '#111827';
  const [b, g, r] = color;
  return `rgb(${r}, ${g}, ${b})`;
};

const VideoPanel = ({ videoUrl, isActive, rulaData }) => {
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

          {/* Optional overlay: quick RULA grand score badge (delete this block to remove) */}
          {rulaData?.detected && Number.isFinite(rulaData?.final_score) && (
            <div className="absolute right-4 top-1/2 -translate-y-1/2 bg-white/85 text-gray-900 border border-gray-200 rounded-xl px-3 py-2 text-center shadow-sm backdrop-blur">
              <div className="text-[10px] uppercase tracking-wide text-gray-500 font-semibold">RULA</div>
              <div className="text-3xl font-bold leading-none" style={{ color: getRiskColor(rulaData?.color) }}>
                {rulaData.final_score}
              </div>
              <div className="text-[10px] text-gray-500">Grand Score</div>
            </div>
          )}
          
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
