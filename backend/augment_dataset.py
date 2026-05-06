import os
import cv2
import glob

CLASSES = [
    "1_Good",
    "2_Fair",
    "3_Poor",
    "4_Bad"
]

def reduce_brightness(image, factor=0.5):
    """
    Reduces the brightness of an image.
    factor = 0.5 means the image becomes 50% darker.
    cv2.convertScaleAbs automatically handles the math and limits pixels to 0-255.
    """
    return cv2.convertScaleAbs(image, alpha=factor, beta=0)

def main():
    print("=======================================")
    print("  Dataset Augmentation Tool")
    print("=======================================")
    
    base_dir = "dataset"
    total_augmented = 0
    total_original = 0

    for folder_name in CLASSES:
        folder_path = os.path.join(base_dir, folder_name)
        if not os.path.exists(folder_path):
            print(f"Folder not found: {folder_path}")
            continue
            
        # Find all images but exclude photos that already have "_dark" to prevent double-augmenting
        images = []
        for ext in ("*.jpg", "*.png", "*.jpeg"):
            images.extend(glob.glob(os.path.join(folder_path, ext)))
            
        orig_images = [img for img in images if "_dark" not in img]
        total_original += len(orig_images)
        
        print(f"\nProcessing '{folder_name}' ({len(orig_images)} original images)...")
        
        for img_path in orig_images:
            # Read the original image
            img = cv2.imread(img_path)
            if img is None:
                print(f"Failed to read {img_path}")
                continue
                
            # Augment 1: reduce brightness by 50% (alpha=0.5)
            dark50_img = reduce_brightness(img, factor=0.5)
            
            # Augment 2: reduce brightness by 75% (alpha=0.25)
            dark75_img = reduce_brightness(img, factor=0.25)
            
            # Create new filenames (e.g., image_dark50.jpg, image_dark75.jpg)
            file_name, file_ext = os.path.splitext(img_path)
            
            # Save the augmented images
            cv2.imwrite(f"{file_name}_dark50{file_ext}", dark50_img)
            cv2.imwrite(f"{file_name}_dark75{file_ext}", dark75_img)
            total_augmented += 2
            
        print(f"  -> Added {len(orig_images) * 2} dark images (50% and 75% reduction).")
        
    print("\n================ REPORT ================")
    print(f"Successfully generated {total_augmented} augmented (dark) images.")
    print(f"Total dataset size is now {total_original + total_augmented} images (Original + Augmented)!")

if __name__ == '__main__':
    main()