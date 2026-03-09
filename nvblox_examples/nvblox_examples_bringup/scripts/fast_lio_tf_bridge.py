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

"""Bridges FAST-LIO /Odometry to TF (odom -> camera0_link)."""

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster


class FastLioTfBridge(Node):

    def __init__(self):
        super().__init__('fast_lio_tf_bridge')
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('child_frame', 'camera0_link')
        self._odom_frame = self.get_parameter('odom_frame').value
        self._child_frame = self.get_parameter('child_frame').value
        self._tf_broadcaster = TransformBroadcaster(self)
        self.create_subscription(Odometry, '/Odometry', self._odometry_callback, 10)
        self.get_logger().info(
            f'Publishing TF: {self._odom_frame} -> {self._child_frame} from /Odometry')

    def _odometry_callback(self, msg: Odometry):
        t = TransformStamped()
        t.header.stamp = msg.header.stamp
        t.header.frame_id = self._odom_frame
        t.child_frame_id = self._child_frame
        t.transform.translation.x = msg.pose.pose.position.x
        t.transform.translation.y = msg.pose.pose.position.y
        t.transform.translation.z = msg.pose.pose.position.z
        t.transform.rotation = msg.pose.pose.orientation
        self._tf_broadcaster.sendTransform(t)


def main(args=None):
    rclpy.init(args=args)
    node = FastLioTfBridge()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
