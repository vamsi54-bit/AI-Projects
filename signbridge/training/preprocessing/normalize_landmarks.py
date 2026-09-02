import numpy as np


LEFT_HAND_SIZE = 21 * 3
RIGHT_HAND_SIZE = 21 * 3
POSE_SIZE = 33 * 4

TOTAL_FEATURES = (
    LEFT_HAND_SIZE
    + RIGHT_HAND_SIZE
    + POSE_SIZE
)


# Normalize one hand: input (63,), output (63,)
def normalize_hand(hand_data):
    hand = hand_data.reshape(21, 3)

    # Hand not detected
    if np.all(hand == 0):
        return hand_data

    # Put wrist at origin
    wrist = hand[0].copy()
    hand = hand - wrist

    # Make hand size consistent
    distances = np.linalg.norm(hand, axis=1)
    scale = np.max(distances)

    if scale > 0:
        hand = hand / scale

    return hand.flatten()


# Normalize pose: input (132,), output (132,)
def normalize_pose(pose_data):
    pose = pose_data.reshape(33, 4)

    # Pose not detected
    if np.all(pose == 0):
        return pose_data

    # Separate x, y, z from visibility
    xyz = pose[:, :3]
    visibility = pose[:, 3:]

    # MediaPipe pose landmarks:
    # 11 = left shoulder
    # 12 = right shoulder
    left_shoulder = xyz[11]
    right_shoulder = xyz[12]

    # Put shoulder midpoint at origin
    center = (left_shoulder + right_shoulder) / 2
    xyz = xyz - center

    # Make body size consistent using shoulder width
    shoulder_distance = np.linalg.norm(
        left_shoulder - right_shoulder
    )

    if shoulder_distance > 0:
        xyz = xyz / shoulder_distance

    # Put normalized xyz and original visibility together
    pose = np.concatenate([xyz, visibility], axis=1)

    return pose.flatten()


# Normalize one frame: input (258,), output (258,)
def normalize_frame(frame):
    if len(frame) != TOTAL_FEATURES:
        raise ValueError(
            f"Expected {TOTAL_FEATURES} features, "
            f"received {len(frame)} features"
        )

    left_start = 0
    left_end = LEFT_HAND_SIZE

    right_start = left_end
    right_end = right_start + RIGHT_HAND_SIZE

    pose_start = right_end
    pose_end = pose_start + POSE_SIZE

    left_hand = frame[left_start:left_end]
    right_hand = frame[right_start:right_end]
    pose = frame[pose_start:pose_end]

    left_hand = normalize_hand(left_hand)
    right_hand = normalize_hand(right_hand)
    pose = normalize_pose(pose)

    normalized = np.concatenate([
        left_hand,
        right_hand,
        pose
    ])

    return normalized.astype(np.float32)


# Normalize every frame in a video sequence
def normalize_sequence(sequence):
    normalized_frames = []

    for frame in sequence:
        normalized_frame = normalize_frame(frame)
        normalized_frames.append(normalized_frame)

    return np.array(normalized_frames, dtype=np.float32)


