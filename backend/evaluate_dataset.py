import cv2
import os
import glob
import app
from app import (
    load_pose_model, 
    draw_pose_and_rula, 
    reset_stability_state,
    _compute_metrics_from_confusion,
    EVAL_LABEL_ALIASES
)

# Disable temporal smoothing/debouncing in app.py for static images
app.LEGS_RAISED_CONFIRM_FRAMES = 1
app.LEGS_NORMAL_CONFIRM_FRAMES = 1
app.ANGLE_EMA_ALPHA = 1.0  # Instant angle updates, no memory of previous frames

CLASSES = {
    1: "1_Good",
    2: "2_Fair",
    3: "3_Poor",
    4: "4_Bad"
}

def main():
    print("=======================================")
    print("  Posture Dataset Evaluator Tool")
    print("=======================================")
    
    # Ensure the model loads correctly
    model = load_pose_model("yolov8n-pose.pt")
    if model is None:
        print("Failed to load the YOLO model. Check 'yolov8n-pose.pt' file.")
        return
        
    confusion_matrix = [[0, 0, 0, 0] for _ in range(4)]
    
    total_images_processed = 0
    total_undetected = 0
    
    for true_id, folder_name in CLASSES.items():
        folder_path = os.path.join("dataset", folder_name)
        if not os.path.exists(folder_path):
            print(f"Folder '{folder_path}' not found. Make sure you capture photos first.")
            continue
            
        images = glob.glob(os.path.join(folder_path, "*.jpg")) + \
         glob.glob(os.path.join(folder_path, "*.png"))
        if not images:
            print(f"No images found in '{folder_path}'. Skipping.")
            continue
            
        print(f"\nProcessing '{folder_name}' ({len(images)} images)...")
        
        for img_path in images:
            frame = cv2.imread(img_path)
            if frame is None:
                continue
                
            # CRITICAL: Reset stability state so the program doesn't "remember" the previous photo's posture.
            # We want to treat every photo completely independently!
            reset_stability_state()
            
            # Run YOLO Prediction
            results = model.predict(frame, verbose=False)
            
            keypoints = None
            if len(results) > 0 and results[0].keypoints is not None:
                # We extract the pure tensor data (N x 17 x 3)
                keypoints = results[0].keypoints.data.cpu().numpy()
            
            # If keypoints are found, calculate the RULA Score 
            if keypoints is not None:
                _, rula_data = app.draw_pose_and_rula(frame, keypoints, conf_threshold=0.35, draw_overlay=False)
                
                if rula_data and rula_data.get("detected"):
                    # This classification string will look like "Good Posture" or "Fair Posture - Monitor"
                    predicted_class_text = rula_data["classification"]
                    
                    # Look up the ID (1, 2, 3, or 4) using our helper dictionary from app.py
                    predicted_id = EVAL_LABEL_ALIASES.get(predicted_class_text.lower().strip())
                    
                    if predicted_id:
                        # We use strict evaluation logic.
                        # The prediction from the model is recorded exactly as it is (no artificial tolerance).
                        
                        # Add a tally to our confusion matrix: matrix[true_row - 1][predicted_col - 1]
                        confusion_matrix[true_id - 1][predicted_id - 1] += 1
                        total_images_processed += 1
                    else:
                        print(f"  Warning: Unknown classification string: '{predicted_class_text}'")
                else:
                    # Model found a person, but not enough keypoints to calculate upper body RULA
                    print(f"  Warning: Not enough upper body keypoints detected in {os.path.basename(img_path)}")
                    total_undetected += 1
            else:
                # Model found 0 people
                print(f"  Warning: No person detected at all in {os.path.basename(img_path)}")
                total_undetected += 1

    print("\n================ EVALUATION RESULTS ================\n")
    if total_images_processed == 0:
        print("No valid images were processed. Did you take the photos yet?")
        return
        
    metrics = _compute_metrics_from_confusion(confusion_matrix)
    
    print("\n[ CONFUSION MATRIX ]")
    print("True \\ Predicted |  Good (1) |  Fair (2) |  Poor (3) |   Bad (4)")
    print("-" * 65)
    for i, row in enumerate(confusion_matrix):
        print(f"  True {i+1:<9} | {row[0]:9d} | {row[1]:9d} | {row[2]:9d} | {row[3]:9d}")
        
    print("\n[ OVERALL METRICS ]")
    print(f"Total Successful Samples : {metrics['total_samples']}")
    print(f"Total Failed Detections  : {total_undetected}")
    print(f"Accuracy                 : {metrics['accuracy'] * 100:.2f}%")
    print(f"Precision (Macro)        : {metrics['precision_macro']:.4f}")
    print(f"Recall (Macro)           : {metrics['recall_macro']:.4f}")
    print(f"F1-Score (Macro)         : {metrics['f1_macro']:.4f}")
    
    print("\n[ PER-CLASS METRICS ]")
    for cls in metrics['per_class']:
        # Format the label name so the columns align cleanly
        short_label = (cls['label'][:18] + '..') if len(cls['label']) > 18 else f"{cls['label']:<20}"
        
        print(f"Class {cls['label_id']} - {short_label}:")
        print(f"  Support   : {cls['support']} samples")
        print(f"  Precision : {cls['precision']:.4f}")
        print(f"  Recall    : {cls['recall']:.4f}")
        print(f"  F1-Score  : {cls['f1']:.4f}")
        print("")

if __name__ == '__main__':
    main()
