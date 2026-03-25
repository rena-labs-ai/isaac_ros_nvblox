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

from typing import List

from isaac_ros_launch_utils.all_types import *
import isaac_ros_launch_utils as lu

from nvblox_ros_python_utils.nvblox_launch_utils import NvbloxCamera
from nvblox_ros_python_utils.nvblox_constants import NVBLOX_CONTAINER_NAME


def get_realsense_remappings(num_cameras: int) -> list:
    remappings = []
    for i in range(num_cameras):
        remappings.append(
            (f'visual_slam/camera_info_{2*i}', f'/camera{i}/infra1/camera_info'))
        remappings.append(
            (f'visual_slam/camera_info_{2*i+1}', f'/camera{i}/infra2/camera_info'))
        if i == 0:
            remappings.append(
                (f'visual_slam/image_{2*i}',
                 f'/camera{i}/realsense_splitter_node/output/infra_1'))
            remappings.append(
                (f'visual_slam/image_{2*i+1}',
                 f'/camera{i}/realsense_splitter_node/output/infra_2'))
        else:
            remappings.append(
                (f'visual_slam/image_{2*i}', f'/camera{i}/infra1/image_rect_raw'))
            remappings.append(
                (f'visual_slam/image_{2*i+1}', f'/camera{i}/infra2/image_rect_raw'))
    return remappings


def get_realsense_optical_frames(num_cameras: int) -> list:
    frames = []
    for i in range(num_cameras):
        frames.append(f'camera{i}_infra1_optical_frame')
        frames.append(f'camera{i}_infra2_optical_frame')
    return frames


def add_vslam(args: lu.ArgumentContainer) -> List[Action]:
    actions = []

    camera = NvbloxCamera[args.camera]
    num_cameras = int(args.num_cameras)
    num_images = 2 * num_cameras

    if camera is NvbloxCamera.realsense:
        base_frame = 'camera0_link'
    else:
        base_frame = 'base_link'

    actions.append(lu.log_info(
        f'Starting cuVSLAM with {num_cameras} camera(s), base_frame: {base_frame}'))

    base_parameters = {
        'num_cameras': num_images,
        'min_num_images': num_images,
        'enable_localization_n_mapping': False,
        'gyro_noise_density': 0.000244,
        'gyro_random_walk': 0.000019393,
        'accel_noise_density': 0.001862,
        'accel_random_walk': 0.003,
        'calibration_frequency': 200.0,
        'rig_frame': 'base_link',
        'imu_frame': 'front_stereo_camera_imu',
        'enable_slam_visualization': True,
        'enable_landmarks_view': True,
        'enable_observations_view': True,
        'path_max_size': 200,
        'verbosity': 5,
        'enable_debug_mode': False,
        'debug_dump_path': '/tmp/cuvslam',
        'map_frame': 'map',
        'odom_frame': 'odom',
        'base_frame': base_frame,
    }
    realsense_parameters = {
        'enable_rectified_pose': True,
        'enable_image_denoising': False,
        'rectified_images': True,
        'imu_frame': 'camera0_gyro_optical_frame',
        'camera_optical_frames': get_realsense_optical_frames(num_cameras),
    }

    if camera is NvbloxCamera.realsense or camera is NvbloxCamera.multi_realsense:
        remappings = get_realsense_remappings(num_cameras)
        camera_parameters = realsense_parameters
    else:
        raise Exception(f'Camera {camera} not implemented for vslam.')

    parameters = []
    parameters.append(base_parameters)
    parameters.append(camera_parameters)
    parameters.append(
        {'enable_ground_constraint_in_odometry': args.enable_ground_constraint_in_odometry})
    parameters.append({'enable_imu_fusion': args.enable_imu_fusion})

    vslam_node = ComposableNode(
        name='visual_slam_node',
        package='isaac_ros_visual_slam',
        plugin='nvidia::isaac_ros::visual_slam::VisualSlamNode',
        remappings=remappings,
        parameters=parameters)
    actions.append(lu.load_composable_nodes(args.container_name, [vslam_node]))

    if args.run_standalone:
        actions.append(lu.component_container(args.container_name))

    return actions


def generate_launch_description() -> LaunchDescription:
    args = lu.ArgumentContainer()
    args.add_arg('camera')
    args.add_arg('num_cameras', 1)
    args.add_arg(
        'enable_ground_constraint_in_odometry',
        'False',
        description='Whether to constraint robot movement to a 2d plane (e.g. for AMRs).',
        cli=True)
    args.add_arg(
        'enable_imu_fusion',
        'False',
        description='Whether to use imu data in visual slam.',
        cli=True)
    args.add_arg('container_name', NVBLOX_CONTAINER_NAME)
    args.add_arg('run_standalone', 'False')
    args.add_opaque_function(add_vslam)
    return LaunchDescription(args.get_launch_actions())
