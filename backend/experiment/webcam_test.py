import cv2

def main():
    """
    Simple webcam streaming program for testing camera access.
    Press 'q' to quit.
    """
    
    # Open the default webcam (index 0)
    cap = cv2.VideoCapture(0)
    
    # Check if webcam opened successfully
    if not cap.isOpened():
        print("Error: Could not open webcam")
        return
    
    print("Webcam opened successfully. Press 'q' to quit.")
    
    # Main loop - continuously capture and display frames
    while True:
        # Read a frame from the webcam
        success, frame = cap.read()
        
        # Check if frame was captured successfully
        if not success:
            print("Error: Failed to capture frame")
            break
        
        # Display the frame in a window
        cv2.imshow("Webcam Feed", frame)
        
        # Wait for keyboard input (1ms timeout)
        # Returns the ASCII value of the key pressed, or -1 if no key pressed
        key = cv2.waitKey(1) & 0xFF
        
        # Exit loop if 'q' key is pressed
        if key == ord('q'):
            print("Exiting...")
            break
    
    # Safely release the webcam resource
    cap.release()
    
    # Close all OpenCV windows
    cv2.destroyAllWindows()
    
    print("Webcam released and windows closed.")

if __name__ == "__main__":
    main()
