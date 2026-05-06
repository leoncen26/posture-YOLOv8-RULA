import os
import glob

def main():
    print("=======================================")
    print("  Revert Dataset Augmentation")
    print("=======================================")
    
    base_dir = "dataset"
    deleted_count = 0
    
    # The folders where the dataset lives
    CLASSES = ["1_Good", "2_Fair", "3_Poor", "4_Bad"]
    
    for folder_name in CLASSES:
        folder_path = os.path.join(base_dir, folder_name)
        if not os.path.exists(folder_path):
            continue
            
        # Find all images that have "_dark" in their filename (matches _dark50, _dark75, and old _dark formats)
        dark_images = []
        for ext in ("*_dark*.jpg", "*_dark*.png", "*_dark*.jpeg"):
            dark_images.extend(glob.glob(os.path.join(folder_path, ext)))
        
        for img_path in dark_images:
            try:
                os.remove(img_path)
                deleted_count += 1
            except Exception as e:
                print(f"Failed to delete {img_path}: {e}")
                
    print(f"\nSuccessfully removed {deleted_count} augmented (dark) images.")
    print("Your dataset is now perfectly reverted to its original state!")

if __name__ == '__main__':
    main()