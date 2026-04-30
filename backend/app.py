"""
Flask Backend for Real-Time Sitting Posture Detection Using YOLOv8-Pose Based on RULA
for Table Manner Analysis

This application provides a Flask API that streams webcam video with real-time pose analysis,
calculating RULA scores for ergonomic posture assessment.
"""

import cv2
import numpy as np
from ultralytics import YOLO
import math
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
import time
import threading

# ============================================================================
# FLASK APP INITIALIZATION
# ============================================================================

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Global variables for model and video capture
model = None
cap = None
previous_keypoints_dict = {}
camera_lock = threading.Lock()
camera_state = "inactive"  # inactive | starting | active | error
camera_error = None
camera_start_thread = None

# Evaluation state (confusion matrix for 4 RULA risk classes)
EVAL_LABELS = {
    1: "Good Posture",
    2: "Fair Posture - Monitor",
    3: "Poor Posture - Improve Soon",
    4: "Bad Posture - Improve Now",
}
EVAL_LABEL_ALIASES = {
    "good": 1,
    "good posture": 1,
    "fair": 2,
    "fair posture": 2,
    "fair posture - monitor": 2,
    "poor": 3,
    "poor posture": 3,
    "poor posture - improve soon": 3,
    "bad": 4,
    "bad posture": 4,
    "bad posture - improve now": 4,
}
evaluation_confusion = [[0, 0, 0, 0] for _ in range(4)]
evaluation_lock = threading.Lock()

# Performance optimization settings
FRAME_SKIP = 4  # Process every Nth frame (skip intermediate frames) - INCREASED for CPU
TARGET_FPS = 30  # Target frame rate for streaming
INFERENCE_SIZE = 416  # Resize frame to this width for inference (faster processing) - REDUCED for CPU
JPEG_QUALITY = 70  # JPEG compression quality (0-100, lower = smaller file size) - REDUCED for CPU
last_inference_result = None  # Cache last inference result for skipped frames
last_rula_data = None  # Cache latest RULA assessment data for JSON API
current_fps = 0.0  # Current actual FPS for performance monitoring

# Stability settings for less jittery posture estimation
ANGLE_EMA_ALPHA = 0.25  # Lower = more stable, higher = more responsive
LEGS_RAISED_CONFIRM_FRAMES = 4
LEGS_NORMAL_CONFIRM_FRAMES = 5

# Temporal state for smoothing and hysteresis
posture_stability_state = {
    "upper_arm": None,
    "lower_arm": None,
    "wrist": None,
    "neck": None,
    "trunk": None,
    "legs_score": 1,
    "legs_raised_counter": 0,
    "legs_normal_counter": 0,
}


def reset_stability_state():
    """Reset temporal smoothing/debouncing state when camera session starts/stops."""
    global posture_stability_state
    posture_stability_state = {
        "upper_arm": None,
        "lower_arm": None,
        "wrist": None,
        "neck": None,
        "trunk": None,
        "legs_score": 1,
        "legs_raised_counter": 0,
        "legs_normal_counter": 0,
    }


def smooth_angle_value(key, current_value, alpha=ANGLE_EMA_ALPHA):
    """EMA smoothing for angle values to reduce rapid frame-to-frame oscillation."""
    global posture_stability_state
    previous_value = posture_stability_state.get(key)
    if previous_value is None:
        smoothed = float(current_value)
    else:
        smoothed = (alpha * float(current_value)) + ((1.0 - alpha) * float(previous_value))
    posture_stability_state[key] = smoothed
    return smoothed


def _open_camera_async():
    """Open and configure camera in a background thread to keep /start responsive."""
    global cap, camera_state, camera_error

    local_cap = None
    try:
        # On Windows, CAP_DSHOW usually opens faster; fallback to default backend.
        local_cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not local_cap.isOpened():
            local_cap.release()
            local_cap = cv2.VideoCapture(0)

        if not local_cap.isOpened():
            raise RuntimeError("Failed to open camera")

        local_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        local_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        local_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        local_cap.set(cv2.CAP_PROP_FPS, 30)

        with camera_lock:
            cap = local_cap
            camera_state = "active"
            camera_error = None

        print("✓ Webcam started successfully")
    except Exception as e:
        if local_cap is not None:
            local_cap.release()

        with camera_lock:
            cap = None
            camera_state = "error"
            camera_error = str(e)

        print(f"✗ Error starting camera: {e}")

# ============================================================================
# POSE MODEL LOADING
# ============================================================================

def load_pose_model(model_path="yolov8n-pose.pt"):
    """
    Load the YOLOv8-Pose pretrained model.
    
    Args:
        model_path: Path to the model file
    
    Returns:
        YOLO model object
    """
    try:
        model = YOLO(model_path)
        print(f"✓ Model loaded successfully from {model_path}")
        return model
    except Exception as e:
        print(f"✗ Error loading model: {e}")
        return None

# ============================================================================
# ANGLE CALCULATION FUNCTIONS
# ============================================================================

def calculate_angle(point_a, point_b, point_c):
    """
    Calculate the angle at point_b formed by points a-b-c.
    Uses vector math: angle = arccos(dot_product / (magnitude_a * magnitude_b))
    
    Args:
        point_a: (x, y) - first point (e.g., shoulder)
        point_b: (x, y) - vertex point (e.g., elbow)
        point_c: (x, y) - third point (e.g., wrist)
    
    Returns:
        angle in degrees (0-180)
    """
    # Create vectors from point_b to point_a and point_b to point_c
    vector_ba = np.array([point_a[0] - point_b[0], point_a[1] - point_b[1]])
    vector_bc = np.array([point_c[0] - point_b[0], point_c[1] - point_b[1]])
    
    # Calculate magnitudes
    magnitude_ba = np.linalg.norm(vector_ba)
    magnitude_bc = np.linalg.norm(vector_bc)
    
    # Avoid division by zero
    if magnitude_ba == 0 or magnitude_bc == 0:
        return 0
    
    # Normalize vectors and calculate dot product
    vector_ba_normalized = vector_ba / magnitude_ba
    vector_bc_normalized = vector_bc / magnitude_bc
    dot_product = np.dot(vector_ba_normalized, vector_bc_normalized)
    
    # Clamp dot product to [-1, 1] to avoid numerical errors with arccos
    dot_product = np.clip(dot_product, -1.0, 1.0)
    
    # Calculate angle in radians, then convert to degrees
    angle_rad = np.arccos(dot_product)
    angle_deg = math.degrees(angle_rad)
    
    return angle_deg

def calculate_center_point(point_a, point_b):
    """
    Calculate the center point (midpoint) between two points.
    
    Args:
        point_a: (x, y, conf) or (x, y) - first point
        point_b: (x, y, conf) or (x, y) - second point
    
    Returns:
        (x, y) center point coordinates
    """
    center_x = (point_a[0] + point_b[0]) / 2
    center_y = (point_a[1] + point_b[1]) / 2
    return (center_x, center_y)

def calculate_trunk_angle(shoulder_center, hip_center):
    """
    Calculate trunk angle - the angle between the trunk line and vertical.
    
    Args:
        shoulder_center: (x, y) - center point between shoulders
        hip_center: (x, y) - center point between hips
    
    Returns:
        angle in degrees from vertical (0° = perfectly upright)
    """
    # Vector from hip to shoulder (trunk direction)
    trunk_vector = np.array([shoulder_center[0] - hip_center[0], 
                             shoulder_center[1] - hip_center[1]])
    
    # Vertical reference vector pointing upward (in image coordinates, up is negative y)
    vertical_vector = np.array([0, -1])
    
    # Calculate magnitudes
    trunk_magnitude = np.linalg.norm(trunk_vector)
    vertical_magnitude = np.linalg.norm(vertical_vector)
    
    # Avoid division by zero
    if trunk_magnitude == 0 or vertical_magnitude == 0:
        return 0
    
    # Normalize and compute dot product
    trunk_normalized = trunk_vector / trunk_magnitude
    vertical_normalized = vertical_vector / vertical_magnitude
    dot_product = np.dot(trunk_normalized, vertical_normalized)
    
    # Clamp and calculate angle
    dot_product = np.clip(dot_product, -1.0, 1.0)
    angle_rad = np.arccos(dot_product)
    angle_deg = math.degrees(angle_rad)
    
    return angle_deg

def calculate_neck_angle(shoulder_center, nose):
    """
    Calculate neck flexion angle - the angle between the neck/head line and vertical upward.
    This is the CORRECT RULA measurement for neck posture.
    
    Accounts for natural cervical lordosis (forward curve of neck) by subtracting baseline angle.
    
    Args:
        shoulder_center: (x, y) - center point between shoulders (neck base)
        nose: (x, y) - nose/head position
    
    Returns:
        angle in degrees from NEUTRAL anatomical position (0° = neutral upright posture)
    """
    # Vector from shoulder_center to nose (neck/head direction)
    neck_vector = np.array([nose[0] - shoulder_center[0], 
                           nose[1] - shoulder_center[1]])
    
    # Vertical reference vector pointing upward (in image coordinates, up is negative y)
    vertical_upward = np.array([0, -1])
    
    # Calculate magnitudes
    neck_magnitude = np.linalg.norm(neck_vector)
    vertical_magnitude = np.linalg.norm(vertical_upward)
    
    # Avoid division by zero
    if neck_magnitude == 0 or vertical_magnitude == 0:
        return 0
    
    # Normalize and compute dot product
    neck_normalized = neck_vector / neck_magnitude
    vertical_normalized = vertical_upward / vertical_magnitude
    dot_product = np.dot(neck_normalized, vertical_normalized)
    
    # Clamp and calculate angle
    dot_product = np.clip(dot_product, -1.0, 1.0)
    angle_rad = np.arccos(dot_product)
    angle_deg = math.degrees(angle_rad)
    
    # CRITICAL: Subtract natural cervical lordosis baseline (~20-25° forward angle)
    # This accounts for the anatomical fact that the neck naturally angles forward
    # even in neutral upright posture, especially visible in side view.
    NATURAL_NECK_BASELINE = 20.0  # degrees
    
    # Calculate flexion from neutral anatomical position
    neck_flexion = max(0, angle_deg - NATURAL_NECK_BASELINE)
    
    # Return flexion angle (0° = neutral upright, positive = forward flexion)
    return neck_flexion

def calculate_upper_arm_flexion(shoulder, elbow):
    """
    Calculate upper arm flexion angle relative to vertical down (RULA official).
    0 degrees = arm straight down, 90 degrees = arm horizontal.
    
    Args:
        shoulder: (x, y) - shoulder position
        elbow: (x, y) - elbow position
    
    Returns:
        angle in degrees (0-180)
    """
    if shoulder is None or elbow is None:
        return 0.0
    
    # Upper arm vector: shoulder to elbow
    vec = np.array([elbow[0] - shoulder[0], elbow[1] - shoulder[1]])
    
    # Vertical down reference (in image coordinates, down is positive y)
    vertical_down = np.array([0, 1.0])
    
    # Calculate magnitude
    mag = np.linalg.norm(vec)
    if mag < 1e-6:
        return 0.0
    
    # Normalize and compute dot product
    cos_theta = np.dot(vec / mag, vertical_down)
    angle = math.degrees(np.arccos(np.clip(cos_theta, -1.0, 1.0)))
    
    return angle

def calculate_wrist_proxy_angle(elbow, wrist):
    """
    Estimate wrist deviation proxy using forearm orientation.

    NOTE:
    YOLOv8-Pose with 17 keypoints does not include finger/hand keypoints,
    so true wrist bend cannot be measured directly. This proxy uses elbow->wrist
    orientation and is mirrored for left/right symmetry.

    Args:
        elbow: (x, y) - elbow position
        wrist: (x, y) - wrist position

    Returns:
        Proxy angle in degrees (0-90), where 0 is near-horizontal forearm.
    """
    if elbow is None or wrist is None:
        return None

    forearm_vector = np.array([wrist[0] - elbow[0], wrist[1] - elbow[1]], dtype=float)
    forearm_magnitude = np.linalg.norm(forearm_vector)
    if forearm_magnitude < 1e-6:
        return None

    # Mirror x and y to make left/right and direction symmetric.
    return math.degrees(math.atan2(abs(forearm_vector[1]), abs(forearm_vector[0])))

# ============================================================================
# RULA SCORING FUNCTIONS
# ============================================================================

def score_upper_arm(angle, is_supported=False, is_abducted=False, is_shoulder_raised=False):

    if angle <= 20:
        score = 1
    elif angle <= 45:
        score = 2
    elif angle <= 90:
        score = 3
    else:
        score = 4

    if is_supported:
        score = max(1, score - 1)

    if is_abducted:
        score += 1

    if is_shoulder_raised:
        score += 1

    return min(score, 6)

def score_lower_arm(angle):
    """
    Official RULA scoring for lower arm (elbow) angle.
    
    Args:
        angle: Elbow angle in degrees (internal angle at elbow joint)
    
    Returns:
        Score (1-2)
    """
    # For seated table work, 60-100° is natural
    if 60 <= angle <= 100:
        return 1
    else:
        return 2

def score_wrist(angle):
    """
    Official RULA scoring for wrist angle.
    
    Args:
        angle: Wrist deviation angle in degrees from neutral
    
    Returns:
        Score (1-3)
    """
    # Official RULA:
    # Score 1: Wrist is in neutral position (0-15°)
    # Score 2: Wrist is bent or deviated (>15°)
    # Score 3: Wrist is at or near end of range (extreme position)
    if angle <= 15:
        return 1
    elif angle <= 25:
        return 2
    else:
        # Extreme wrist deviation (>45°)
        return 3

def score_neck(neck_flexion_angle):
    """
    Adapted RULA scoring for neck angle in seated posture / table manner context.
    
    Args:
        neck_flexion_angle: Neck flexion angle in degrees from neutral anatomical position
    
    Returns:
        Score (1-4)
    """
    if neck_flexion_angle <= 20:
        return 1
    elif neck_flexion_angle <= 35:
        return 2
    elif neck_flexion_angle <= 60:
        return 3
    else:  # >60° (severe flexion) or <0° (extension/backward)
        return 4

def score_trunk(angle):
    """
    Official RULA scoring for trunk angle (relative to vertical).
    
    Args:
        angle: Trunk angle in degrees (deviation from vertical)
    
    Returns:
        Score (1-6)
    """
    if angle <= 5:
        return 1
    elif angle <= 20:
        return 2
    elif angle <= 60:
        return 3
    else:
        return 4

def score_legs(keypoints, conf_threshold=0.35):
    """
    Enhanced RULA scoring for legs with TABLE MANNER analysis.

    Detects improper sitting postures such as raised legs on chair.

    IMPORTANT POLICY:
    - Score 2 only when there is clear raised-leg evidence.
    - Leg visibility/asymmetry alone must NOT trigger score 2.

    Args:
        keypoints: YOLOv8-Pose keypoints array (x, y, confidence)
        conf_threshold: Minimum confidence threshold for keypoint detection

    Returns:
        Score (1-2):
        - 1: Proper sitting posture (feet on floor, legs evenly balanced)
        - 2: Poor posture (raised legs, uneven position, cross-legged)
    """
    global posture_stability_state

    raw_score = 1

    try:
        # COCO keypoints: 11=left hip, 12=right hip, 13=left knee, 14=right knee, 15=left ankle, 16=right ankle
        if len(keypoints) < 15:
            # Not enough keypoints, assume neutral (legs hidden under table)
            raw_score = 1
        else:
            left_hip = keypoints[11]
            right_hip = keypoints[12]
            left_knee = keypoints[13]
            right_knee = keypoints[14]

            # In side-view, one leg can be partially occluded. Evaluate each side independently.
            hip_vis_left = left_hip[2] > conf_threshold
            hip_vis_right = right_hip[2] > conf_threshold
            knee_vis_left = left_knee[2] > conf_threshold
            knee_vis_right = right_knee[2] > conf_threshold

            if not ((hip_vis_left and knee_vis_left) or (hip_vis_right and knee_vis_right)):
                raw_score = 1
            else:
                raw_score = 1

                # Use body scale to make thresholds less sensitive to camera distance.
                if hip_vis_left and hip_vis_right:
                    hip_width = abs(left_hip[0] - right_hip[0])
                    scale = max(hip_width, 40.0)
                else:
                    scale = 55.0

                # Rule A: if either visible leg is clearly raised, mark non-neutral.
                if hip_vis_left and knee_vis_left:
                    if left_knee[1] < left_hip[1] - (0.22 * scale):
                        raw_score = 2

                if hip_vis_right and knee_vis_right:
                    if right_knee[1] < right_hip[1] - (0.22 * scale):
                        raw_score = 2

                # Rule C: ankle above knee on either visible side is non-neutral.
                if len(keypoints) >= 17:
                    left_ankle = keypoints[15]
                    right_ankle = keypoints[16]
                    ankle_vis_left = left_ankle[2] > conf_threshold
                    ankle_vis_right = right_ankle[2] > conf_threshold

                    if knee_vis_left and ankle_vis_left:
                        if left_ankle[1] < left_knee[1] - (0.18 * scale):
                            raw_score = 2

                    if knee_vis_right and ankle_vis_right:
                        if right_ankle[1] < right_knee[1] - (0.18 * scale):
                            raw_score = 2

    except (IndexError, TypeError, AttributeError):
        # If any error occurs, return neutral score (assume proper sitting)
        raw_score = 1

    # Debounce leg score changes to prevent wild flickering on noisy keypoints.
    current_stable = posture_stability_state.get("legs_score", 1)

    if raw_score == 2:
        posture_stability_state["legs_raised_counter"] = posture_stability_state.get("legs_raised_counter", 0) + 1
        posture_stability_state["legs_normal_counter"] = 0
        if posture_stability_state["legs_raised_counter"] >= LEGS_RAISED_CONFIRM_FRAMES:
            current_stable = 2
    else:
        posture_stability_state["legs_normal_counter"] = posture_stability_state.get("legs_normal_counter", 0) + 1
        posture_stability_state["legs_raised_counter"] = 0
        if posture_stability_state["legs_normal_counter"] >= LEGS_NORMAL_CONFIRM_FRAMES:
            current_stable = 1

    posture_stability_state["legs_score"] = current_stable
    return current_stable

def compute_table_A(upper_arm_score, wrist_score, lower_arm_score):
    """
    Official RULA Table A: Upper Limb Analysis.
    Combines Upper Arm, Wrist, and Lower Arm scores.
    
    Args:
        upper_arm_score: 1-6
        wrist_score: 1-3
        lower_arm_score: 1-2
    
    Returns:
        Score A (1-9, typically 1-6)
    """
    # RULA Table A [upper_arm][wrist][lower_arm]
    table_a = [
        # Upper Arm = 1
        [[1, 2], [2, 2], [2, 3]],
        # Upper Arm = 2
        [[2, 2], [2, 2], [3, 3]],
        # Upper Arm = 3
        [[2, 3], [3, 3], [3, 3]],
        # Upper Arm = 4
        [[3, 3], [3, 3], [3, 4]],
        # Upper Arm = 5
        [[4, 4], [4, 4], [4, 5]],
        # Upper Arm = 6
        [[5, 5], [5, 6], [6, 6]]
    ]
    
    # Clamp indices
    ua_idx = min(max(upper_arm_score - 1, 0), 5)
    w_idx = min(max(wrist_score - 1, 0), 2)
    la_idx = min(max(lower_arm_score - 1, 0), 1)
    
    return table_a[ua_idx][w_idx][la_idx]

def compute_table_B(neck_score, trunk_score, legs_score):
    """
    Official RULA Table B: Neck, Trunk, and Leg Analysis.
    
    Args:
        neck_score: 1-4
        trunk_score: 1-4
        legs_score: 1-2
    
    Returns:
        Score B (1-9, typically 1-7)
    """
    # RULA Table B [neck][trunk][legs]
    table_b = [
        # Neck = 1
        [[1, 3], [2, 3], [3, 4], [5, 5]],
        # Neck = 2
        [[2, 3], [2, 3], [4, 5], [5, 5]],
        # Neck = 3
        [[3, 3], [3, 4], [4, 5], [5, 6]],
        # Neck = 4
        [[5, 5], [5, 6], [6, 7], [7, 7]]
    ]
    
    # Clamp indices
    n_idx = min(max(neck_score - 1, 0), 3)
    t_idx = min(max(trunk_score - 1, 0), 3)
    l_idx = min(max(legs_score - 1, 0), 1)
    
    return table_b[n_idx][t_idx][l_idx]

def compute_table_C(score_a, score_b):
    """
    Official RULA Table C: Combines Score A and Score B to get Final RULA Score.
    
    Args:
        score_a: 1-9
        score_b: 1-9
    
    Returns:
        Final RULA Score (1-7)
    """
    # RULA Table C [score_b][score_a]
    table_c = [
        [1, 2, 3, 3, 4, 5, 5, 6, 6],  # Score B = 1
        [2, 2, 3, 4, 4, 5, 5, 6, 6],  # Score B = 2
        [3, 3, 3, 4, 4, 5, 6, 6, 7],  # Score B = 3
        [3, 3, 3, 4, 5, 6, 6, 7, 7],  # Score B = 4
        [4, 4, 4, 5, 6, 7, 7, 7, 7],  # Score B = 5
        [4, 4, 5, 6, 6, 7, 7, 7, 7],  # Score B = 6
        [5, 5, 6, 6, 7, 7, 7, 7, 7],  # Score B = 7
        [5, 5, 6, 7, 7, 7, 7, 7, 7],  # Score B = 8
        [6, 6, 6, 7, 7, 7, 7, 7, 7]   # Score B = 9
    ]
    
    # Clamp indices
    b_idx = min(max(score_b - 1, 0), 8)
    a_idx = min(max(score_a - 1, 0), 8)
    
    return table_c[b_idx][a_idx]

def classify_rula(final_score):
    """
    Classify RULA score into risk levels.
    
    Args:
        final_score: Final RULA score (1-7)
    
    Returns:
        (classification_text, color_bgr)
    """

    if final_score <= 2:
        return "Good Posture", (0, 255, 0)  # Green
    elif final_score <= 4:
        return "Fair Posture - Monitor", (0, 255, 255)  # Yellow
    elif final_score <= 6:
        return "Poor Posture - Improve Soon", (0, 165, 255)  # Orange
    else:  # 7
        return "Bad Posture - Improve Now", (0, 0, 255)  # Red

def _normalize_eval_label(value):
    """Normalize label input (int or str) to class id 1-4."""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        label_id = int(value)
        return label_id if 1 <= label_id <= 4 else None

    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned.isdigit():
            label_id = int(cleaned)
            return label_id if 1 <= label_id <= 4 else None
        return EVAL_LABEL_ALIASES.get(cleaned)

    return None

def _label_from_rula_classification(classification_text):
    if not classification_text:
        return None
    return _normalize_eval_label(classification_text)

def _compute_metrics_from_confusion(matrix):
    """Compute accuracy, precision, recall, and F1 from 4x4 confusion matrix."""
    totals = {
        "total_samples": 0,
        "correct": 0
    }

    per_class = []
    for idx in range(4):
        tp = matrix[idx][idx]
        fp = sum(matrix[row][idx] for row in range(4)) - tp
        fn = sum(matrix[idx]) - tp
        denom_p = tp + fp
        denom_r = tp + fn
        precision = (tp / denom_p) if denom_p > 0 else 0.0
        recall = (tp / denom_r) if denom_r > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        per_class.append({
            "label_id": idx + 1,
            "label": EVAL_LABELS[idx + 1],
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": int(sum(matrix[idx]))
        })

        totals["total_samples"] += sum(matrix[idx])
        totals["correct"] += tp

    accuracy = (totals["correct"] / totals["total_samples"]) if totals["total_samples"] > 0 else 0.0
    macro_precision = sum(item["precision"] for item in per_class) / 4
    macro_recall = sum(item["recall"] for item in per_class) / 4
    macro_f1 = sum(item["f1"] for item in per_class) / 4

    return {
        "accuracy": round(accuracy, 4),
        "precision_macro": round(macro_precision, 4),
        "recall_macro": round(macro_recall, 4),
        "f1_macro": round(macro_f1, 4),
        "per_class": per_class,
        "total_samples": totals["total_samples"],
        "correct": totals["correct"]
    }

def calculate_official_rula(upper_arm_angle, lower_arm_angle, wrist_angle, 
                            neck_angle, trunk_angle, keypoints, person_detected=True, 
                            is_arm_supported=False, is_abducted=False, legs_score_override=None):
    """
    Calculate OFFICIAL RULA score using proper tables and structure.
    
    Args:
        upper_arm_angle: Upper arm flexion angle (degrees, relative to vertical down)
        lower_arm_angle: Elbow angle (degrees)
        wrist_angle: Wrist angle (degrees)
        neck_angle: Neck flexion angle from NEUTRAL anatomical position (degrees)
        trunk_angle: Trunk angle from vertical (degrees)
        keypoints: YOLOv8-Pose keypoints array for legs scoring
        person_detected: Whether person is detected (for leg score)
        is_arm_supported: Whether arm is resting on table
        is_abducted: Whether arm is abducted or shoulder raised
    
    Returns:
        Dictionary with complete RULA assessment
    """
    # Step 1: Calculate individual joint scores
    upper_arm_score = score_upper_arm(upper_arm_angle, is_supported=is_arm_supported, 
                                     is_abducted=is_abducted)
    lower_arm_score = score_lower_arm(lower_arm_angle)
    wrist_score = score_wrist(wrist_angle)
    neck_score = score_neck(neck_angle)
    trunk_score = score_trunk(trunk_angle)
    legs_score = legs_score_override if legs_score_override is not None else score_legs(keypoints)
    
    # Step 2: Compute Score A (Group A: Upper Limb)
    score_a = compute_table_A(upper_arm_score, wrist_score, lower_arm_score)
    
    # Step 3: Compute Score B (Group B: Neck, Trunk, Legs)
    score_b = compute_table_B(neck_score, trunk_score, legs_score)
    
    # Step 4: Compute Final RULA Score (Table C)
    final_score = compute_table_C(score_a, score_b)
    
    # Step 5: Classify risk level
    classification, color = classify_rula(final_score)
    
    return {
        "upper_arm_score": upper_arm_score,
        "lower_arm_score": lower_arm_score,
        "wrist_score": wrist_score,
        "neck_score": neck_score,
        "trunk_score": trunk_score,
        "legs_score": legs_score,
        "score_a": score_a,
        "score_b": score_b,
        "final_score": final_score,
        "classification": classification,
        "color": color,
        "neck_flexion": neck_angle
    }

# ============================================================================
# KEYPOINT PROCESSING AND SMOOTHING
# ============================================================================

def smooth_keypoints_with_tracking(results, previous_keypoints_dict, alpha=0.3):
    """
    Apply exponential smoothing to keypoints using tracking IDs.
    This stabilizes skeleton visualization across frames.
    
    Formula: smoothed = alpha * current + (1 - alpha) * previous
    
    Args:
        results: YOLO tracking results (from model.track())
        previous_keypoints_dict: Dictionary mapping person_id -> smoothed keypoints (17x3)
        alpha: Smoothing factor (0 to 1). Lower = smoother but more lag.
    
    Returns:
        smoothed_keypoints: NumPy array (N, 17, 3) with smoothed x, y and original confidence
        updated_dict: Updated dictionary with latest smoothed keypoints
    """
    # Check if tracking results exist
    if results[0].keypoints is None or results[0].keypoints.data is None:
        return None, previous_keypoints_dict
    
    # Get current keypoints and tracking IDs
    current_keypoints = results[0].keypoints.data.cpu().numpy()  # Shape: (N, 17, 3)
    
    # Check if tracking IDs are available
    if results[0].boxes is None or results[0].boxes.id is None:
        # No tracking IDs available, return current keypoints without smoothing
        return current_keypoints, previous_keypoints_dict
    
    tracking_ids = results[0].boxes.id.cpu().numpy().astype(int)  # Shape: (N,)
    
    # Initialize smoothed keypoints array
    smoothed_keypoints = np.zeros_like(current_keypoints)
    
    # Clean up dictionary: remove IDs that haven't been seen in a while
    active_ids = set(tracking_ids)
    ids_to_remove = [pid for pid in previous_keypoints_dict.keys() if pid not in active_ids]
    for pid in ids_to_remove:
        del previous_keypoints_dict[pid]
    
    # Apply smoothing for each detected person
    for idx, person_id in enumerate(tracking_ids):
        current_kp = current_keypoints[idx]  # Shape: (17, 3)
        
        if person_id in previous_keypoints_dict:
            # Person seen before - apply exponential smoothing
            previous_kp = previous_keypoints_dict[person_id]
            
            # Smooth only x and y coordinates (columns 0 and 1)
            smoothed_xy = alpha * current_kp[:, :2] + (1 - alpha) * previous_kp[:, :2]
            
            # Keep current confidence values (column 2)
            smoothed_conf = current_kp[:, 2:3]
            
            # Combine smoothed x, y with current confidence
            smoothed_kp = np.concatenate([smoothed_xy, smoothed_conf], axis=1)
        else:
            # New person ID - initialize with current keypoints (no smoothing)
            smoothed_kp = current_kp.copy()
        
        # Store smoothed keypoints for this person
        smoothed_keypoints[idx] = smoothed_kp
        previous_keypoints_dict[person_id] = smoothed_kp
    
    return smoothed_keypoints, previous_keypoints_dict

def extract_keypoints(results, smoothed_keypoints=None):
    """
    Extract keypoints from YOLOv8 results.
    
    Args:
        results: YOLO inference results
        smoothed_keypoints: Optional pre-smoothed keypoints to use instead of raw data
    
    Returns:
        List of keypoints for each detected person, or None if no detections
    """
    # If smoothed keypoints are provided, use them
    if smoothed_keypoints is not None:
        return smoothed_keypoints
    
    # Otherwise, extract raw keypoints
    if results[0].keypoints is None:
        return None
    
    keypoints_data = results[0].keypoints.data.cpu().numpy()  # (num_persons, 17, 3)
    return keypoints_data

def calculate_keypoint_confidence(keypoints, conf_threshold=0.5):
    """
    Calculate average confidence of RULA-relevant keypoints for table manner analysis.

    Counts the 11 keypoints used for sitting posture RULA + leg analysis:
    - Nose (0): for neck angle
    - Shoulders (5, 6): for upper arm and trunk
    - Elbows (7, 8): for lower arm angle
    - Wrists (9, 10): for wrist angle
    - Hips (11, 12): for trunk angle
    - Knees (13, 14): for leg posture detection (raised legs, cross-legged)

    Args:
        keypoints: Keypoint array (17, 3) where [:, 2] is confidence
        conf_threshold: Minimum confidence to consider a keypoint as detected

    Returns:
        Dictionary with confidence statistics
    """
    # Define RULA-relevant keypoints for table manner (sitting posture + legs)
    RULA_KEYPOINT_INDICES = [0, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]  # 11 keypoints total

    if keypoints is None or len(keypoints) == 0:
        return {
            "average_confidence": 0.0,
            "detected_keypoints": 0,
            "total_keypoints": 11
        }

    # Extract confidence values only for RULA-relevant keypoints
    rula_confidences = keypoints[RULA_KEYPOINT_INDICES, 2]

    # Count keypoints above threshold
    detected_count = np.sum(rula_confidences > conf_threshold)

    # Calculate average confidence for detected keypoints
    valid_confidences = rula_confidences[rula_confidences > conf_threshold]
    avg_confidence = float(np.mean(valid_confidences)) if len(valid_confidences) > 0 else 0.0

    return {
        "average_confidence": round(avg_confidence * 100, 1),  # Convert to percentage
        "detected_keypoints": int(detected_count),
        "total_keypoints": 11
    }

# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

def draw_pose_and_rula(frame, keypoints, conf_threshold=0.5, debug=False, draw_overlay=False):
    """
    Draw keypoints, calculate angles, and optionally display RULA scores on the frame.
    
    Args:
        frame: OpenCV image frame
        keypoints: Keypoints array for detected persons
        conf_threshold: Confidence threshold for drawing keypoints
        debug: If True, show additional debug information
        draw_overlay: If True, draw RULA scores on frame (default False, send to frontend instead)
    
    Returns:
        Tuple of (frame with drawn keypoints and angles, rula_result dict or None)
    """
    # COCO indices for keypoints
    nose = 0
    left_shoulder, left_elbow, left_wrist = 5, 7, 9
    right_shoulder, right_elbow, right_wrist = 6, 8, 10
    left_hip, right_hip = 11, 12
    
    keypoint_radius = 5
    keypoint_color = (0, 0, 255)  # Red for keypoints
    line_color = (0, 255, 0)      # Green for lines
    text_color = (255, 0, 0)      # Blue for text
    
    # Initialize angle storage for RULA calculation
    rula_angles = {}
    rula_result_to_return = None  # Store RULA result to return
    
    # Process each detected person
    for person_idx, person_kps in enumerate(keypoints):
        # Process left arm
        left_sh = person_kps[left_shoulder]
        left_el = person_kps[left_elbow]
        left_wr = person_kps[left_wrist]
        
        if left_sh[2] > conf_threshold and left_el[2] > conf_threshold and left_wr[2] > conf_threshold:
            # Draw keypoints
            cv2.circle(frame, (int(left_sh[0]), int(left_sh[1])), keypoint_radius, keypoint_color, -1)
            cv2.circle(frame, (int(left_el[0]), int(left_el[1])), keypoint_radius, keypoint_color, -1)
            cv2.circle(frame, (int(left_wr[0]), int(left_wr[1])), keypoint_radius, keypoint_color, -1)
            
            # Draw lines connecting the points
            cv2.line(frame, (int(left_sh[0]), int(left_sh[1])), 
                     (int(left_el[0]), int(left_el[1])), line_color, 2)
            cv2.line(frame, (int(left_el[0]), int(left_el[1])), 
                     (int(left_wr[0]), int(left_wr[1])), line_color, 2)
            
            # Calculate and display left elbow angle
            left_angle = calculate_angle(
                (left_sh[0], left_sh[1]),
                (left_el[0], left_el[1]),
                (left_wr[0], left_wr[1])
            )
            
            text = f"L Elbow: {left_angle:.1f}°"
            cv2.putText(frame, text, (int(left_el[0]) - 50, int(left_el[1]) - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)
        
        # Process right arm
        right_sh = person_kps[right_shoulder]
        right_el = person_kps[right_elbow]
        right_wr = person_kps[right_wrist]
        
        if right_sh[2] > conf_threshold and right_el[2] > conf_threshold and right_wr[2] > conf_threshold:
            # Draw keypoints
            cv2.circle(frame, (int(right_sh[0]), int(right_sh[1])), keypoint_radius, keypoint_color, -1)
            cv2.circle(frame, (int(right_el[0]), int(right_el[1])), keypoint_radius, keypoint_color, -1)
            cv2.circle(frame, (int(right_wr[0]), int(right_wr[1])), keypoint_radius, keypoint_color, -1)
            
            # Draw lines connecting the points
            cv2.line(frame, (int(right_sh[0]), int(right_sh[1])), 
                     (int(right_el[0]), int(right_el[1])), line_color, 2)
            cv2.line(frame, (int(right_el[0]), int(right_el[1])), 
                     (int(right_wr[0]), int(right_wr[1])), line_color, 2)
            
            # Calculate and display right elbow angle
            right_angle = calculate_angle(
                (right_sh[0], right_sh[1]),
                (right_el[0], right_el[1]),
                (right_wr[0], right_wr[1])
            )
            
            text = f"R Elbow: {right_angle:.1f}°"
            cv2.putText(frame, text, (int(right_el[0]) - 50, int(right_el[1]) - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)
            
            # Store for RULA
            rula_angles['lower_arm'] = right_angle
        
        # Get trunk vector and body centers
        nose_kp = person_kps[nose]
        left_sh_kp = person_kps[left_shoulder]
        right_sh_kp = person_kps[right_shoulder]
        left_hp_kp = person_kps[left_hip]
        right_hp_kp = person_kps[right_hip]
        
        # Calculate center points for trunk
        shoulder_center = None
        hip_center = None
        
        torso_threshold = 0.2
        if (left_sh_kp[2] > conf_threshold and right_sh_kp[2] > conf_threshold and
            left_hp_kp[2] > torso_threshold and right_hp_kp[2] > torso_threshold):
            shoulder_center = calculate_center_point(left_sh_kp, right_sh_kp)
            hip_center = calculate_center_point(left_hp_kp, right_hp_kp)
        
        # UPPER ARM ANGLE (RULA Group A)
        right_sh = person_kps[right_shoulder]
        right_el_kp = person_kps[right_elbow]
        right_wr = person_kps[right_wrist]
        
        upper_arm_conf_threshold = 0.5
        upper_arm_angle = None
        is_arm_supported = False
        is_abducted = False
        
        if (right_sh[2] > upper_arm_conf_threshold and 
            right_el_kp[2] > upper_arm_conf_threshold):
            
            # Calculate upper arm angle RELATIVE TO VERTICAL DOWN
            upper_arm_angle = calculate_upper_arm_flexion(
                (right_sh[0], right_sh[1]),
                (right_el_kp[0], right_el_kp[1])
            )
            
            # Detect arm support
            if 'lower_arm' in rula_angles and right_wr[2] > upper_arm_conf_threshold:
                lower_arm_angle_val = rula_angles['lower_arm']
                wrist_below_elbow = right_wr[1] > right_el_kp[1] - 30
                is_arm_supported = (75 <= lower_arm_angle_val <= 115) and wrist_below_elbow
            
            # Detect abduction
            shoulder_to_elbow_x = abs(right_el_kp[0] - right_sh[0])
            is_abducted = shoulder_to_elbow_x > 60
            
            # Draw upper arm line (blue)
            cv2.line(frame, 
                    (int(right_sh[0]), int(right_sh[1])),
                    (int(right_el_kp[0]), int(right_el_kp[1])),
                    (255, 128, 0), 3)
            
            # Draw vertical reference line
            vertical_ref = (right_sh[0], right_sh[1] - 100)
            cv2.line(frame,
                    (int(right_sh[0]), int(right_sh[1])),
                    (int(vertical_ref[0]), int(vertical_ref[1])),
                    (180, 180, 180), 1)
            
            # Display upper arm angle
            upper_arm_text = f"Upper Arm: {upper_arm_angle:.1f}°"
            cv2.putText(frame, upper_arm_text,
                       (int(right_sh[0]) + 15, int(right_sh[1]) - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 128, 0), 2)
            
            # Store for RULA
            rula_angles['upper_arm'] = upper_arm_angle
            rula_angles['is_arm_supported'] = is_arm_supported
            rula_angles['is_abducted'] = is_abducted
        
        # WRIST ANGLE (proxy): evaluate both sides and choose best visible side
        right_wr_kp = person_kps[right_wrist]
        left_wr_kp = person_kps[left_wrist]
        
        wrist_conf_threshold = 0.5
        wrist_candidates = []

        if left_el[2] > wrist_conf_threshold and left_wr_kp[2] > wrist_conf_threshold:
            left_wrist_angle = calculate_wrist_proxy_angle(
                (left_el[0], left_el[1]),
                (left_wr_kp[0], left_wr_kp[1])
            )
            if left_wrist_angle is not None:
                left_conf = float((left_el[2] + left_wr_kp[2]) / 2.0)
                wrist_candidates.append((left_wrist_angle, left_conf, 'L', left_wr_kp))

                # Draw forearm and label
                cv2.line(frame,
                        (int(left_el[0]), int(left_el[1])),
                        (int(left_wr_kp[0]), int(left_wr_kp[1])),
                        (0, 200, 0), 2)
                cv2.putText(frame, f"Wrist: {left_wrist_angle:.1f}°",
                           (int(left_wr_kp[0]) - 120, int(left_wr_kp[1]) + 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 220), 1)

        if right_el_kp[2] > wrist_conf_threshold and right_wr_kp[2] > wrist_conf_threshold:
            right_wrist_angle = calculate_wrist_proxy_angle(
                (right_el_kp[0], right_el_kp[1]),
                (right_wr_kp[0], right_wr_kp[1])
            )
            if right_wrist_angle is not None:
                right_conf = float((right_el_kp[2] + right_wr_kp[2]) / 2.0)
                wrist_candidates.append((right_wrist_angle, right_conf, 'R', right_wr_kp))

                # Draw forearm and label
                cv2.line(frame,
                        (int(right_el_kp[0]), int(right_el_kp[1])),
                        (int(right_wr_kp[0]), int(right_wr_kp[1])),
                        (0, 255, 0), 2)
                cv2.putText(frame, f"Wrist: {right_wrist_angle:.1f}°",
                           (int(right_wr_kp[0]) + 10, int(right_wr_kp[1]) + 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 220), 1)

        if wrist_candidates:
            # Prefer the side with better confidence; use larger angle as tie-breaker.
            selected_wrist_angle, _, _, _ = max(
                wrist_candidates,
                key=lambda x: (x[1], x[0])
            )

            rula_angles['wrist'] = selected_wrist_angle
        
        # NECK AND TRUNK ANGLES
        if (nose_kp[2] > conf_threshold and shoulder_center is not None and hip_center is not None):
            
            # Draw center points
            cv2.circle(frame, (int(shoulder_center[0]), int(shoulder_center[1])), 
                      4, (255, 255, 0), -1)
            cv2.circle(frame, (int(hip_center[0]), int(hip_center[1])), 
                      4, (255, 255, 0), -1)
            
            # Draw lines
            cv2.line(frame, (int(nose_kp[0]), int(nose_kp[1])),
                    (int(shoulder_center[0]), int(shoulder_center[1])), 
                    (255, 255, 0), 2)
            cv2.line(frame, (int(shoulder_center[0]), int(shoulder_center[1])),
                    (int(hip_center[0]), int(hip_center[1])), 
                    (255, 255, 0), 2)
            
            # Draw vertical reference for neck
            vertical_neck_ref = (shoulder_center[0], shoulder_center[1] - 80)
            cv2.line(frame,
                    (int(shoulder_center[0]), int(shoulder_center[1])),
                    (int(vertical_neck_ref[0]), int(vertical_neck_ref[1])),
                    (180, 180, 180), 1)
            
            # Calculate neck angle
            neck_angle = calculate_neck_angle(
                shoulder_center,
                (nose_kp[0], nose_kp[1])
            )
            
            # Display neck angle
            neck_text = f"Neck: {neck_angle:.1f}°"
            cv2.putText(frame, neck_text, 
                       (int(shoulder_center[0]) + 20, int(shoulder_center[1]) - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            
            # Store for RULA
            rula_angles['neck'] = neck_angle
            
            # Calculate trunk angle
            trunk_angle = calculate_trunk_angle(shoulder_center, hip_center)
            
            # Display trunk angle
            trunk_text = f"Trunk: {trunk_angle:.1f}°"
            cv2.putText(frame, trunk_text,
                       (int(hip_center[0]) + 20, int(hip_center[1]) + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)

            # Store for RULA
            rula_angles['trunk'] = trunk_angle

        # LEG DETECTION AND VISUALIZATION (for table manner analysis)
        left_knee_kp = person_kps[13]
        right_knee_kp = person_kps[14]
        stable_legs_score = score_legs(person_kps, conf_threshold=0.35)

        leg_threshold = 0.35  # Side-view tolerant threshold for partially occluded far leg

        # Color follows stable legs score only to avoid false red flashes.
        leg_color_stable = (0, 0, 255) if stable_legs_score == 2 else (0, 255, 0)

        # Draw left leg (hip to knee) with color-coding
        if left_hp_kp[2] > leg_threshold and left_knee_kp[2] > leg_threshold:
            leg_color = leg_color_stable
            cv2.circle(frame, (int(left_hp_kp[0]), int(left_hp_kp[1])),
                      keypoint_radius, leg_color, -1)
            cv2.circle(frame, (int(left_knee_kp[0]), int(left_knee_kp[1])),
                      keypoint_radius, leg_color, -1)
            cv2.line(frame, (int(left_hp_kp[0]), int(left_hp_kp[1])),
                    (int(left_knee_kp[0]), int(left_knee_kp[1])),
                    leg_color, 3)  # Thicker line for visibility

        # Draw right leg (hip to knee) with color-coding
        if right_hp_kp[2] > leg_threshold and right_knee_kp[2] > leg_threshold:
            leg_color = leg_color_stable
            cv2.circle(frame, (int(right_hp_kp[0]), int(right_hp_kp[1])),
                      keypoint_radius, leg_color, -1)
            cv2.circle(frame, (int(right_knee_kp[0]), int(right_knee_kp[1])),
                      keypoint_radius, leg_color, -1)
            cv2.line(frame, (int(right_hp_kp[0]), int(right_hp_kp[1])),
                    (int(right_knee_kp[0]), int(right_knee_kp[1])),
                    leg_color, 3)  # Thicker line for visibility

        # Draw ankles if visible (optional - often hidden under table)
        if len(person_kps) >= 17:
            left_ankle_kp = person_kps[15]
            right_ankle_kp = person_kps[16]

            # Draw left knee to ankle with same color coding
            if left_knee_kp[2] > leg_threshold and left_ankle_kp[2] > leg_threshold:
                leg_color = leg_color_stable
                cv2.circle(frame, (int(left_ankle_kp[0]), int(left_ankle_kp[1])),
                          keypoint_radius, leg_color, -1)
                cv2.line(frame, (int(left_knee_kp[0]), int(left_knee_kp[1])),
                        (int(left_ankle_kp[0]), int(left_ankle_kp[1])),
                        leg_color, 3)

            # Draw right knee to ankle with same color coding
            if right_knee_kp[2] > leg_threshold and right_ankle_kp[2] > leg_threshold:
                leg_color = leg_color_stable
                cv2.circle(frame, (int(right_ankle_kp[0]), int(right_ankle_kp[1])),
                          keypoint_radius, leg_color, -1)
                cv2.line(frame, (int(right_knee_kp[0]), int(right_knee_kp[1])),
                        (int(right_ankle_kp[0]), int(right_ankle_kp[1])),
                        leg_color, 3)

        # OFFICIAL RULA SCORING AND CLASSIFICATION
        required_angles = ['upper_arm', 'lower_arm', 'wrist']
        has_upper_body = all(angle_key in rula_angles for angle_key in required_angles)
        
        # Display RULA if we have upper body
        if has_upper_body:
            # Stabilize angle inputs before discrete RULA score mapping.
            rula_angles['upper_arm'] = smooth_angle_value('upper_arm', rula_angles['upper_arm'])
            rula_angles['lower_arm'] = smooth_angle_value('lower_arm', rula_angles['lower_arm'])
            rula_angles['wrist'] = smooth_angle_value('wrist', rula_angles['wrist'])

            # Use default neck and trunk values if not available
            neck_angle_val = rula_angles.get('neck', 5)
            trunk_angle_val = rula_angles.get('trunk', 0)

            # Smooth neck/trunk too to reduce jumping when upper body is mostly still.
            neck_angle_val = smooth_angle_value('neck', neck_angle_val)
            trunk_angle_val = smooth_angle_value('trunk', trunk_angle_val)
            
            # Get arm support and abduction status
            arm_supported = rula_angles.get('is_arm_supported', False)
            arm_abducted = rula_angles.get('is_abducted', False)
            
            # Calculate OFFICIAL RULA score
            rula_result = calculate_official_rula(
                rula_angles['upper_arm'],
                rula_angles['lower_arm'],
                rula_angles['wrist'],
                neck_angle_val,
                trunk_angle_val,
                person_kps,
                person_detected=True,
                is_arm_supported=arm_supported,
                is_abducted=arm_abducted,
                legs_score_override=stable_legs_score
            )
            
            # Store RULA result for JSON API
            # Calculate keypoint detection confidence
            confidence_stats = calculate_keypoint_confidence(person_kps)
            
            rula_result_to_return = {
                "detected": True,
                "upper_arm_score": rula_result['upper_arm_score'],
                "lower_arm_score": rula_result['lower_arm_score'],
                "wrist_score": rula_result['wrist_score'],
                "neck_score": rula_result['neck_score'],
                "trunk_score": rula_result['trunk_score'],
                "legs_score": rula_result['legs_score'],
                "score_a": rula_result['score_a'],
                "score_b": rula_result['score_b'],
                "final_score": rula_result['final_score'],
                "classification": rula_result['classification'],
                "color": rula_result['color'],
                "neck_flexion": rula_result['neck_flexion'],
                "confidence": confidence_stats,
                "fps": round(current_fps, 1)
            }
            
            # Optionally display RULA scores on video frame
            if draw_overlay:
                # Display OFFICIAL RULA scores on screen (bottom-left corner)
                frame_height = frame.shape[0]
                x_position = 10
                # Start from bottom and work upward
                y_start = frame_height - 240  # 240px from bottom for the entire box
                y_offset = y_start
                
                # Background rectangle for better readability
                cv2.rectangle(frame, (x_position - 5, y_start - 20), 
                             (x_position + 400, frame_height - 10), 
                             (0, 0, 0), -1)
                cv2.rectangle(frame, (x_position - 5, y_start - 20), 
                             (x_position + 400, frame_height - 10), 
                             (255, 255, 255), 2)
                
                # Title
                cv2.putText(frame, "OFFICIAL RULA ASSESSMENT", 
                           (x_position, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                y_offset += 30
                
                # Individual joint scores
                cv2.putText(frame, f"Upper Arm: {rula_result['upper_arm_score']}  " + 
                                  f"Lower Arm: {rula_result['lower_arm_score']}  " +
                                  f"Wrist: {rula_result['wrist_score']}", 
                           (x_position, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                y_offset += 25
                
                cv2.putText(frame, f"Neck: {rula_result['neck_score']}  " +
                                  f"Trunk: {rula_result['trunk_score']}  " +
                                  f"Legs: {rula_result['legs_score']}", 
                           (x_position, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                y_offset += 30
                
                # Group scores
                cv2.putText(frame, f"Score A (Table A): {rula_result['score_a']}", 
                           (x_position, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.55, (100, 200, 255), 1)
                y_offset += 25
                
                cv2.putText(frame, f"Score B (Table B): {rula_result['score_b']}", 
                           (x_position, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.55, (100, 200, 255), 1)
                y_offset += 30
                
                # Final RULA score
                cv2.putText(frame, f"FINAL RULA SCORE: {rula_result['final_score']} / 7", 
                           (x_position, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                y_offset += 35
                
                # Risk classification with color coding
                classification_text = f"{rula_result['classification']}"
                cv2.putText(frame, classification_text, 
                           (x_position, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.65, rula_result['color'], 2)
    
    return frame, rula_result_to_return

# ============================================================================
# FLASK VIDEO STREAMING
# ============================================================================

def generate_frames():
    """
    Generator function that yields video frames with pose analysis.
    This function captures frames from the webcam, processes them with YOLO,
    and streams them to the client.
    
    PERFORMANCE OPTIMIZATIONS:
    - Frame skipping: Process every Nth frame to reduce CPU load
    - Resolution scaling: Downscale for inference, keep original for display
    - FPS limiting: Control frame rate to prevent overwhelming the client
    - JPEG compression: Reduce quality slightly for faster encoding/transmission
    """
    global cap, model, previous_keypoints_dict, last_inference_result, last_rula_data, current_fps
    
    frame_count = 0
    fps_update_interval = 1.0  # Update FPS every 1 second
    fps_frame_count = 0
    fps_last_update = time.time()
    
    while True:
        if cap is None or not cap.isOpened():
            time.sleep(0.05)
            continue
            
        success, frame = cap.read()
        
        if not success:
            break
        
        # Calculate actual FPS
        fps_frame_count += 1
        fps_current_time = time.time()
        fps_elapsed = fps_current_time - fps_last_update
        if fps_elapsed >= fps_update_interval:
            current_fps = fps_frame_count / fps_elapsed
            fps_frame_count = 0
            fps_last_update = fps_current_time
        
        try:
            # OPTIMIZATION: Frame skipping - only process every Nth frame
            if frame_count % FRAME_SKIP == 0:
                # Get original frame dimensions
                orig_height, orig_width = frame.shape[:2]
                
                # OPTIMIZATION: Downscale frame for inference (faster processing)
                scale_factor = INFERENCE_SIZE / orig_width
                inference_height = int(orig_height * scale_factor)
                inference_frame = cv2.resize(frame, (INFERENCE_SIZE, inference_height))
                
                # Run YOLOv8-Pose inference WITHOUT tracking (faster on CPU)
                results = model.predict(inference_frame, verbose=False, half=False, max_det=1)
                
                # Apply simple exponential smoothing (no tracking IDs needed)
                smoothed_keypoints = None
                if len(results) > 0 and results[0].keypoints is not None:
                    # Keep full keypoint format (x, y, confidence) for downstream RULA logic
                    current_kp = results[0].keypoints.data.cpu().numpy()
                    if len(previous_keypoints_dict) > 0 and 'last' in previous_keypoints_dict:
                        prev_kp = previous_keypoints_dict['last']
                        smoothed_keypoints = 0.55 * current_kp + 0.45 * prev_kp
                    else:
                        smoothed_keypoints = current_kp
                    previous_keypoints_dict['last'] = current_kp
                
                # Extract keypoints (use smoothed)
                keypoints = smoothed_keypoints if smoothed_keypoints is not None else None
                
                # Scale keypoints back to original frame size
                if keypoints is not None:
                    keypoints_scaled = keypoints.copy()
                    keypoints_scaled[:, :, 0] *= (orig_width / INFERENCE_SIZE)  # Scale x coordinates
                    keypoints_scaled[:, :, 1] *= (orig_height / inference_height)  # Scale y coordinates
                    last_inference_result = keypoints_scaled
                else:
                    last_inference_result = None
            
            # Draw pose and RULA analysis using cached result (smooth for skipped frames)
            if last_inference_result is not None:
                frame, rula_data = draw_pose_and_rula(frame, last_inference_result, conf_threshold=0.5, draw_overlay=False)
                # Store RULA data globally for JSON API endpoint
                if rula_data is not None:
                    last_rula_data = rula_data
            else:
                # No person detected - clear RULA data
                last_rula_data = {"detected": False, "message": "No person detected"}
                # Display message if no person detected (bottom-left)
                frame_height = frame.shape[0]
                cv2.putText(frame, "No person detected", (20, frame_height - 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        except Exception as e:
            # Minimal error output to avoid console spam (bottom-left)
            frame_height = frame.shape[0]
            cv2.putText(frame, "Processing error", (20, frame_height - 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # OPTIMIZATION: Encode frame as JPEG with reduced quality for faster transmission
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
        ret, buffer = cv2.imencode('.jpg', frame, encode_param)
        if not ret:
            continue
            
        frame_bytes = buffer.tobytes()
        frame_count += 1
        
        # Yield frame in multipart format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# ============================================================================
# FLASK ROUTES
# ============================================================================

@app.route('/')
def index():
    """Root endpoint - API information."""
    return jsonify({
        "name": "Posture RULA Analysis API",
        "version": "1.0.0",
        "endpoints": {
            "/": "API information",
            "/video": "Video stream with pose analysis",
            "/rula_data": "Latest RULA assessment data (JSON)",
            "/status": "System status",
            "/evaluation/record": "POST ground-truth label (and optional predicted label)",
            "/evaluation/result": "Evaluation metrics and confusion matrix",
            "/evaluation/reset": "Reset evaluation counters"
        }
    })

@app.route('/video')
def video():
    """Video streaming route."""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def status():
    """Check system status."""
    global cap, model, camera_state, camera_error
    return jsonify({
        "model_loaded": model is not None,
        "camera_active": cap is not None and cap.isOpened(),
        "camera_state": camera_state,
        "camera_error": camera_error
    })

@app.route('/rula_data')
def rula_data():
    """Get latest RULA assessment data as JSON."""
    global last_rula_data
    if last_rula_data is None:
        return jsonify({
            "detected": False,
            "message": "No person detected or waiting for analysis"
        })
    return jsonify(last_rula_data)

@app.route('/evaluation/record', methods=['POST'])
def evaluation_record():
    """Record an evaluation sample into the confusion matrix."""
    global last_rula_data

    payload = request.get_json(silent=True) or {}
    true_label_raw = payload.get("true_label")
    predicted_label_raw = payload.get("predicted_label")

    true_label_id = _normalize_eval_label(true_label_raw)
    if true_label_id is None:
        return jsonify({
            "status": "error",
            "message": "true_label must be 1-4 or a valid label string"
        }), 400

    if predicted_label_raw is None:
        if last_rula_data is None or not last_rula_data.get("detected"):
            return jsonify({
                "status": "error",
                "message": "No detected posture. Provide predicted_label or wait for detection."
            }), 409
        predicted_label_id = _label_from_rula_classification(last_rula_data.get("classification"))
    else:
        predicted_label_id = _normalize_eval_label(predicted_label_raw)

    if predicted_label_id is None:
        return jsonify({
            "status": "error",
            "message": "predicted_label must be 1-4 or a valid label string"
        }), 400

    with evaluation_lock:
        evaluation_confusion[true_label_id - 1][predicted_label_id - 1] += 1

    return jsonify({
        "status": "success",
        "true_label": {
            "id": true_label_id,
            "label": EVAL_LABELS[true_label_id]
        },
        "predicted_label": {
            "id": predicted_label_id,
            "label": EVAL_LABELS[predicted_label_id]
        }
    })

@app.route('/evaluation/result')
def evaluation_result():
    """Return current evaluation metrics and confusion matrix."""
    with evaluation_lock:
        matrix = [row[:] for row in evaluation_confusion]

    metrics = _compute_metrics_from_confusion(matrix)
    return jsonify({
        "labels": EVAL_LABELS,
        "confusion_matrix": matrix,
        "metrics": metrics
    })

@app.route('/evaluation/reset', methods=['POST'])
def evaluation_reset():
    """Reset confusion matrix counters."""
    with evaluation_lock:
        for i in range(4):
            for j in range(4):
                evaluation_confusion[i][j] = 0

    return jsonify({
        "status": "success",
        "message": "Evaluation counters reset"
    })

@app.route('/start', methods=['POST'])
def start_camera():
    """Start the webcam."""
    global model, camera_state, camera_error, camera_start_thread, previous_keypoints_dict, last_inference_result

    if model is None:
        return jsonify({
            'status': 'error',
            'message': 'Model is not loaded yet'
        }), 503

    with camera_lock:
        if camera_state == "active" and cap is not None and cap.isOpened():
            return jsonify({
                'status': 'already_active',
                'message': 'Camera is already running'
            })

        if camera_state == "starting":
            return jsonify({
                'status': 'starting',
                'message': 'Camera is starting'
            }), 202

        camera_state = "starting"
        camera_error = None
        previous_keypoints_dict = {}
        last_inference_result = None
        reset_stability_state()
        camera_start_thread = threading.Thread(target=_open_camera_async, daemon=True)
        camera_start_thread.start()

    return jsonify({
        'status': 'starting',
        'message': 'Camera start initiated'
    }), 202

@app.route('/stop', methods=['POST'])
def stop_camera():
    """Stop the webcam and release the camera resource."""
    global cap, last_rula_data, camera_state, camera_error, previous_keypoints_dict, last_inference_result

    local_cap = None
    with camera_lock:
        if cap is None and camera_state in ("inactive", "error"):
            camera_state = "inactive"
            camera_error = None
            return jsonify({
                'status': 'already_inactive',
                'message': 'Camera is not running'
            })

        local_cap = cap
        cap = None
        camera_state = "inactive"
        camera_error = None

    try:
        if local_cap is not None:
            local_cap.release()  # This turns off the camera light

        # Clear RULA data when camera stops
        last_rula_data = None
        previous_keypoints_dict = {}
        last_inference_result = None
        reset_stability_state()

        print("✓ Webcam stopped and released")
        return jsonify({
            'status': 'success',
            'message': 'Camera stopped successfully'
        })
    except Exception as e:
        print(f"✗ Error stopping camera: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ============================================================================
# APPLICATION INITIALIZATION AND CLEANUP
# ============================================================================

def initialize_app():
    """Initialize the application - load model only. Camera will be started via /start endpoint."""
    global model, cap, previous_keypoints_dict

    print("\n" + "="*60)
    print("  Posture RULA Analysis System - Flask Backend")
    print("="*60)

    # Load YOLO model
    print("\n[1/1] Loading YOLOv8-Pose model...")
    model = load_pose_model("yolov8n-pose.pt")
    if model is None:
        print("✗ Failed to load model. Exiting.")
        return False

    # Camera will be opened on-demand via /start endpoint
    print("✓ Model loaded successfully")
    print("  ℹ  Camera will be started when you click 'Aktifkan Webcam' in the frontend")

    # Initialize tracking dictionary
    previous_keypoints_dict = {}

    print(f"\nOptimization settings:")
    print(f"  - Frame skip: {FRAME_SKIP} (process every {FRAME_SKIP}{'nd' if FRAME_SKIP == 2 else 'rd' if FRAME_SKIP == 3 else 'th'} frame)")
    print(f"  - Inference size: {INFERENCE_SIZE}px width")
    print(f"  - Target FPS: {TARGET_FPS}")
    print(f"  - JPEG quality: {JPEG_QUALITY}%")

    print("\n" + "="*60)
    print("  System Ready!")
    print("="*60)
    print("\nFlask server starting...")
    print("API Endpoints:")
    print("  - POST /start  : Start camera")
    print("  - POST /stop   : Stop camera and turn off light")
    print("  - GET  /video  : Video stream (after starting camera)")
    print("  - GET  /status : Check system status")
    print("  - GET  /rula_data : Get latest RULA assessment")
    print("\nPress Ctrl+C to stop the server\n")

    return True

def cleanup():
    """Cleanup resources on shutdown."""
    global cap
    if cap is not None:
        cap.release()
        print("\n✓ Webcam released")

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Initialize the application
    if initialize_app():
        try:
            # Run Flask app
            app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
        except KeyboardInterrupt:
            print("\n\nShutting down...")
        finally:
            cleanup()
    else:
        print("\nFailed to initialize application.")
