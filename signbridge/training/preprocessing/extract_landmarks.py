import cv2
import mediapipe as mp
import numpy as np
from pathlib import Path

VIDEO_PATH = Path("data/raw/isl_videos/archive/Sample Videos/Bear.mp4")
OUTPUT_DIR = Path("data/processed/landmarks")

OUTPUT_DIR.mkdir(parents = True,exist_ok = True)

#mediapipe setup
mp_holistic = mp.solutions.holistic

holistic = mp_holistic.Holistic(
    static_image_mode = False,
    model_complexity = 1,
    enable_segmentation = False,
    refine_face_landmarks = False,
    min_detection_confidence = 0.5,
    min_tracking_confidence = 0.5
)

def landmark_extraction(results):
    landmarks = []

    # Left hand
    if results.left_hand_landmarks:
        for lm in results.left_hand_landmarks.landmark:
            landmarks.extend([lm.x, lm.y, lm.z])
    else:
        landmarks.extend([0.0] * 63)

    # Right hand
    if results.right_hand_landmarks:
        for lm in results.right_hand_landmarks.landmark:
            landmarks.extend([lm.x, lm.y, lm.z])
    else:
        landmarks.extend([0.0] * 63)

    # Pose
    if results.pose_landmarks:
        for lm in results.pose_landmarks.landmark:
            landmarks.extend([lm.x, lm.y, lm.z, lm.visibility])
    else:
        landmarks.extend([0.0] * (33 * 4))

    return np.array(landmarks, dtype=np.float32)

def process_video(VIDEO_PATH):
    print("Processing: ",VIDEO_PATH)
    cap = cv2.VideoCapture(str(VIDEO_PATH))

    if not cap.isOpened():
        print("could not open video")
        return None
    sequence = []
    frame_count = 0

    while True:
        success, frame = cap.read()
        if not success:
            break
        frame_count += 1

        rgb_frame = cv2.cvtColor(
            frame,cv2.COLOR_BGR2RGB
        )

        rgb_frame.flags.writeable = False
        results = holistic.process(rgb_frame)
        rgb_frame.flags.writeable = True

        frame_landmarks = landmark_extraction(results)
        sequence.append(frame_landmarks)
        print(f"\r Frames Processed: {frame_count}",end = "")
    cap.release()
    print()

    if len(sequence) == 0:
        print("No frames found")
        return None
    sequence = np.array(sequence)
    return sequence

#main function
if __name__ == "__main__":
    sequence = process_video(
        VIDEO_PATH
    )
    if sequence is not None:
        output_file = (
            OUTPUT_DIR / f"{VIDEO_PATH.stem}.npy"
        )

        print("Landmarks saved successfully.")

        np.save(output_file, sequence)

        print(
            "Output:",
            output_file
        )

        print(
            "Sequence shape:",
            sequence.shape
        )

        print(
            "Landmarks per frame:",
            sequence.shape[1]
        )

    holistic.close()