/**
 * RulaDisplay Component - Compact RULA Assessment Display
 *
 * Purpose:
 * Displays real-time RULA (Rapid Upper Limb Assessment) scores
 * in a compact format that sits beside the video without scrolling.
 *
 * Features:
 * - Compact grid layout for all scores
 * - Color-coded risk classification
 * - Confidence indicator
 * - Clean, minimal design
 *
 * @param {Object} rulaData - RULA assessment data from backend
 * @returns {JSX.Element} Compact RULA display panel
 */

import React from 'react';

const RulaDisplay = ({ rulaData }) => {
  // Handle no person detected or no data
  if (!rulaData || !rulaData.detected) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-4 w-72 border-2 border-gray-200">
        <h3 className="text-sm font-bold text-gray-700 mb-2">RULA ASSESSMENT</h3>
        <p className="text-xs text-gray-500">
          {rulaData?.message || 'Waiting for analysis...'}
        </p>
      </div>
    );
  }

  // Convert BGR color from backend to RGB for CSS
  const getRiskColor = (color) => {
    if (!color || color.length !== 3) return '#999';
    const [b, g, r] = color;
    return `rgb(${r}, ${g}, ${b})`;
  };

  const riskColor = getRiskColor(rulaData.color);

  // Get confidence data
  const confidence = rulaData.confidence || {};
  const avgConfidence = confidence.average_confidence || 0;
  const detectedKps = confidence.detected_keypoints || 0;
  const totalKps = confidence.total_keypoints || 17;
  const fps = rulaData.fps || 0;

  // Determine confidence quality color
  const getConfidenceColor = (conf) => {
    if (conf >= 80) return '#10b981'; // Green - Excellent
    if (conf >= 60) return '#f59e0b'; // Yellow - Good  
    if (conf >= 40) return '#f97316'; // Orange - Fair
    return '#ef4444'; // Red - Poor
  };

  // Determine FPS quality color
  const getFpsColor = (fps) => {
    if (fps >= 25) return '#10b981'; // Green - Excellent
    if (fps >= 20) return '#f59e0b'; // Yellow - Good
    if (fps >= 15) return '#f97316'; // Orange - Fair
    return '#ef4444'; // Red - Poor
  };

  // Get feedback based on RULA score
  const getFeedback = (score) => {
    if (score >= 1 && score <= 2) {
      return {
        title: 'Acceptable Posture',
        message: 'Your posture is within acceptable limits. Continue maintaining good ergonomic practices.',
        suggestions: [
          'Take regular breaks every 30-60 minutes',
          'Maintain this posture to prevent future issues'
        ],
        bgColor: 'bg-green-50',
        borderColor: 'border-green-200',
        textColor: 'text-green-800'
      };
    } else if (score >= 3 && score <= 4) {
      return {
        title: 'Further Investigation Needed',
        message: 'Your posture may require attention. Consider making adjustments to reduce strain.',
        suggestions: [
          'Adjust your monitor to eye level',
          'Ensure your chair provides proper back support',
          'Keep elbows close to your body at 90-120° angle'
        ],
        bgColor: 'bg-yellow-50',
        borderColor: 'border-yellow-200',
        textColor: 'text-yellow-800'
      };
    } else if (score >= 5 && score <= 6) {
      return {
        title: 'Changes Required Soon',
        message: 'Your posture poses a risk. Make ergonomic improvements as soon as possible.',
        suggestions: [
          'Adjust desk and chair height immediately',
          'Position keyboard and mouse within easy reach',
          'Take frequent breaks to stretch and move',
          'Consider consulting an ergonomics specialist'
        ],
        bgColor: 'bg-orange-50',
        borderColor: 'border-orange-200',
        textColor: 'text-orange-800'
      };
    } else if (score === 7) {
      return {
        title: 'Immediate Action Required',
        message: 'Your posture is at high risk level. Take immediate corrective action to prevent injury.',
        suggestions: [
          'Stop and readjust your posture immediately',
          'Consult with an ergonomics professional urgently',
          'Review entire workstation setup',
          'Take a break and perform stretching exercises',
          'Consider using ergonomic equipment'
        ],
        bgColor: 'bg-red-50',
        borderColor: 'border-red-200',
        textColor: 'text-red-800'
      };
    }
    return null;
  };

  const feedback = getFeedback(rulaData.final_score);

  return (
    <div className="bg-white rounded-lg shadow-lg border-2 w-120! p-2 md:p-4! overflow-hidden" style={{ borderColor: riskColor }}>
      {/* Header with Final Score */}
      <div className="px-6 py-5 border-b" style={{ backgroundColor: riskColor + '15', borderBottomColor: riskColor }}>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-bold text-gray-800">RULA SCORE</h3>
          <div className="flex items-center gap-3 space-y-2!">
            <span className="text-4xl font-bold" style={{ color: riskColor }}>
              {rulaData.final_score}
            </span>
            <span className="text-base text-gray-500">/ 7</span>
          </div>
        </div>
        <p className="text-base font-medium" style={{ color: riskColor }}>
          {rulaData.classification}
        </p>
      </div>

      {/* Confidence Indicator */}
      <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
        <div className="flex items-center justify-between text-sm mb-3 space-y-2!">
          <div className="flex items-center gap-3">
            <span className="text-gray-700 font-medium">Quality: {avgConfidence}%</span>
            <span className="text-gray-500">{detectedKps}/{totalKps} kps</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">FPS:</span>
            <span className="font-bold text-base" style={{ color: getFpsColor(fps) }}>
              {fps}
            </span>
          </div>
        </div>
        <div className="h-2.5 bg-gray-200 rounded-full overflow-hidden">
          <div 
            className="h-full rounded-full transition-all duration-300" 
            style={{ 
              width: `${avgConfidence}%`,
              backgroundColor: getConfidenceColor(avgConfidence)
            }}
          />
        </div>
      </div>

      {/* Compact Scores Grid */}
      <div className="px-6 py-5 space-y-5">
        {/* Joint Scores - 2 columns */}
        <div className="space-y-4!">
          <h4 className="text-sm font-semibold text-gray-700 mb-4">Joint Scores</h4>
          <div className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
            <div className="flex justify-between items-center px-4! py-2.5! bg-blue-50 rounded-lg">
              <span className="text-gray-700">Upper Arm</span>
              <span className="font-bold text-blue-700 text-lg">{rulaData.upper_arm_score}</span>
            </div>
            <div className="flex justify-between items-center px-4! py-2.5! bg-blue-50 rounded-lg">
              <span className="text-gray-700">Lower Arm</span>
              <span className="font-bold text-blue-700 text-lg">{rulaData.lower_arm_score}</span>
            </div>
            <div className="flex justify-between items-center px-4! py-2.5! bg-blue-50 rounded-lg">
              <span className="text-gray-700">Wrist</span>
              <span className="font-bold text-blue-700 text-lg">{rulaData.wrist_score}</span>
            </div>
            <div className="flex justify-between items-center px-4! py-2.5! bg-purple-50 rounded-lg">
              <span className="text-gray-700">Neck</span>
              <span className="font-bold text-purple-700 text-lg">{rulaData.neck_score}</span>
            </div>
            <div className="flex justify-between items-center px-4! py-2.5! bg-purple-50 rounded-lg">
              <span className="text-gray-700">Trunk</span>
              <span className="font-bold text-purple-700 text-lg">{rulaData.trunk_score}</span>
            </div>
            <div className="flex justify-between items-center px-4! py-2.5! bg-purple-50 rounded-lg">
              <span className="text-gray-700">Legs</span>
              <span className="font-bold text-purple-700 text-lg">{rulaData.legs_score}</span>
            </div>
          </div>
        </div>

        {/* Table Scores */}
        <div className="pt-4! border-t border-gray-200">
          <h4 className="text-sm font-semibold text-gray-700 mb-4 ">RULA Tables</h4>
          <div className="flex gap-4 text-sm">
            <div className="flex-1 px-4 py-4 bg-green-50 rounded-lg border border-green-200">
              <div className="text-gray-700 font-medium mb-2 p-2!">Score A</div>
              <div className="text-3xl font-bold text-green-700  p-2!">{rulaData.score_a}</div>
            </div>
            <div className="flex-1 px-4 py-4 bg-orange-50 rounded-lg border border-orange-200">
              <div className="text-gray-700 font-medium mb-2 p-2!">Score B</div>
              <div className="text-3xl font-bold text-orange-700  p-2!">{rulaData.score_b}</div>
            </div>
          </div>
        </div>

        {/* Feedback & Recommendations */}
        {feedback && (
          <div className={`pt-4 border-t border-gray-200`}>
            <h4 className="text-sm font-semibold text-gray-700 mb-3">Feedback & Recommendations</h4>
            <div className={`${feedback.bgColor} ${feedback.borderColor} border rounded-lg p-4`}>
              <div className={`${feedback.textColor} font-semibold text-sm mb-2`}>
                {feedback.title}
              </div>
              <p className="text-xs text-gray-700 mb-3 leading-relaxed">
                {feedback.message}
              </p>
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-gray-600 mb-1">Suggestions:</p>
                {feedback.suggestions.map((suggestion, index) => (
                  <div key={index} className="flex items-start gap-2">
                    <span className="text-xs text-gray-500 mt-0.5">•</span>
                    <span className="text-xs text-gray-700 leading-relaxed flex-1">
                      {suggestion}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default RulaDisplay;
