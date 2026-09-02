import numpy as np


SEQUENCE_LENGTH = 30


# --------------------------------------------------
# CREATE FIXED LENGTH SEQUENCE
# --------------------------------------------------

def create_fixed_sequence(
    sequence,
    target_length=SEQUENCE_LENGTH
):
    """
    Converts variable number of frames:

    (205, 258)
    (100, 258)
    (80, 258)

    into:

    (30, 258)
    """

    total_frames = len(sequence)

    if total_frames == 0:
        raise ValueError(
            "Sequence contains no frames."
        )

    # -----------------------------------------------
    # VIDEO LONGER THAN 30 FRAMES
    # Uniformly sample across entire video.
    # -----------------------------------------------

    if total_frames >= target_length:

        indices = np.linspace(
            0,
            total_frames - 1,
            target_length,
            dtype=int
        )

        fixed_sequence = sequence[
            indices
        ]

    # -----------------------------------------------
    # VIDEO SHORTER THAN 30 FRAMES
    # Pad with zeros.
    # -----------------------------------------------

    else:

        feature_count = sequence.shape[1]

        padding_size = (
            target_length
            - total_frames
        )

        padding = np.zeros(
            (
                padding_size,
                feature_count
            ),
            dtype=np.float32
        )

        fixed_sequence = np.concatenate(
            [
                sequence,
                padding
            ],
            axis=0
        )

    return fixed_sequence.astype(
        np.float32
    )