"""COCO-17 keypoint layout used by YOLO pose models."""

from __future__ import annotations

KEYPOINT_NAMES = [
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
]

KP = {name: i for i, name in enumerate(KEYPOINT_NAMES)}

# Limb connections drawn by the dashboard overlay.
SKELETON = [
    (5, 7), (7, 9),        # left arm
    (6, 8), (8, 10),       # right arm
    (5, 6),                # shoulders
    (5, 11), (6, 12),      # torso sides
    (11, 12),              # hips
    (11, 13), (13, 15),    # left leg
    (12, 14), (14, 16),    # right leg
    (0, 5), (0, 6),        # head to shoulders
]

# Joints needed per body side for push-up analysis.
SIDE_JOINTS = {
    "left": {
        "shoulder": KP["left_shoulder"],
        "elbow": KP["left_elbow"],
        "wrist": KP["left_wrist"],
        "hip": KP["left_hip"],
        "knee": KP["left_knee"],
        "ankle": KP["left_ankle"],
    },
    "right": {
        "shoulder": KP["right_shoulder"],
        "elbow": KP["right_elbow"],
        "wrist": KP["right_wrist"],
        "hip": KP["right_hip"],
        "knee": KP["right_knee"],
        "ankle": KP["right_ankle"],
    },
}
