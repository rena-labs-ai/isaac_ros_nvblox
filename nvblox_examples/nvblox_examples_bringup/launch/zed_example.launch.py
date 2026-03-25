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

from nvblox_ros_python_utils.nvblox_launch_utils import NvbloxMode, NvbloxCamera, NvbloxPeopleSegmentation

ZED_EXAMPLE_CAMERA = str(NvbloxCamera.zed2)
from nvblox_ros_python_utils.nvblox_constants import NVBLOX_CONTAINER_NAME


def generate_launch_description() -> LaunchDescription:
    args = lu.ArgumentContainer()
    args.add_arg(
        'rosbag', 'None', description='Path to rosbag (running on sensor if not set).', cli=True)
    args.add_arg('rosbag_args', '', description='Additional args for ros2 bag play.', cli=True)
    args.add_arg('log_level', 'info', choices=['debug', 'info', 'warn'], cli=True)
    args.add_arg(
        'mode',
        default=NvbloxMode.static,
        choices=NvbloxMode.names(),
        description='The nvblox mode (use people_segmentation or people_detection to run the DNN pipelines).',
        cli=True)
    args.add_arg(
        'people_segmentation',
        default=NvbloxPeopleSegmentation.peoplesemsegnet_vanilla,
        choices=[
            str(NvbloxPeopleSegmentation.peoplesemsegnet_vanilla),
            str(NvbloxPeopleSegmentation.peoplesemsegnet_shuffleseg)
        ],
        description='PeopleSemSegNet variant (only used when mode:=people_segmentation).',
        cli=True)
    args.add_arg(
        'navigation',
        False,
        description='Whether to enable Nav2 with nvblox costmap (same as nvblox_carter_navigation with zed_nav2).',
        cli=True)
    args.add_arg(
        'nav_config',
        'zed_nav2.yaml',
        description='Nav2 params file under config/navigation (e.g. zed_nav2.yaml).',
        cli=True)
    args.add_arg(
        'slam',
        'none',
        choices=['none', 'fast_lio'],
        description='none: ZED odometry. fast_lio: external FAST-LIO only (publishes /Odometry); launches TF bridge odom->zed_camera_link.',
        cli=True)
    args.add_arg(
        'zed_lighting',
        'default',
        choices=['default', 'low_light'],
        description='ZED: default = zed_common + zed2 only (no overlay). low_light = zed2_low_light.yaml '
        '(cuVSLAM-oriented: 30 FPS, ISP tune + denoising; see TROUBLESHOOTING.md).',
        cli=True)
    actions = args.get_launch_actions()

    # Globally set use_sim_time if we're running from bag or sim
    actions.append(
        SetParameter('use_sim_time', True, condition=IfCondition(lu.is_valid(args.rosbag))))

    # Navigation (same stack as: ros2 launch ... nvblox_carter_navigation.launch.py mode:=static nav_config:=zed_nav2.yaml)
    # NOTE: must run before the nvblox component container; loads Nav2 params globally.
    actions.append(
        lu.include(
            'nvblox_examples_bringup',
            'launch/navigation/nvblox_carter_navigation.launch.py',
            launch_arguments={
                'container_name': NVBLOX_CONTAINER_NAME,
                'mode': args.mode,
                'nav_config': args.nav_config,
            },
            condition=IfCondition(lu.is_true(args.navigation))))

    # Robot center (Nav2 base) vs ZED odom frame: camera is 0.15 m behind and 0.08 m left of chassis center
    # (zed_camera_link: x forward, y left). Publishes zed_camera_link -> zed_base_link for zed_nav2.yaml.
    actions.append(
        Node(
            package='tf2_ros',
            name='zed_camera_to_base_link_tf',
            executable='static_transform_publisher',
            output='screen',
            arguments=[
                '0.15',
                '-0.08',
                '0',
                '0',
                '0',
                '0',
                'zed_camera_link',
                'zed_base_link',
            ],
            condition=IfCondition(
                AndSubstitution(lu.is_true(args.navigation),
                              lu.is_equal(args.nav_config, 'zed_nav2.yaml')))))

    # Container
    actions.append(lu.component_container(NVBLOX_CONTAINER_NAME, log_level=args.log_level))

    # ZED driver
    actions.append(
        lu.include(
            'nvblox_examples_bringup',
            'launch/sensors/zed.launch.py',
            launch_arguments={
                'container_name': NVBLOX_CONTAINER_NAME,
                'zed_lighting': args.zed_lighting,
            },
            condition=UnlessCondition(lu.is_valid(args.rosbag))))

    # FAST-LIO (external): bridge /Odometry to TF odom -> zed_camera_link (Realsense uses camera0_link via fast_lio.launch.py defaults).
    actions.append(
        lu.include(
            'nvblox_examples_bringup',
            'launch/perception/fast_lio.launch.py',
            launch_arguments={
                'child_frame': 'zed_camera_link',
            },
            condition=IfCondition(lu.is_equal(args.slam, 'fast_lio'))))

    # ZED topics use namespace `zed` (see launch/sensors/zed.launch.py).
    zed_ns = 'zed'
    camera_namespaces = [zed_ns]
    camera_input_topics = [f'/{zed_ns}/zed_node/rgb/image_rect_color']
    input_camera_info_topics = [f'/{zed_ns}/zed_node/rgb/camera_info']
    output_resized_image_topics = [f'/{zed_ns}/segmentation/image_resized']
    output_resized_camera_info_topics = [f'/{zed_ns}/segmentation/camera_info_resized']

    # People segmentation
    actions.append(
        lu.include(
            'nvblox_examples_bringup',
            'launch/perception/segmentation.launch.py',
            launch_arguments={
                'container_name': NVBLOX_CONTAINER_NAME,
                'people_segmentation': args.people_segmentation,
                'namespace_list': camera_namespaces,
                'input_topic_list': camera_input_topics,
                'input_camera_info_topic_list': input_camera_info_topics,
                'output_resized_image_topic_list': output_resized_image_topics,
                'output_resized_camera_info_topic_list': output_resized_camera_info_topics,
                'num_cameras': '1',
                'one_container_per_camera': 'False',
            },
            condition=IfCondition(lu.has_substring(args.mode, str(NvbloxMode.people_segmentation)))))

    # People detection
    actions.append(
        lu.include(
            'nvblox_examples_bringup',
            'launch/perception/detection.launch.py',
            launch_arguments={
                'namespace_list': camera_namespaces,
                'input_topic_list': camera_input_topics,
                'num_cameras': '1',
                'container_name': NVBLOX_CONTAINER_NAME,
                'one_container_per_camera': 'False',
            },
            condition=IfCondition(lu.has_substring(args.mode, str(NvbloxMode.people_detection)))))

    # Nvblox
    actions.append(
        lu.include(
            'nvblox_examples_bringup',
            'launch/perception/nvblox.launch.py',
            launch_arguments={
                'container_name': NVBLOX_CONTAINER_NAME,
                'mode': args.mode,
                'camera': ZED_EXAMPLE_CAMERA,
            },
        ))

    # # Play ros2bag
    # actions.append(
    #     lu.play_rosbag(
    #         bag_path=args.rosbag,
    #         additional_bag_play_args=args.rosbag_args,
    #         condition=IfCondition(lu.is_valid(args.rosbag))))

    # # Visualization
    # actions.append(
    #     lu.include(
    #         'nvblox_examples_bringup',
    #         'launch/visualization/visualization.launch.py',
    #         launch_arguments={
    #             'mode': args.mode,
    #             'camera': ZED_EXAMPLE_CAMERA,
    #         }))

    return LaunchDescription(actions)
