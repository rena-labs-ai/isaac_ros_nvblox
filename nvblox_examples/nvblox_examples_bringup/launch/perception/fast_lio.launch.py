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

from isaac_ros_launch_utils.all_types import *
import isaac_ros_launch_utils as lu


def generate_launch_description() -> LaunchDescription:
    args = lu.ArgumentContainer()
    args.add_arg(
        'odom_frame',
        'odom',
        description='Parent frame for FAST-LIO odometry TF.',
        cli=True)
    args.add_arg(
        'child_frame',
        'camera0_link',
        description='Child frame (e.g. camera0_link for Realsense, zed_camera_link for ZED).',
        cli=True)
    actions = args.get_launch_actions()

    actions.append(
        Node(
            package='nvblox_examples_bringup',
            executable='fast_lio_tf_bridge.py',
            name='fast_lio_tf_bridge',
            parameters=[{
                'odom_frame': args.odom_frame,
                'child_frame': args.child_frame,
            }],
        ))

    return LaunchDescription(actions)
