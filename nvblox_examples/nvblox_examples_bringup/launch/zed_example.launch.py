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

ZED_DEPTH_REGISTERED = '/zed/zed_node/depth/depth_registered'
ZED_DEPTH_TOPIC_DECOMPRESSED = f'{ZED_DEPTH_REGISTERED}/decompressed'
ZED_DEPTH_TOPIC_COMPRESSED = f'{ZED_DEPTH_REGISTERED}/compressedDepth'

ZED_COLOR_BASE = '/zed/zed_node/rgb/color/rect/image'
ZED_COLOR_COMPRESSED = f'{ZED_COLOR_BASE}/compressed'
ZED_COLOR_DECOMPRESSED = f'{ZED_COLOR_BASE}/decompressed'


def _setup_perception(context):
    lc = context.launch_configurations
    mode = lc.get('mode', str(NvbloxMode.static))
    mode_str = str(mode)
    zed_ns = 'zed'
    base_zed_rgb = f'/{zed_ns}/zed_node/rgb/color/rect/image'

    camera_namespaces = [zed_ns]
    input_camera_info_topics = [f'/{zed_ns}/zed_node/rgb/color/rect/image/camera_info']
    output_resized_image_topics = [f'/{zed_ns}/segmentation/image_resized']
    output_resized_camera_info_topics = [f'/{zed_ns}/segmentation/camera_info_resized']
    output_detection_resized_image_topics = [f'/{zed_ns}/detection/image_resized']
    output_detection_resized_camera_info_topics = [
        f'/{zed_ns}/detection/camera_info_resized']

    out = []

    if str(NvbloxMode.people_segmentation) in mode_str:
        # BGRA to RGB8 bridge (people_segmentation needs rgb8)
        zed_rgb8 = f'{base_zed_rgb}/rgb8'
        out.append(
            lu.load_composable_nodes(
                NVBLOX_CONTAINER_NAME,
                [
                    ComposableNode(
                        package='isaac_ros_image_proc',
                        plugin='nvidia::isaac_ros::image_proc::ImageFormatConverterNode',
                        name='zed_rgb8_segmentation_bridge',
                        parameters=[{
                            'encoding_desired': 'rgb8',
                            'image_width': int(lc.get('zed_seg_rgb8_width', '640')),
                            'image_height': int(lc.get('zed_seg_rgb8_height', '360')),
                        }],
                        remappings=[
                            ('image_raw', base_zed_rgb),
                            ('image', zed_rgb8),
                        ],
                    ),
                ],
            ))
        out.append(
            lu.include(
                'nvblox_examples_bringup',
                'launch/perception/segmentation.launch.py',
                launch_arguments={
                    'container_name': NVBLOX_CONTAINER_NAME,
                    'people_segmentation': lc.get(
                        'people_segmentation',
                        str(NvbloxPeopleSegmentation.peoplesemsegnet_vanilla)),
                    'namespace_list': camera_namespaces,
                    'input_topic_list': [zed_rgb8],
                    'input_camera_info_topic_list': input_camera_info_topics,
                    'output_resized_image_topic_list': output_resized_image_topics,
                    'output_resized_camera_info_topic_list': output_resized_camera_info_topics,
                    'num_cameras': '1',
                    'one_container_per_camera': 'False',
                }))

    if str(NvbloxMode.people_detection) in mode_str:
        out.append(
            lu.include(
                'nvblox_examples_bringup',
                'launch/perception/detection.launch.py',
                launch_arguments={
                    'namespace_list': camera_namespaces,
                    'input_topic_list': [base_zed_rgb],
                    'input_camera_info_topic_list': input_camera_info_topics,
                    'output_resized_image_topic_list': output_detection_resized_image_topics,
                    'output_resized_camera_info_topic_list':
                        output_detection_resized_camera_info_topics,
                    'num_cameras': '1',
                    'container_name': NVBLOX_CONTAINER_NAME,
                    'one_container_per_camera': 'False',
                }))

    nvblox_args = {
        'container_name': NVBLOX_CONTAINER_NAME,
        'mode': mode,
        'camera': ZED_EXAMPLE_CAMERA,
    }
    if str(lc.get('use_compressed', 'false')).lower() == 'true':
        nvblox_args['zed_depth_image_topic'] = ZED_DEPTH_TOPIC_DECOMPRESSED
        nvblox_args['zed_color_image_topic'] = ZED_COLOR_DECOMPRESSED
    out.append(
        lu.include(
            'nvblox_examples_bringup',
            'launch/perception/nvblox.launch.py',
            launch_arguments=nvblox_args,
        ))
    return out

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
        description='ZED: default = zed_common + zed2. low_light = zed2_low_light.yaml overlay.',
        cli=True)
    args.add_arg(
        'zed_seg_rgb8_width',
        '640',
        description='ZED rect RGB width for people_segmentation BGRA→rgb8 bridge (match zed_common output).',
        cli=True)
    args.add_arg(
        'zed_seg_rgb8_height',
        '360',
        description='ZED rect RGB height for people_segmentation BGRA→rgb8 bridge (match zed_common output).',
        cli=True)
    args.add_arg(
        'use_compressed',
        False,
        description='If true, subscribe to compressed depth and color from the network and '
        'republish as raw locally for nvblox.',
        cli=True)
    actions = args.get_launch_actions()

    # Globally set use_sim_time
    actions.append(
        SetParameter('use_sim_time', True, condition=IfCondition(lu.is_valid(args.rosbag))))

    # Navigation
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

    # zed_base_link (robot center) wrt. zed_camera_link (camera position)
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
    # actions.append(
    #     lu.include(
    #         'nvblox_examples_bringup',
    #         'launch/sensors/zed.launch.py',
    #         launch_arguments={
    #             'container_name': NVBLOX_CONTAINER_NAME,
    #             'zed_lighting': args.zed_lighting,
    #         },
    #         condition=UnlessCondition(lu.is_valid(args.rosbag))))

    actions.append(
        lu.include(
            'nvblox_examples_bringup',
            'launch/perception/fast_lio.launch.py',
            launch_arguments={
                'child_frame': 'zed_camera_link',
            },
            condition=IfCondition(lu.is_equal(args.slam, 'fast_lio'))))

    actions.append(
        Node(
            package='nvblox_examples_bringup',
            executable='depth_compressed_to_raw.py',
            name='zed_depth_decompress',
            parameters=[{
                'input_topic': ZED_DEPTH_TOPIC_COMPRESSED,
                'output_topic': ZED_DEPTH_TOPIC_DECOMPRESSED,
                'qos_preset': 'sensor_data',
            }],
            condition=IfCondition(lu.is_true(args.use_compressed)),
        ))

    actions.append(
        Node(
            package='image_transport',
            executable='republish',
            name='zed_color_decompress',
            arguments=['compressed', 'raw'],
            remappings=[
                ('in/compressed', ZED_COLOR_COMPRESSED),
                ('out', ZED_COLOR_DECOMPRESSED),
            ],
            condition=IfCondition(lu.is_true(args.use_compressed)),
        ))

    actions.append(OpaqueFunction(function=_setup_perception))

    actions.append(
        lu.play_rosbag(
            bag_path=args.rosbag,
            additional_bag_play_args=args.rosbag_args,
            condition=IfCondition(lu.is_valid(args.rosbag))))

    actions.append(
        lu.include(
            'nvblox_examples_bringup',
            'launch/visualization/visualization.launch.py',
            launch_arguments={
                'mode': args.mode,
                'camera': ZED_EXAMPLE_CAMERA,
            }))

    return LaunchDescription(actions)
