#!/usr/bin/env python3
# SPDX-FileCopyrightText: NVIDIA CORPORATION & AFFILIATES
# Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""Subscribe to compressedDepth (CompressedImage), publish raw depth (Image).

Decode follows compressed_depth_image_transport/src/codec.cpp (ConfigHeader +
PNG or RVL), not cv_bridge.compressed_imgmsg_to_cv2 (raw PNG-only).
"""

from __future__ import annotations

import struct
import time

import rclpy
import cv2
import numpy as np
from cv_bridge import CvBridge, CvBridgeError
from rclpy.node import Node
from rclpy.qos import (
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
    qos_profile_sensor_data,
)
from sensor_msgs.msg import CompressedImage, Image

# ConfigHeader in compressed_depth_image_transport/compression_common.hpp
_CONFIG_HEADER = struct.Struct('<iff')


def _transport_format_from_ros_format(format_str: str) -> str | None:
    """Same rules as codec.cpp decodeCompressedDepthImage."""
    split_pos = format_str.find(';')
    if split_pos == -1:
        return 'png'
    ending = format_str[split_pos:]
    if 'compressedDepth png' in ending:
        return 'png'
    if 'compressedDepth rvl' in ending:
        return 'rvl'
    if 'compressedDepth' in ending and 'compressedDepth ' not in ending:
        return 'png'
    return None


def _encoding_bit_depth(image_encoding: str) -> int:
    digits: list[str] = []
    for char in image_encoding:
        if char.isdigit():
            digits.append(char)
        elif digits:
            break
    return int(''.join(digits)) if digits else 0


def decode_compressed_depth_image(msg: CompressedImage) -> tuple[np.ndarray, str] | None:
    """Decode like compressed_depth_image_transport::decodeCompressedDepthImage."""
    if len(msg.data) <= _CONFIG_HEADER.size:
        return None

    split_pos = msg.format.find(';')
    if split_pos == -1:
        image_encoding = msg.format
    else:
        image_encoding = msg.format[:split_pos]

    transport_fmt = _transport_format_from_ros_format(msg.format)
    if transport_fmt is None:
        return None

    _, depth_quant_a, depth_quant_b = _CONFIG_HEADER.unpack_from(msg.data, 0)
    png_or_rvl_bytes = bytes(msg.data[_CONFIG_HEADER.size :])

    if transport_fmt == 'rvl':
        return None

    if transport_fmt != 'png':
        return None

    try:
        decompressed = cv2.imdecode(
            np.frombuffer(png_or_rvl_bytes, dtype=np.uint8), cv2.IMREAD_UNCHANGED
        )
    except cv2.error:
        return None

    if decompressed is None:
        return None

    rows, cols = decompressed.shape[:2]
    if rows == 0 or cols == 0:
        return None

    bit_depth = _encoding_bit_depth(image_encoding)
    if bit_depth == 32:
        inv = decompressed.astype(np.float32, copy=False)
        depth = np.full((rows, cols), np.nan, dtype=np.float32)
        mask = inv != 0.0
        depth[mask] = depth_quant_a / (inv[mask] - depth_quant_b)
        return depth, image_encoding

    # 16-bit etc.: already decoded raw depth
    return decompressed, image_encoding


class DepthCompressedToRaw(Node):

    def __init__(self) -> None:
        super().__init__('depth_compressed_to_raw')
        self.declare_parameter('input_topic', '')
        self.declare_parameter('output_topic', '')
        self.declare_parameter('qos_preset', 'reliable')

        in_topic = self.get_parameter('input_topic').get_parameter_value().string_value
        out_topic = self.get_parameter('output_topic').get_parameter_value().string_value
        qos_preset = self.get_parameter('qos_preset').get_parameter_value().string_value

        if not in_topic or not out_topic:
            raise RuntimeError('depth_compressed_to_raw: input_topic and output_topic must be set')

        if qos_preset.lower() == 'sensor_data':
            sub_qos = pub_qos = qos_profile_sensor_data
        else:
            sub_qos = pub_qos = QoSProfile(
                depth=10,
                reliability=ReliabilityPolicy.RELIABLE,
                history=HistoryPolicy.KEEP_LAST,
            )

        self._bridge = CvBridge()
        self._pub = self.create_publisher(Image, out_topic, pub_qos)
        self.create_subscription(CompressedImage, in_topic, self._on_compressed, sub_qos)
        self._logged_once = False
        self._compressed_debug_count = 0
        self._last_decode_fail_mono = 0.0
        self._rvl_warned = False
        self.get_logger().info(
            f'Depth decompress (codec.cpp-style): subscribe {in_topic} (qos={qos_preset}) -> '
            f'publish {out_topic}'
        )

    def _on_compressed(self, msg: CompressedImage) -> None:
        data_len = len(msg.data)
        if self._compressed_debug_count < 3:
            self.get_logger().info(
                f'CompressedImage[{self._compressed_debug_count}]: format={msg.format!r} '
                f'data_len={data_len} frame_id={msg.header.frame_id!r}'
            )
            self._compressed_debug_count += 1

        decoded = decode_compressed_depth_image(msg)
        if decoded is None:
            now = time.monotonic()
            if _transport_format_from_ros_format(msg.format) == 'rvl':
                if not self._rvl_warned:
                    self.get_logger().error(
                        'RVL compressed depth is not supported in this node; use png on publisher.'
                    )
                    self._rvl_warned = True
            elif now - self._last_decode_fail_mono > 2.0:
                self.get_logger().error(
                    f'decode_compressed_depth_image failed format={msg.format!r} len={data_len}'
                )
                self._last_decode_fail_mono = now
            return

        cv_image, encoding = decoded
        if cv_image.ndim == 3:
            cv_image = cv_image[:, :, 0]

        try:
            out = self._bridge.cv2_to_imgmsg(cv_image, encoding=encoding)
        except CvBridgeError as exc:
            self.get_logger().error(f'cv2_to_imgmsg failed: {exc} encoding={encoding!r}')
            return

        out.header = msg.header
        self._pub.publish(out)
        if not self._logged_once:
            self.get_logger().info(
                f'Publishing raw depth encoding={out.encoding} {out.width}x{out.height}'
            )
            self._logged_once = True


def main() -> None:
    rclpy.init()
    node = DepthCompressedToRaw()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
