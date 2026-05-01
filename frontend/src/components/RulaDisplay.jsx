/**
 * RulaDisplay Component
 * Purpose: Shows all backend RULA data in a compact right-side panel.
 */

import React, { useEffect, useState } from 'react';
import { getVoiceFeedbackEnglish, getVoiceFeedbackIndonesian } from '../utils/voiceFeedback';

// Maximum scores for each body part (used for ratio-based color calculation)
const SCORE_LIMITS = {
  upper_arm_score: 6,
  lower_arm_score: 2,
  wrist_score: 3,
  neck_score: 4,
  trunk_score: 4,
  legs_score: 2,
};

const METRIC_CONFIG = [
  { key: 'upper_arm_score', label: 'Upper Arm' },
  { key: 'lower_arm_score', label: 'Lower Arm' },
  { key: 'wrist_score', label: 'Wrist' },
  { key: 'neck_score', label: 'Neck Position' },
  { key: 'trunk_score', label: 'Trunk Angle' },
  { key: 'legs_score', label: 'Legs Support' },
];

const getRiskColor = (color) => {
  if (!color || color.length !== 3) return '#6b7280';
  const [b, g, r] = color;
  return `rgb(${r}, ${g}, ${b})`;
};

const getConfidenceColor = (conf) => {
  if (conf >= 80) return '#16a34a';
  if (conf >= 60) return '#d97706';
  if (conf >= 40) return '#ea580c';
  return '#dc2626';
};

const getMetricColor = (score, maxScore) => {
  // Ratio-based coloring reflects the score as a proportion of each joint's maximum
  // This ensures colors are consistent relative to each body part's scale
  const ratio = maxScore > 0 ? score / maxScore : 0;
  if (ratio <= 0.5) return '#16a34a';     // Green - Good (0-50% of max)
  if (ratio <= 0.75) return '#d97706';    // Orange - Fair (50-75% of max)
  return '#dc2626';                        // Red - Poor (75-100% of max)
};


const getFeedback = (score) => {
 if (score >= 1 && score <= 2) {
    return {
      title: 'Good Posture',
      message: 'Your sitting posture is elegant and suitable for table manner.',
      suggestions: [
        'Keep your back straight and shoulders relaxed while eating',
        'Maintain a comfortable neck position without looking too far down at your plate',
        'Keep elbows close to your body when using utensils'
      ],
      tone: 'text-green-700 bg-green-50 border-green-200',
      textColor: 'text-green-700',
      pillClass: 'bg-green-100 text-green-700',
    };
  }

  if (score >= 3 && score <= 4) {
    return {
      title: 'Fair Posture - Needs Attention',
      message: 'Your posture is acceptable but can be improved for better table manner.',
      suggestions: [
        'Avoid leaning forward too much when reaching for food',
        'Keep your head slightly raised instead of looking down excessively',
        'Position your elbows closer to your body while dining'
      ],
      tone: 'text-amber-700 bg-amber-50 border-amber-200',
      textColor: 'text-amber-700',
      pillClass: 'bg-amber-100 text-amber-700',
    };
  }

  if (score >= 5 && score <= 6) {
    return {
      title: 'Poor Posture - Improve Soon',
      message: 'Your current posture may affect table manner and comfort.',
      suggestions: [
        'Straighten your back and avoid slouching over the table',
        'Lift your head slightly to maintain proper neck alignment',
        'Bring your elbows closer to your body when using cutlery'
      ],
      tone: 'text-orange-700 bg-orange-50 border-orange-200',
      textColor: 'text-orange-700',
      pillClass: 'bg-orange-100 text-orange-700',
    };
  }

  return {
    title: 'Bad Posture - Correct Immediately',
    message: 'Your posture needs immediate correction for proper table manner.',
    suggestions: [
      'Sit upright with your back straight against the chair',
      'Avoid hunching or looking too far down at your plate',
      'Keep shoulders relaxed and elbows close to your body'
    ],
    tone: 'text-red-700 bg-red-50 border-red-200',
    textColor: 'text-red-700',
    pillClass: 'bg-red-100 text-red-700',
  };
};

const RulaDisplay = ({ rulaData }) => {
  const [prevSpokenScore, setPrevSpokenScore] = useState(null);
  const [lastSpokenTime, setLastSpokenTime] = useState(0);
  const [isVoiceEnabled, setIsVoiceEnabled] = useState(false);
  const voiceLanguage = 'en'; // Change to 'id' to use Indonesian voice feedback.

  // Cleanup: stop any queued/ongoing utterances when component unmounts.
  useEffect(() => {
    return () => {
      if (typeof window !== 'undefined' && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  useEffect(() => {
    if (!isVoiceEnabled && typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
  }, [isVoiceEnabled]);

  useEffect(() => {
    if (!rulaData?.detected || !Number.isFinite(rulaData?.final_score)) return;
    if (!isVoiceEnabled) return;
    if (typeof window === 'undefined' || !window.speechSynthesis) return;

    const score = rulaData.final_score;
    const voicePayload =
      voiceLanguage === 'id'
        ? getVoiceFeedbackIndonesian(score, prevSpokenScore, lastSpokenTime)
        : getVoiceFeedbackEnglish(score, prevSpokenScore, lastSpokenTime);

    if (!voicePayload) return;

    const timeoutId = window.setTimeout(() => {
      const utterance = new SpeechSynthesisUtterance(voicePayload.message);
      utterance.lang = voiceLanguage === 'id' ? 'id-ID' : 'en-US';
      utterance.rate = 0.95;
      utterance.pitch = 1.0;
      utterance.volume = 0.9;

      // Cancel any pending utterance so feedback stays current but not spammy.
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utterance);

      setPrevSpokenScore(score);
      setLastSpokenTime(Date.now());
    }, voicePayload.delay ?? 0);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [rulaData?.detected, rulaData?.final_score, prevSpokenScore, lastSpokenTime, voiceLanguage, isVoiceEnabled]);

  if (!rulaData || !rulaData.detected) {
    return (
      <div className="bg-white border border-gray-200 rounded-2xl shadow-sm overflow-hidden">
        <div className="px-4 py-4 border-b border-gray-200 flex items-center justify-between">
          <h3 className="text-xl font-semibold text-gray-900">RULA Assessment</h3>
          <span className="text-[11px] font-semibold px-2 py-1 rounded bg-blue-100 text-blue-700">REAL-TIME</span>
        </div>
        <div className="p-4 text-sm text-gray-500">{rulaData?.message || 'Waiting for analysis...'}</div>
      </div>
    );
  }

  const confidence = rulaData.confidence || {};
  const avgConfidence = confidence.average_confidence || 0;
  const detectedKps = confidence.detected_keypoints || 0;
  const totalKps = confidence.total_keypoints || 17;
  const fps = rulaData.fps || 0;
  const riskColor = getRiskColor(rulaData.color);
  const feedback = getFeedback(rulaData.final_score);

  return (
    <div className="bg-white border border-gray-200 rounded-2xl shadow-sm overflow-hidden">
      <div className="px-4 py-4 border-b border-gray-200 flex items-center justify-between gap-2">
        <h3 className="text-xl font-semibold text-gray-900">RULA Assessment</h3>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setIsVoiceEnabled((prev) => !prev)}
            className={`text-[11px] font-semibold px-2 py-1 rounded border ${
              isVoiceEnabled
                ? 'bg-emerald-100 text-emerald-700 border-emerald-200'
                : 'bg-gray-100 text-gray-600 border-gray-200'
            }`}
          >
            Voice: {isVoiceEnabled ? 'On' : 'Off'}
          </button>
          <span className="text-[11px] font-semibold px-2 py-1 rounded bg-blue-100 text-blue-700">REAL-TIME</span>
        </div>
      </div>

      <div className="p-4 space-y-4">
        <div className="space-y-2">
          {METRIC_CONFIG.map(({ key, label }) => {
            const value = rulaData[key] ?? 0;
            const maxScore = SCORE_LIMITS[key] || 1;
            const metricColor = getMetricColor(value, maxScore);

            return (
              <div key={key} className="flex items-center justify-between text-sm py-1.5 border-b border-gray-100 last:border-b-0">
                <span className="font-semibold text-gray-700">{label}</span>
                <span className="font-semibold" style={{ color: metricColor }}>
                  Score: {value}
                </span>
              </div>
            );
          })}
        </div>

        <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 px-3 py-4">
          <p className="text-[10px] uppercase tracking-wide text-gray-500 font-semibold text-center">Grand Score Index</p>
          <div className="mt-2 grid grid-cols-[96px_1fr] gap-3 items-start">
            <p className="text-5xl leading-none font-bold" style={{ color: riskColor }}>
              {rulaData.final_score}
            </p>
            <div className="space-y-1">
              <p className="text-[11px] uppercase tracking-wide font-semibold" style={{ color: riskColor }}>
                {rulaData.classification}
              </p>
              <span className={`inline-flex px-2 py-0.5 rounded text-[10px] font-semibold ${feedback.pillClass}`}>
                {feedback.title}
              </span>
              <p className={`text-[11px] leading-relaxed ${feedback.textColor}`}>
                {feedback.message}
              </p>
              <div className="space-y-0.5">
                {feedback.suggestions.map((item) => (
                  <p key={item} className="text-[10px] text-gray-600 leading-relaxed">- {item}</p>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="rounded-lg border border-green-200 bg-green-50 p-2.5">
            <p className="text-gray-600">Score A</p>
            <p className="text-2xl font-bold text-green-700">{rulaData.score_a}</p>
          </div>
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-2.5">
            <p className="text-gray-600">Score B</p>
            <p className="text-2xl font-bold text-amber-700">{rulaData.score_b}</p>
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
          <div className="flex items-center justify-between text-xs mb-2">  
            <span className="text-gray-600 font-medium">Detection quality: {avgConfidence}%</span>
            <span className="text-gray-500">{detectedKps}/{totalKps} keypoints</span>
          </div>
          <div className="h-2 rounded-full bg-gray-200 overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-300"
              style={{ width: `${Math.min(100, avgConfidence)}%`, backgroundColor: getConfidenceColor(avgConfidence) }}
            />
          </div>
          <div className="grid grid-cols-2 gap-2 mt-2 text-[11px] text-gray-600">
            {/* <div>Neck flexion: {rulaData.neck_flexion ?? '-'}deg</div> */}
            <div className="text-right">FPS: {fps}</div>
          </div>
        </div>

      </div>
    </div>
  );
};

export default RulaDisplay;
