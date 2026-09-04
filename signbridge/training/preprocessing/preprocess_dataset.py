import csv
import json
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

from training.preprocessing.normalize_landmarks import normalize_sequence
from training.preprocessing.create_sequences import create_fixed_sequence


# ==================================================
# CONFIGURATION
# ==================================================

# We search the whole archive.
# "Sample Videos" will be ignored automatically.
DATASET_DIR = Path(
    "data/raw/isl_videos/archive"
)

LANDMARK_DIR = Path(
    "data/processed/landmarks"
)

SEQUENCE_DIR = Path(
    "data/processed/sequences"
)

METADATA_DIR = Path(
    "data/metadata"
)

LANDMARK_DIR.mkdir(
    parents=True,
    exist_ok=True
)

SEQUENCE_DIR.mkdir(
    parents=True,
    exist_ok=True
)

METADATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ==================================================
# MEDIAPIPE
# ==================================================

mp_holistic = mp.solutions.holistic


# ==================================================
# EXTRACT LANDMARKS
# ==================================================

def extract_landmarks(results):

    landmarks = []

    # --------------------------------------------------
    # LEFT HAND
    # 21 landmarks × 3 = 63
    # --------------------------------------------------

    if results.left_hand_landmarks:

        for lm in results.left_hand_landmarks.landmark:

            landmarks.extend([
                lm.x,
                lm.y,
                lm.z
            ])

    else:

        landmarks.extend(
            [0.0] * 63
        )

    # --------------------------------------------------
    # RIGHT HAND
    # 21 landmarks × 3 = 63
    # --------------------------------------------------

    if results.right_hand_landmarks:

        for lm in results.right_hand_landmarks.landmark:

            landmarks.extend([
                lm.x,
                lm.y,
                lm.z
            ])

    else:

        landmarks.extend(
            [0.0] * 63
        )

    # --------------------------------------------------
    # POSE
    # 33 landmarks × 4 = 132
    # --------------------------------------------------

    if results.pose_landmarks:

        for lm in results.pose_landmarks.landmark:

            landmarks.extend([
                lm.x,
                lm.y,
                lm.z,
                lm.visibility
            ])

    else:

        landmarks.extend(
            [0.0] * (33 * 4)
        )

    # Total:
    # 63 + 63 + 132 = 258

    return np.array(
        landmarks,
        dtype=np.float32
    )


# ==================================================
# PROCESS ONE VIDEO
# ==================================================

def process_video(video_path, holistic):

    cap = cv2.VideoCapture(
        str(video_path)
    )

    if not cap.isOpened():

        print(
            "Could not open:",
            video_path
        )

        return None

    sequence = []

    while True:

        success, frame = cap.read()

        if not success:
            break

        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        rgb_frame.flags.writeable = False

        results = holistic.process(
            rgb_frame
        )

        rgb_frame.flags.writeable = True

        frame_landmarks = extract_landmarks(
            results
        )

        sequence.append(
            frame_landmarks
        )

    cap.release()

    if len(sequence) == 0:

        return None

    return np.array(
        sequence,
        dtype=np.float32
    )


# ==================================================
# PREPROCESS FULL DATASET
# ==================================================

def preprocess_dataset():

    # --------------------------------------------------
    # FIND VIDEOS
    # --------------------------------------------------

    all_videos = sorted(
        DATASET_DIR.rglob("*.mp4")
    )

    # Ignore the 61 single example videos
    # inside "Sample Videos".
    videos = [
        video
        for video in all_videos
        if video.parent.name != "Sample Videos"
    ]

    if len(videos) == 0:

        print(
            "No training videos found in:",
            DATASET_DIR
        )

        return

    print(
        "Videos found:",
        len(videos)
    )

    # --------------------------------------------------
    # CREATE LABELS
    #
    # Example:
    #
    # Bear/WIN_001.mp4
    #
    # label = Bear
    # --------------------------------------------------

    labels = sorted(
        list(
            set(
                video.parent.name
                for video in videos
            )
        )
    )

    label_to_index = {
        label: index
        for index, label in enumerate(labels)
    }

    print(
        "Classes found:",
        len(labels)
    )

    # --------------------------------------------------
    # SAVE CLASSES.JSON
    # --------------------------------------------------

    classes_file = (
        METADATA_DIR /
        "classes.json"
    )

    with open(
        classes_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            label_to_index,
            file,
            indent=4
        )

    # --------------------------------------------------
    # CSV
    # --------------------------------------------------

    csv_file = (
        METADATA_DIR /
        "metadata.csv"
    )

    csv_rows = []

    # --------------------------------------------------
    # START MEDIAPIPE
    # --------------------------------------------------

    with mp_holistic.Holistic(

        static_image_mode=False,

        model_complexity=1,

        enable_segmentation=False,

        refine_face_landmarks=False,

        min_detection_confidence=0.5,

        min_tracking_confidence=0.5

    ) as holistic:

        total = len(videos)

        # --------------------------------------------------
        # LOOP THROUGH VIDEOS
        # --------------------------------------------------

        for index, video_path in enumerate(
            videos,
            start=1
        ):

            # Folder name becomes label.
            label = video_path.parent.name

            class_index = (
                label_to_index[label]
            )

            print()
            print(
                f"[{index}/{total}]"
            )

            print(
                "Label:",
                label
            )

            print(
                "Video:",
                video_path.name
            )

            # --------------------------------------------------
            # CREATE CLASS OUTPUT FOLDERS
            # --------------------------------------------------

            class_landmark_dir = (
                LANDMARK_DIR /
                label
            )

            class_sequence_dir = (
                SEQUENCE_DIR /
                label
            )

            class_landmark_dir.mkdir(
                parents=True,
                exist_ok=True
            )

            class_sequence_dir.mkdir(
                parents=True,
                exist_ok=True
            )

            landmark_file = (
                class_landmark_dir /
                f"{video_path.stem}.npy"
            )

            sequence_file = (
                class_sequence_dir /
                f"{video_path.stem}.npy"
            )

            # --------------------------------------------------
            # RESUME SUPPORT
            #
            # If preprocessing stops halfway,
            # already processed sequences are not
            # processed again.
            # --------------------------------------------------

            if sequence_file.exists():

                print(
                    "Already processed. Skipping MediaPipe."
                )

                processed_sequence = np.load(
                    sequence_file
                )

                csv_rows.append({

                    "video": video_path.name,

                    "label": label,

                    "class_index": class_index,

                    "frames": processed_sequence.shape[0],

                    "features": processed_sequence.shape[1],

                    "sequence_file": str(
                        sequence_file
                    )
                })

                continue

            # --------------------------------------------------
            # STEP 1:
            # VIDEO → LANDMARKS
            # --------------------------------------------------

            sequence = process_video(
                video_path,
                holistic
            )

            if sequence is None:

                print(
                    "Skipping invalid video."
                )

                continue

            print(
                "Raw shape:",
                sequence.shape
            )

            # --------------------------------------------------
            # SAVE RAW LANDMARKS
            # --------------------------------------------------

            np.save(
                landmark_file,
                sequence
            )

            # --------------------------------------------------
            # STEP 2:
            # NORMALIZATION
            # --------------------------------------------------

            sequence = normalize_sequence(
                sequence
            )

            # --------------------------------------------------
            # STEP 3:
            # FIXED 30 FRAME SEQUENCE
            # --------------------------------------------------

            sequence = create_fixed_sequence(
                sequence
            )

            print(
                "Processed shape:",
                sequence.shape
            )

            # --------------------------------------------------
            # STEP 4:
            # SAVE FINAL SEQUENCE
            # --------------------------------------------------

            np.save(
                sequence_file,
                sequence
            )

            # --------------------------------------------------
            # ADD METADATA
            # --------------------------------------------------

            csv_rows.append({

                "video": video_path.name,

                "label": label,

                "class_index": class_index,

                "frames": sequence.shape[0],

                "features": sequence.shape[1],

                "sequence_file": str(
                    sequence_file
                )
            })

            # --------------------------------------------------
            # SAVE CSV PROGRESS
            #
            # This means if preprocessing is interrupted,
            # metadata is not completely lost.
            # --------------------------------------------------

            with open(
                csv_file,
                "w",
                newline="",
                encoding="utf-8"
            ) as file:

                writer = csv.DictWriter(

                    file,

                    fieldnames=[
                        "video",
                        "label",
                        "class_index",
                        "frames",
                        "features",
                        "sequence_file"
                    ]
                )

                writer.writeheader()

                writer.writerows(
                    csv_rows
                )

    # --------------------------------------------------
    # FINAL CSV SAVE
    # --------------------------------------------------

    with open(
        csv_file,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(

            file,

            fieldnames=[
                "video",
                "label",
                "class_index",
                "frames",
                "features",
                "sequence_file"
            ]
        )

        writer.writeheader()

        writer.writerows(
            csv_rows
        )

    # ==================================================
    # COMPLETE
    # ==================================================

    print()
    print(
        "======================================"
    )

    print(
        "PREPROCESSING COMPLETED"
    )

    print(
        "======================================"
    )

    print(
        "Videos processed:",
        len(csv_rows)
    )

    print(
        "Classes:",
        len(labels)
    )

    print(
        "Sequence shape:",
        "(30, 258)"
    )

    print(
        "Classes file:",
        classes_file
    )

    print(
        "Dataset CSV:",
        csv_file
    )


# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":

    preprocess_dataset()