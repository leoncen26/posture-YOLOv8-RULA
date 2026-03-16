import cv2
import numpy as np
from ultralytics import YOLO

def load_pose_model(model_path="yolov8n-pose.pt"):
    """
    Load the YOLOv8-Pose pretrained model.
    
    Args:
        model_path: Path to the model file (e.g., "yolov8n-pose.pt")
    
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

def draw_poses(frame, results):
    """
    Draw keypoints and skeleton connections on the frame.
    
    Args:
        frame: OpenCV image frame
        results: YOLO inference results object
    
    Returns:
        Frame with drawn keypoints and skeleton
    """
    # COCO skeleton connections (pairs of keypoint indices)
    skeleton = [
        (0, 1),   # nose to left eye
        (0, 2),   # nose to right eye
        (1, 3),   # left eye to left ear
        (2, 4),   # right eye to right ear
        (5, 6),   # left shoulder to right shoulder
        (5, 7),   # left shoulder to left elbow
        (7, 9),   # left elbow to left wrist
        (6, 8),   # right shoulder to right elbow
        (8, 10),  # right elbow to right wrist
        (5, 11),  # left shoulder to left hip
        (6, 12),  # right shoulder to right hip
        (11, 12), # left hip to right hip
        (11, 13), # left hip to left knee
        (13, 15), # left knee to left ankle
        (12, 14), # right hip to right knee
        (14, 16), # right knee to right ankle
    ]
    
    # Confidence threshold for drawing keypoints
    conf_threshold = 0.3
    
    # Check if there are detections
    if results[0].keypoints is not None:
        keypoints = results[0].keypoints.data  # Shape: (num_persons, 17, 3) - (x, y, confidence)
        
        # Draw for each detected person
        for person_keypoints in keypoints:
            # Draw skeleton connections
            for start_idx, end_idx in skeleton:
                start_point = person_keypoints[start_idx]
                end_point = person_keypoints[end_idx]
                
                # Check if both keypoints have sufficient confidence
                if start_point[2] > conf_threshold and end_point[2] > conf_threshold:
                    pt1 = (int(start_point[0]), int(start_point[1]))
                    pt2 = (int(end_point[0]), int(end_point[1]))
                    cv2.line(frame, pt1, pt2, (0, 255, 0), 2)
            
            # Draw keypoints as circles
            for keypoint in person_keypoints:
                x, y, conf = keypoint
                if conf > conf_threshold:
                    center = (int(x), int(y))
                    cv2.circle(frame, center, 4, (0, 0, 255), -1)
    
    return frame

def main():
    """
    Main function: Run YOLOv8-Pose on webcam feed.
    Press 'q' to quit.
    """
    
    # Load the YOLOv8-Pose model
    model = load_pose_model("yolov8n-pose.pt")
    if model is None:
        return
    
    # Open the default webcam
    cap = cv2.VideoCapture(0)
    
    # Check if webcam opened successfully
    if not cap.isOpened():
        print("Error: Could not open webcam")
        return
    
    print("Webcam opened. Running YOLOv8-Pose inference. Press 'q' to quit.")
    
    # Main loop - process frames from webcam
    while True:
        # Capture a frame from the webcam
        success, frame = cap.read()
        
        if not success:
            print("Error: Failed to capture frame")
            break
        
        # Run YOLOv8-Pose inference on the frame
        try:
            results = model(frame, verbose=False)
            
            # Draw keypoints and skeleton on the frame
            frame = draw_poses(frame, results)
            
        except Exception as e:
            print(f"Inference error: {e}")
        
        # Display the processed frame
        cv2.imshow("YOLOv8-Pose Detection", frame)
        
        # Wait for keyboard input (1ms timeout)
        key = cv2.waitKey(1) & 0xFF
        
        # Exit if 'q' key is pressed
        if key == ord('q'):
            print("Exiting...")
            break
    
    # Clean up: release webcam and close windows
    cap.release()
    cv2.destroyAllWindows()
    
    print("Webcam released and windows closed.")

if __name__ == "__main__":
    main()
