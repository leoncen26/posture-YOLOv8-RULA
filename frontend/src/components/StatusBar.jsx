/**
 * StatusBar Component - Real-time Application Status Display
 *
 * Purpose:
 * Displays connection status, FPS, latency, and analysis state.
 * Provides real-time feedback on backend connectivity and performance.
 */

export default function StatusBar({ isActive, rulaData }) {
  // Calculate latency in milliseconds based on FPS
  const latencyMs = rulaData?.fps ? Math.round(1000 / rulaData.fps) : null;

  return (
    <div className="mt-auto bg-white border border-gray-200 rounded-xl px-4 py-3 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-gray-600">
        <div className="flex items-center gap-4">
          {/* Connection Status Indicator */}
          <div className="inline-flex items-center gap-2">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                isActive ? "bg-green-500" : "bg-gray-300"
              }`}
            />
            <span>
              {isActive ? "CONNECTED TO BACKEND" : "BACKEND IDLE"}
            </span>
          </div>

          {/* Performance Metrics */}
          <div>FPS: {rulaData?.fps ?? "--"}</div>
          <div>LATENCY: {latencyMs ?? "--"}ms</div>
        </div>

        {/* Analysis Status */}
        <div className="font-medium tracking-wide text-gray-500">
          {isActive ? "REAL-TIME ANALYSIS ACTIVE" : "READY"}
        </div>
      </div>
    </div>
  );
}
