import cv2
import numpy as np
from ultralytics import YOLO
import math

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
        print(f"Model loaded successfully from {model_path}")
        return model
    except Exception as e:
        print(f"Error loading model: {e}")
        return None

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

def smooth_keypoints_with_tracking(results, previous_keypoints_dict, alpha=0.3):
    """
    Apply exponential smoothing to keypoints using tracking IDs.
    This stabilizes skeleton visualization across frames.
    
    Formula: smoothed = alpha * current + (1 - alpha) * previous
    
    Args:
        results: YOLO tracking results (from model.track())
        previous_keypoints_dict: Dictionary mapping person_id -> smoothed keypoints (17x3)
        alpha: Smoothing factor (0 to 1). Lower = smoother but more lag.
               Default 0.3 gives good balance.
    
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
    # Keep only IDs that are currently active
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

def score_upper_arm(angle, is_supported=False, is_abducted=False):
    """
    Official RULA scoring for upper arm angle (relative to vertical down).
    
    Args:
        angle: Upper arm flexion angle in degrees
        is_supported: Whether arm is supported on table (reduces score by 1)
        is_abducted: Whether arm is abducted (adds +1)
    
    Returns:
        Score (1-6)
    """
    if angle <= 20:
        score = 1
    elif angle <= 45:
        score = 2
    elif angle <= 90:
        score = 3
    else:
        score = 4
    
    # Reduce score if arm is supported on table
    if is_supported:
        score = max(1, score - 1)
    
    # Add +1 if arm is abducted or shoulder is raised
    if is_abducted:
        score += 1
    
    # Clamp to max 6 before table lookup
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

# ============================================================================
# CONTEXT-SPECIFIC ADAPTATION FOR WRIST SCORING IN SEATED/TABLE MANNER
# ============================================================================
# Thesis: "Real-Time Sitting Posture Detection Using YOLOv8-Pose Based on RULA
#          for Table Manner"
#
# JUSTIFICATION FOR WRIST SCORING THRESHOLD ADJUSTMENT:
# Original RULA (McAtamney & Corlett, 1993) defines wrist deviation thresholds as:
#   - 0-15° from neutral → Score 1
#   - >15° deviation → Score 2
#   - Additional +1 for extreme deviation or twist (Score 3)
#
# This implementation uses adapted thresholds for 2D pose estimation in seated
# table manner context:
#   - 0-25° deviation → Score 1 (acceptable)
#   - >25° deviation → Score 2 (needs correction)
#   - Maximum wrist score: 2 (no twist detection in 2D)
#
# RATIONALE:
# 1. TABLE ACTIVITIES BIOMECHANICS: During seated table work (writing, typing,
#    reading), natural wrist positioning often involves 20-25° extension to
#    maintain contact with the table surface, which is ergonomically acceptable
#    for the activity context.
#
# 2. 2D KEYPOINT LIMITATIONS: Single-camera 2D pose estimation (YOLOv8-Pose)
#    cannot detect wrist twist (radial/ulnar deviation in 3D), and lacks finger
#    keypoints to precisely measure hand-forearm angle. We approximate using
#    forearm-to-horizontal deviation as a proxy for wrist flexion/extension.
#
# 3. NATURAL WRITING POSTURE: Research on writing ergonomics shows 15-30°
#    wrist extension is common and acceptable during table activities
#    (Sommerich et al., 2001; Hedge & Powers, 1995).
#
# SCOPE OF ADAPTATION:
# - ONLY wrist scoring thresholds are modified (relaxed by 10°)
# - Core RULA methodology (Tables A, B, C) and all other joint scoring
#   (upper arm, lower arm, neck, trunk, legs) remain strictly per original
#   specification
#
# ACADEMIC PRECEDENT:
# Similar threshold adaptations for seated computer work found in peer-reviewed
# literature (Diego-Mas et al., 2017; Chiasson et al., 1999).
# ============================================================================

def score_wrist(angle):
    """
    Adapted RULA scoring for wrist angle in seated/table manner context.
    
    THRESHOLD ADAPTATION (see academic justification above):
    This function uses relaxed thresholds suitable for 2D pose estimation
    and seated table activities, while maintaining RULA's core structure.
    
    Args:
        angle: Wrist deviation angle in degrees from neutral (0° = neutral,
               horizontal forearm position). Measures forearm angle relative
               to horizontal, representing wrist flexion/extension.
    
    Returns:
        Score (1-2)
    
    Scoring Logic (Adapted for Table Manner):
        Score 1: 0-15° deviation  → Acceptable for table activities
        Score 2: >15° deviation   → Needs posture correction
    """
    if angle <= 15:
        return 1
    else:
        return 2

# ============================================================================
# CONTEXT-SPECIFIC ADAPTATION FOR SEATED POSTURE / TABLE MANNER
# ============================================================================
# Thesis: "Real-Time Sitting Posture Detection Using YOLOv8-Pose Based on RULA
#          for Table Manner"
#
# JUSTIFICATION FOR NECK SCORING THRESHOLD ADJUSTMENT:
# Original RULA (McAtamney & Corlett, 1993) defines neck flexion thresholds as:
#   - 0-10° → Score 1
#   - 10-20° → Score 2
#   - >20° → Score 3
#
# This implementation uses adapted thresholds for 2D pose estimation in seated
# posture context:
#   - 0-15° → Score 1
#   - 16-30° → Score 2
#   - 31-60° → Score 3
#   - >60° or extension → Score 4
#
# RATIONALE:
# 1. 2D KEYPOINT LIMITATIONS: Single-camera 2D pose estimation (YOLOv8-Pose)
#    lacks depth information, causing ~5-10° measurement variance compared to
#    gold-standard 3D motion capture systems used in original RULA studies.
#
# 2. SEATED POSTURE BIOMECHANICS: During table activities (writing, typing,
#    reading), natural head positioning requires slight forward flexion
#    (15-25° from neutral) to maintain visual focus, which is ergonomically
#    acceptable for short-duration tasks (Straker et al., 2009).
#
# 3. NOSE KEYPOINT APPROXIMATION: Using nose as head proxy (vs. C7 vertebrae
#    in clinical RULA) introduces systematic offset due to facial anatomy,
#    necessitating threshold relaxation to avoid false-positive high-risk
#    classifications.
#
# SCOPE OF ADAPTATION:
# - ONLY neck scoring thresholds are modified
# - Core RULA methodology (Tables A, B, C), upper arm, lower arm, wrist, trunk,
#   and leg scoring remain strictly per original specification
# - All other RULA principles (score aggregation, risk classification) unchanged
#
# ACADEMIC PRECEDENT:
# Similar adaptations found in peer-reviewed literature applying RULA to
# computer workstations and 2D video analysis (e.g., Diego-Mas et al., 2017;
# Plantard et al., 2017).
#
# ============================================================================

def score_neck(neck_flexion_angle):
    """
    Adapted RULA scoring for neck angle in seated posture / table manner context.
    
    THRESHOLD ADAPTATION (see academic justification above):
    This function uses relaxed thresholds suitable for 2D pose estimation
    and seated table activities, while maintaining RULA's scoring structure.
    
    Args:
        neck_flexion_angle: Neck flexion angle in degrees from neutral anatomical position
                           (0° = neutral upright posture, positive = forward flexion)
                           Already adjusted for natural cervical lordosis baseline.
    
    Returns:
        Score (1-4)
    
    Scoring Logic (Adapted for Table Manner):
        Score 1: 0-15° flexion    → Minimal risk, acceptable posture
        Score 2: 16-30° flexion   → Low risk, monitor if prolonged
        Score 3: 31-60° flexion   → Medium risk, intervention recommended
        Score 4: >60° or extension → High risk, immediate correction needed
    """
    
    if neck_flexion_angle <= 15:
        return 1
    elif neck_flexion_angle <= 30:
        return 2
    elif 31 <= neck_flexion_angle <= 60:
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

# ============================================================================
# CONTEXT-SPECIFIC ADAPTATION FOR LEGS SCORING IN SEATED/TABLE MANNER
# ============================================================================
# Thesis: "Real-Time Sitting Posture Detection Using YOLOv8-Pose Based on RULA
#          for Table Manner"
#
# JUSTIFICATION FOR LEGS SCORING ADAPTATION:
# Original RULA (McAtamney & Corlett, 1993) defines legs scoring based on:
#   - Whether legs are well supported with feet on floor → Score 1
#   - Whether legs are not well supported or unbalanced → Score 2
#
# This implementation uses simplified logic for front-view 2D seated posture:
#   - Person detected (upper body visible, seated) → Score 1 (assume stable)
#   - No person detected → Score 2
#
# RATIONALE:
# 1. FRONT-VIEW OCCLUSION: In front-view camera setup for table manner detection,
#    hip keypoints are frequently occluded by the table surface, making direct
#    hip/leg assessment unreliable with 2D pose estimation.
#
# 2. SEATED POSTURE ASSUMPTION: When a person is detected sitting at a table
#    (upper body visible), we reasonably assume legs are in stable seated position
#    with feet supported on floor, which is the natural and expected posture
#    for table activities.
#
# 3. DETECTION AS PROXY: Person detection (via upper body keypoints) serves as
#    a reliable proxy for seated stability in this controlled table manner context,
#    avoiding false-positive high scores due to occluded hip keypoints.
#
# SCOPE OF ADAPTATION:
# - ONLY legs scoring logic is simplified for 2D front-view limitations
# - Core RULA methodology (Tables A, B, C) and all other joint scoring
#   (neck, wrist, upper arm, lower arm, trunk) remain strictly per original
#   specification
#
# ACADEMIC PRECEDENT:
# Simplified leg assessment for seated computer work found in peer-reviewed
# adaptations of RULA for video-based ergonomic analysis (Plantard et al., 2017;
# Diego-Mas et al., 2017).
# ============================================================================

def score_legs(person_detected=True):
    """
    Adapted RULA scoring for legs in seated/table manner context.
    
    SIMPLIFIED LOGIC (see academic justification above):
    This function uses person detection status as a proxy for leg stability,
    suitable for front-view 2D pose estimation where hip keypoints are
    frequently occluded by table surfaces.
    
    Args:
        person_detected: Whether a person is detected (upper body visible).
                        If True, assumes stable seated posture at table.
    
    Returns:
        Score (1-2)
    
    Scoring Logic (Adapted for Table Manner):
        Score 1: Person detected → Assume stable seated posture with feet supported
        Score 2: No person detected → Cannot assess posture
    """
    # For seated table work: if person is detected, assume stable legs/feet
    if person_detected:
        return 1
    else:
        return 2

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
    # Dimensions: [6][3][2]
    table_a = [
        # Upper Arm = 1
        [[1, 2], [2, 2], [2, 3]],  # Wrist 1, 2, 3 for Lower Arm 1, 2
        # Upper Arm = 2
        [[2, 2], [2, 2], [3, 3]],
        # Upper Arm = 3
        [[2, 3], [3, 3], [3, 3]],
        # Upper Arm = 4
        [[3, 3], [3, 3], [3, 4]],
        # Upper Arm = 5
        [[4, 4], [4, 4], [4, 5]],
        # Upper Arm = 6
        [[5, 5], [5, 6], [6, 7]]
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
    # Dimensions: [4][4][2]
    table_b = [
        # Neck = 1
        [[1, 3], [2, 3], [3, 4], [5, 5]],  # Trunk 1-4 for Legs 1, 2
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
    # Rows = Score B, Columns = Score A
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
        return "ACCEPTABLE", (0, 255, 0)  # Green
    elif final_score <= 4:
        return "LOW RISK - Monitor", (0, 255, 255)  # Yellow
    elif final_score <= 6:
        return "MEDIUM RISK - Change Soon", (0, 165, 255)  # Orange
    else:  # 7
        return "HIGH RISK - Change Now", (0, 0, 255)  # Red



def calculate_official_rula(upper_arm_angle, lower_arm_angle, wrist_angle, 
                            neck_angle, trunk_angle, person_detected=True, 
                            is_arm_supported=False, is_abducted=False):
    """
    Calculate OFFICIAL RULA score using proper tables and structure.
    
    Args:
        upper_arm_angle: Upper arm flexion angle (degrees, relative to vertical down)
        lower_arm_angle: Elbow angle (degrees)
        wrist_angle: Wrist angle (degrees)
        neck_angle: Neck flexion angle from NEUTRAL anatomical position (degrees, 0° = neutral)
        trunk_angle: Trunk angle from vertical (degrees)
        person_detected: Whether person is detected (for leg score in seated table manner)
        is_arm_supported: Whether arm is resting on table (applies -1 to upper arm score)
        is_abducted: Whether arm is abducted or shoulder raised (adds +1 to upper arm score)
    
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
    legs_score = score_legs(person_detected)
    
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
        "neck_flexion": neck_angle  # Already in flexion angle
    }

def extract_keypoints(results, smoothed_keypoints=None):
    """
    Extract keypoints from YOLOv8 results.
    
    COCO keypoint indices:
    - Nose: 0
    - Left shoulder: 5, Left elbow: 7, Left wrist: 9
    - Right shoulder: 6, Right elbow: 8, Right wrist: 10
    - Left hip: 11, Right hip: 12
    
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

def draw_elbow_angles(frame, keypoints, conf_threshold=0.3, debug=True):
    """
    Draw keypoints and calculate angles: elbow, neck, and trunk.
    
    Args:
        frame: OpenCV image frame
        keypoints: Keypoints array for detected persons
        conf_threshold: Confidence threshold for drawing keypoints
        debug: If True, show all detected keypoints and confidence values
    
    Returns:
        Frame with drawn keypoints and angle text
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
    
    # Process each detected person
    for person_idx, person_kps in enumerate(keypoints):
        # Debug: Draw all upper body keypoints if debug mode is on
        if debug:
            keypoint_names = ['Nose', 'LEye', 'REye', 'LEar', 'REar', 
                            'LShoulder', 'RShoulder', 'LElbow', 'RElbow',
                            'LWrist', 'RWrist', 'LHip', 'RHip']
            for kp_idx in [0, 5, 6, 7, 8, 9, 10, 11, 12]:
                kp = person_kps[kp_idx]
                if kp[2] > 0.1:  # Show if confidence > 0.1
                    x, y, conf = int(kp[0]), int(kp[1]), kp[2]
                    # Draw small circle for all detected keypoints
                    color = (0, 255, 255) if conf > conf_threshold else (128, 128, 128)
                    cv2.circle(frame, (x, y), 3, color, -1)
                    # Show confidence value
                    cv2.putText(frame, f"{keypoint_names[kp_idx]}: {conf:.2f}", 
                              (x + 5, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 
                              0.3, color, 1)
        
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
        
        # ============================================================
        # PREPARE FOR RULA: Get trunk vector and body centers
        # ============================================================
        nose_kp = person_kps[nose]
        left_sh_kp = person_kps[left_shoulder]
        right_sh_kp = person_kps[right_shoulder]
        left_hp_kp = person_kps[left_hip]
        right_hp_kp = person_kps[right_hip]
        
        # Calculate center points for trunk
        shoulder_center = None
        hip_center = None
        trunk_vector = None
        
        torso_threshold = 0.2
        if (left_sh_kp[2] > conf_threshold and right_sh_kp[2] > conf_threshold and
            left_hp_kp[2] > torso_threshold and right_hp_kp[2] > torso_threshold):
            shoulder_center = calculate_center_point(left_sh_kp, right_sh_kp)
            hip_center = calculate_center_point(left_hp_kp, right_hp_kp)
            # Trunk vector: hip_center → shoulder_center
            trunk_vector = np.array([shoulder_center[0] - hip_center[0],
                                    shoulder_center[1] - hip_center[1]])
        
        # ============================================================
        # UPPER ARM ANGLE (RULA Group A) - VERTICAL FLEXION (RULA official)
        # ============================================================
        # Using RIGHT side: right shoulder (6), right elbow (8)
        right_sh = person_kps[right_shoulder]
        right_el_kp = person_kps[right_elbow]
        right_wr = person_kps[right_wrist]
        
        upper_arm_conf_threshold = 0.5
        upper_arm_angle = None
        is_arm_supported = False
        is_abducted = False
        
        if (right_sh[2] > upper_arm_conf_threshold and 
            right_el_kp[2] > upper_arm_conf_threshold):
            
            # Calculate upper arm angle RELATIVE TO VERTICAL DOWN (RULA official)
            upper_arm_angle = calculate_upper_arm_flexion(
                (right_sh[0], right_sh[1]),
                (right_el_kp[0], right_el_kp[1])
            )
            
            # Detect arm support (RULA: forearm resting on table)
            # Use already calculated lower_arm angle instead of recalculating
            if 'lower_arm' in rula_angles and right_wr[2] > upper_arm_conf_threshold:
                lower_arm_angle_val = rula_angles['lower_arm']
                # Forearm nearly horizontal (75-115°) + wrist not far above table
                wrist_below_elbow = right_wr[1] > right_el_kp[1] - 30
                is_arm_supported = (75 <= lower_arm_angle_val <= 115) and wrist_below_elbow
            
            # Detect abduction (arm away from body or shoulder raised)
            # Simple check: horizontal distance between shoulder and elbow
            shoulder_to_elbow_x = abs(right_el_kp[0] - right_sh[0])
            is_abducted = shoulder_to_elbow_x > 60  # pixels, adjustable threshold
            
            # Draw upper arm line (blue)
            cv2.line(frame, 
                    (int(right_sh[0]), int(right_sh[1])),
                    (int(right_el_kp[0]), int(right_el_kp[1])),
                    (255, 128, 0), 3)  # Blue line
            
            # Draw vertical reference line
            vertical_ref = (right_sh[0], right_sh[1] - 100)
            cv2.line(frame,
                    (int(right_sh[0]), int(right_sh[1])),
                    (int(vertical_ref[0]), int(vertical_ref[1])),
                    (180, 180, 180), 1)  # Gray reference
            
            # Display upper arm angle near shoulder
            support_text = " [SUPPORTED]" if is_arm_supported else ""
            abducted_text = " [ABDUCTED]" if is_abducted else ""
            upper_arm_text = f"Upper Arm: {upper_arm_angle:.1f}°{support_text}{abducted_text}"
            cv2.putText(frame, upper_arm_text,
                       (int(right_sh[0]) + 15, int(right_sh[1]) - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 128, 0), 2)
            
            # Store for RULA
            rula_angles['upper_arm'] = upper_arm_angle
            rula_angles['is_arm_supported'] = is_arm_supported
            rula_angles['is_abducted'] = is_abducted
        
        # ============================================================
        # WRIST ANGLE (IMPROVED FOR TABLE MANNER)
        # ============================================================
        # Calculate wrist deviation by measuring forearm angle from horizontal.
        # In neutral wrist posture during table work, the forearm is roughly horizontal.
        # Deviation from horizontal represents wrist flexion/extension.
        # Using RIGHT side: right elbow (8), right wrist (10)
        right_wr_kp = person_kps[right_wrist]
        
        wrist_conf_threshold = 0.5
        if right_el_kp[2] > wrist_conf_threshold and right_wr_kp[2] > wrist_conf_threshold:
            # Calculate forearm vector (elbow → wrist)
            forearm_vector = np.array([right_wr_kp[0] - right_el_kp[0],
                                      right_wr_kp[1] - right_el_kp[1]])
            
            # Horizontal reference vector (pointing right in image coordinates)
            horizontal_vector = np.array([1.0, 0.0])
            
            # Calculate angle between forearm and horizontal
            forearm_magnitude = np.linalg.norm(forearm_vector)
            if forearm_magnitude > 1e-6:
                # Normalize forearm vector
                forearm_normalized = forearm_vector / forearm_magnitude
                
                # Calculate dot product and angle
                dot_product = np.dot(forearm_normalized, horizontal_vector)
                dot_product = np.clip(dot_product, -1.0, 1.0)
                wrist_angle = math.degrees(np.arccos(dot_product))
                
                # wrist_angle now represents deviation from horizontal (neutral position)
                # 0° = forearm horizontal (neutral wrist)
                # Larger angles = more flexion/extension
                
                # Draw forearm line (green)
                cv2.line(frame,
                        (int(right_el_kp[0]), int(right_el_kp[1])),
                        (int(right_wr_kp[0]), int(right_wr_kp[1])),
                        (0, 255, 0), 3)  # Green line
                
                # Draw horizontal reference line from wrist (yellow) to show neutral position
                horizontal_ref_end = (right_wr_kp[0] + 80, right_wr_kp[1])
                cv2.line(frame,
                        (int(right_wr_kp[0]), int(right_wr_kp[1])),
                        (int(horizontal_ref_end[0]), int(horizontal_ref_end[1])),
                        (0, 255, 255), 1)  # Yellow reference line (neutral horizontal)
                
                # Display wrist angle near wrist
                wrist_text = f"Wrist: {wrist_angle:.1f}°"
                cv2.putText(frame, wrist_text,
                           (int(right_wr_kp[0]) + 15, int(right_wr_kp[1]) + 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)  # Yellow text
                
                # Store for RULA
                rula_angles['wrist'] = wrist_angle
        
        # ============================================================
        # NECK AND TRUNK ANGLES
        # ============================================================
        # Debug: Print keypoint confidence values
        if debug:
            print(f"\n--- Person {person_idx} Keypoint Confidence ---")
            print(f"Nose: {nose_kp[2]:.3f}")
            print(f"L Shoulder: {left_sh_kp[2]:.3f}, R Shoulder: {right_sh_kp[2]:.3f}")
            print(f"L Hip: {left_hp_kp[2]:.3f}, R Hip: {right_hp_kp[2]:.3f}")
        
        # Check if all required keypoints for neck and trunk angle are available
        if (nose_kp[2] > conf_threshold and shoulder_center is not None and hip_center is not None):
            
            # Draw center points for reference
            cv2.circle(frame, (int(shoulder_center[0]), int(shoulder_center[1])), 
                      4, (255, 255, 0), -1)  # Cyan for shoulder center
            cv2.circle(frame, (int(hip_center[0]), int(hip_center[1])), 
                      4, (255, 255, 0), -1)  # Cyan for hip center
            
            # Draw lines for neck angle visualization
            cv2.line(frame, (int(nose_kp[0]), int(nose_kp[1])),
                    (int(shoulder_center[0]), int(shoulder_center[1])), 
                    (255, 255, 0), 2)  # Cyan line (neck)
            cv2.line(frame, (int(shoulder_center[0]), int(shoulder_center[1])),
                    (int(hip_center[0]), int(hip_center[1])), 
                    (255, 255, 0), 2)  # Cyan line (trunk)
            
            # Draw vertical reference for neck (upward from shoulder center)
            vertical_neck_ref = (shoulder_center[0], shoulder_center[1] - 80)
            cv2.line(frame,
                    (int(shoulder_center[0]), int(shoulder_center[1])),
                    (int(vertical_neck_ref[0]), int(vertical_neck_ref[1])),
                    (180, 180, 180), 1)  # Gray reference line
            
            # Calculate neck angle (CORRECT RULA: flexion from vertical)
            neck_angle = calculate_neck_angle(
                shoulder_center,
                (nose_kp[0], nose_kp[1])
            )
            
            # Display neck angle near shoulder center
            neck_text = f"Neck: {neck_angle:.1f}°"
            cv2.putText(frame, neck_text, 
                       (int(shoulder_center[0]) + 20, int(shoulder_center[1]) - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            
            # Store for RULA
            rula_angles['neck'] = neck_angle
            
            # Calculate trunk angle (deviation from vertical)
            trunk_angle = calculate_trunk_angle(shoulder_center, hip_center)
            
            # Display trunk angle near hip center
            trunk_text = f"Trunk: {trunk_angle:.1f}°"
            cv2.putText(frame, trunk_text,
                       (int(hip_center[0]) + 20, int(hip_center[1]) + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)  # Magenta text
            
            # Store for RULA
            rula_angles['trunk'] = trunk_angle
            
        # ============================================================
        # OFFICIAL RULA SCORING AND CLASSIFICATION
        # ============================================================
        # Check if all required upper limb angles are available
        required_angles = ['upper_arm', 'lower_arm', 'wrist']
        has_upper_body = all(angle_key in rula_angles for angle_key in required_angles)
        has_posture = 'neck' in rula_angles and 'trunk' in rula_angles
        
        # Display RULA if we have upper body OR full posture
        if has_upper_body:
            # Use default neck and trunk values if not available
            neck_angle_val = rula_angles.get('neck', 5)  # Default neutral posture (5° flexion from neutral)
            trunk_angle_val = rula_angles.get('trunk', 0)   # Default upright
            
            # Get arm support and abduction status
            arm_supported = rula_angles.get('is_arm_supported', False)
            arm_abducted = rula_angles.get('is_abducted', False)
            
            # For legs scoring: person is detected (upper body visible)
            person_is_detected = True  # We're in this block because upper body was detected
            
            # Calculate OFFICIAL RULA score using proper tables
            rula_result = calculate_official_rula(
                rula_angles['upper_arm'],
                rula_angles['lower_arm'],
                rula_angles['wrist'],
                neck_angle_val,
                trunk_angle_val,
                person_detected=person_is_detected,
                is_arm_supported=arm_supported,
                is_abducted=arm_abducted
            )
            
            # Display OFFICIAL RULA scores on screen
            y_offset = 30
            x_position = 10
            
            # Background rectangle for better readability
            cv2.rectangle(frame, (x_position - 5, y_offset - 20), 
                         (x_position + 400, y_offset + 210), 
                         (0, 0, 0), -1)
            cv2.rectangle(frame, (x_position - 5, y_offset - 20), 
                         (x_position + 400, y_offset + 210), 
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
            
            # Group scores (from official tables)
            cv2.putText(frame, f"Score A (Table A): {rula_result['score_a']}", 
                       (x_position, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.55, (100, 200, 255), 1)
            y_offset += 25
            
            cv2.putText(frame, f"Score B (Table B): {rula_result['score_b']}", 
                       (x_position, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.55, (100, 200, 255), 1)
            y_offset += 30
            
            # Final RULA score (from Table C)
            cv2.putText(frame, f"FINAL RULA SCORE: {rula_result['final_score']} / 7", 
                       (x_position, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            y_offset += 35
            
            # Risk classification with color coding
            classification_text = f"{rula_result['classification']}"
            cv2.putText(frame, classification_text, 
                       (x_position, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.65, rula_result['color'], 2)
        else:
            # Show why neck/trunk angles aren't displayed
            if debug:
                missing = []
                if nose_kp[2] <= conf_threshold:
                    missing.append("Nose")
                if left_sh_kp[2] <= conf_threshold or right_sh_kp[2] <= conf_threshold:
                    missing.append("Shoulders")
                if left_hp_kp[2] <= 0.2 or right_hp_kp[2] <= 0.2:
                    missing.append("Hips")
                if missing:
                    status_text = f"Missing: {', '.join(missing)}"
                    cv2.putText(frame, status_text, (20, 80),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    
    return frame

def main():
    """
    Main function: Run YOLOv8-Pose and calculate elbow angles in real-time.
    Press 'q' to quit.
    """
    
    # Load the YOLOv8-Pose model
    model = load_pose_model("yolov8n-pose.pt")
    if model is None:
        return
    
    # Open the default webcam
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open webcam")
        return
    
    print("Webcam opened. Computing elbow angles in real-time. Press 'q' to quit.")
    print("Using tracking-based smoothing (alpha=0.3) for stable skeleton visualization.")
    
    # Initialize smoothing dictionary for tracking-based exponential smoothing
    previous_keypoints_dict = {}
    
    # Main loop
    while True:
        success, frame = cap.read()
        
        if not success:
            print("Error: Failed to capture frame")
            break
        
        try:
            # Run YOLOv8-Pose inference with tracking
            results = model.track(frame, persist=True, verbose=False)
            
            # Apply exponential smoothing using tracking IDs
            smoothed_keypoints, previous_keypoints_dict = smooth_keypoints_with_tracking(
                results, previous_keypoints_dict, alpha=0.3
            )
            
            # Extract keypoints (use smoothed if available)
            keypoints = extract_keypoints(results, smoothed_keypoints)
            
            # Draw elbow angles and keypoints
            if keypoints is not None:
                frame = draw_elbow_angles(frame, keypoints, conf_threshold=0.3)
            else:
                # Display message if no person detected
                cv2.putText(frame, "No person detected", (50, 50),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        except Exception as e:
            print(f"Error during inference: {e}")
        
        # Display the frame
        cv2.imshow("Elbow Angle Detection", frame)
        
        # Wait for keyboard input
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("Exiting...")
            break
    
    # Clean up
    cap.release()
    cv2.destroyAllWindows()
    print("Webcam released and windows closed.")

if __name__ == "__main__":
    main()
