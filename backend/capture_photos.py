import cv2
import os
import time

CLASSES = {
    1: "1_Good",
    2: "2_Fair",
    3: "3_Poor",
    4: "4_Bad"
}

def main():
    print("=======================================")
    print("  Posture Dataset Capture Tool")
    print("=======================================")
    for k, v in CLASSES.items():
        print(f"  {k}: {v}")
    
    # Get user choices
    try:
        class_id = int(input("\nEnter the class ID to capture (1-4): "))
        if class_id not in CLASSES:
            print("Invalid class ID. Must be 1, 2, 3, or 4.")
            return
    except ValueError:
        print("Invalid input.")
        return

    try:
        num_photos = int(input("Enter number of photos to capture (e.g., 50): "))
    except ValueError:
        print("Invalid input.")
        return
        
    # Create directory if it doesn't exist
    folder_name = os.path.join("dataset", CLASSES[class_id])
    os.makedirs(folder_name, exist_ok=True)
    
    # Start webcam
    print("\nOpening webcam...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open webcam. Is it being used by another app?")
        return
        
    print(f"\n[GET READY] You selected: {CLASSES[class_id]}")
    for i in range(5, 0, -1):
        print(f"Capture starting in {i} seconds...")
        time.sleep(1)
        
    print("\n*** CAPTURING NOW ***")
    print("Move slightly to get variations in your posture.")
    
    count = 0
    while count < num_photos:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame from camera.")
            break
            
        # Save frame
        filename = os.path.join(folder_name, f"sample_{int(time.time() * 1000)}.jpg")
        cv2.imwrite(filename, frame)
        count += 1
        
        print(f"Captured {count} / {num_photos}")
        
        # Show the camera feed
        cv2.imshow("Capture - Press 'q' to quit early", frame)
        
        # Wait 500ms (0.5 seconds) between photos
        key = cv2.waitKey(500) & 0xFF
        if key == ord('q'):
            print("\nCapture stopped early by user.")
            break
        
    cap.release()
    cv2.destroyAllWindows()
    print(f"\nSUCCESS! Saved {count} photos to the '{folder_name}' folder.")

if __name__ == '__main__':
    main()
