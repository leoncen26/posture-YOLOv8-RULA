const VOICE_COOLDOWN_MS = 10000;

const shouldSpeakVoiceFeedback = (score, prevScore, lastSpokenTime) => {
  const now = Date.now();

  if (!Number.isFinite(score)) return false;
  if (lastSpokenTime && now - lastSpokenTime < VOICE_COOLDOWN_MS) return false;

  // Speak only when score changes by at least 1 point.
  if (prevScore !== null && Math.abs(score - prevScore) < 1) return false;

  return true;
};

export const getVoiceFeedbackEnglish = (score, prevScore, lastSpokenTime) => {
  if (!shouldSpeakVoiceFeedback(score, prevScore, lastSpokenTime)) return null;

  if (score <= 2) {
    return {
      message: 'Lovely posture. Please keep your back gently upright, shoulders relaxed, and elbows close to your body for elegant table manner.',
      delay: 300,
    };
  }

  if (score <= 4) {
    return {
      message: 'You are doing well. For a more refined dining posture, sit a little taller, avoid leaning toward the plate, and keep your neck long and comfortable.',
      delay: 300,
    };
  }

  if (score <= 6) {
    return {
      message: 'A gentle reminder: please straighten your back, lift your chin slightly, and relax your shoulders while keeping your elbows near your body.',
      delay: 300,
    };
  }

  return {
    message: 'Let us correct your posture calmly. Sit upright, avoid slouching over the table, keep your neck neutral, and dine with small controlled arm movement.',
    delay: 300,
  };
};

export const getVoiceFeedbackIndonesian = (score, prevScore, lastSpokenTime) => {
  if (!shouldSpeakVoiceFeedback(score, prevScore, lastSpokenTime)) return null;

  if (score <= 2) {
    return {
      message: 'Postur Anda sudah sangat baik. Pertahankan punggung tegak santai, bahu rileks, dan siku tetap dekat badan saat makan.',
      delay: 300,
    };
  }

  if (score <= 4) {
    return {
      message: 'Postur Anda sudah cukup baik. Untuk table manner yang lebih elegan, duduk sedikit lebih tegak, jangan terlalu condong ke piring, dan jaga leher tetap nyaman.',
      delay: 300,
    };
  }

  if (score <= 6) {
    return {
      message: 'Pengingat halus: luruskan punggung, angkat dagu sedikit, rilekskan bahu, dan jaga siku tetap dekat badan saat menggunakan alat makan.',
      delay: 300,
    };
  }

  return {
    message: 'Mari perbaiki postur secara perlahan. Duduk tegak, hindari membungkuk ke meja, jaga leher netral, dan lakukan gerakan tangan yang lebih terkontrol saat makan.',
    delay: 300,
  };
};
