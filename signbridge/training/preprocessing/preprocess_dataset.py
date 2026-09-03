import json
import csv
from pathlib import Path

import cv2 
import numpy as np
import mediapipe as mp

from training.preprocessing.normalize_landmarks import normalize_sequence
from training.preprocessing.create_sequences import create_fixed_sequence

DATASET_DIR = Path(
    "data/raw/isl_videos/archive/Sample Videos"
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
    parents = True,
    exist_ok = True
)

SEQUENCE_DIR.mkdir(
    parents = True,
    exist_ok = True
)

METADATA_DIR.mkdir(
    parents = True,
    exist_ok = True
)

mp_holistic = mp.solutions.holistic

def extract_landmarks(results):

    landmarks = []

    # ----------------------------------------------
    # LEFT HAND
    # ----------------------------------------------

    if results.left_hand_landmarks:

        for lm in (
            results
            .left_hand_landmarks
            .landmark
        ):

            landmarks.extend([
                lm.x,
                lm.y,
                lm.z
            ])

    else:

        landmarks.extend(
            [0.0] * 63
        )

    # ----------------------------------------------
    # RIGHT HAND
    # ----------------------------------------------

    if results.right_hand_landmarks:

        for lm in (
            results
            .right_hand_landmarks
            .landmark
        ):

            landmarks.extend([
                lm.x,
                lm.y,
                lm.z
            ])

    else:

        landmarks.extend(
            [0.0] * 63
        )

    # ----------------------------------------------
    # POSE
    # ----------------------------------------------

    if results.pose_landmarks:

        for lm in (
            results
            .pose_landmarks
            .landmark
        ):

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

    return np.array(
        landmarks,
        dtype=np.float32
    )

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


        landmarks = extract_landmarks(
            results
        )

        sequence.append(
            landmarks
        )


    cap.release()


    if len(sequence) == 0:

        return None


    return np.array(
        sequence,
        dtype=np.float32
    )



    
def preprocess_dataset():
    videos = sorted(DATASET_DIR.rglob("*.mp4"))

    if len(videos) == 0:
        print("No Videos Found in: ",DATASET_DIR)
        return

    print("Videos found: ", len(videos))

    labels = sorted(
        list(
            set(
                video.stem
                for video in videos
            )
        )
    )

    label_to_index = {
        label: index
        for index, label in enumerate(labels)
    }

    print("Classes found: ", len(labels))

    classes_file = (
        METADATA_DIR
        / "classes.json"
    )

    with open(classes_file, "w", encoding = "utf-8") as file:
        json.dump(
            label_to_index,
            file,
            indent = 4
        )

    csv_file = (
        METADATA_DIR
        / "metadata.csv"
    )

    csv_rows = []

    with mp_holistic.Holistic(
        static_image_mode = False,
        model_complexity = 1,
        enable_segmentation = False,
        refine_face_landmarks = False,
        min_detection_confidence = 0.5,
        min_tracking_confidence = 0.5
    ) as holistic:

        total = len(videos)
        for index, video_path in enumerate(videos, start = 1):
            label = video_path.stem
            class_index = (
                label_to_index[label]
            )

            print()
            print(f"[{index}/{total}] Processing: {video_path}")

            sequence = process_video(video_path, holistic)

            if sequence is None:
                print("Skipping Video")
                continue

            print("Row: ", sequence.shape)

            landmark_file = (
                LANDMARK_DIR /
                f"{video_path.stem}.npy"
            )

            np.save(landmark_file, sequence)

            sequence = normalize_sequence(sequence)

            sequence = create_fixed_sequence(sequence)

            print("processed: ",sequence.shape)

            output_file = (
                SEQUENCE_DIR /
                f"{video_path.stem}.npy"
            )

            np.save(output_file,sequence)

            csv_rows.append({
                "video": video_path.name,
                "label": label,
                "class_index": class_index,
                "frames": sequence.shape[0],
                "features": sequence.shape[1],
                "sequence_file": str(output_file)
            })

        with open(csv_file, "w", newline = "", encoding = "utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames = [
                    "video",
                    "label",
                    "class_index",
                    "frames",
                    "features",
                    "sequence_file"
                ]
            )

            writer.writeheader()
            writer.writerows(csv_rows)

    print()
    print(
        "================================"
    )

    print(
        "PREPROCESSING COMPLETED"
    )

    print(
        "================================"
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


# --------------------------------------------------
# RUN
# --------------------------------------------------

if __name__ == "__main__":

    preprocess_dataset()



    