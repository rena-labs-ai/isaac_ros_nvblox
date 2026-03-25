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

from launch import Action
from isaac_ros_launch_utils.all_types import *
import isaac_ros_launch_utils as lu

from nvblox_ros_python_utils.nvblox_constants import NVBLOX_CONTAINER_NAME

ZED_CAMERA_NAME = 'zed'
ZED_MODEL = 'zed2'

_ZED_LIGHTING_PRESETS = ('default', 'low_light')


def add_zed_camera(evaluated_args) -> List[Action]:
    container_name = str(evaluated_args.container_name)
    config_file_camera = lu.get_path('nvblox_examples_bringup', 'config/sensors/zed2.yaml')
    config_file_common = lu.get_path('nvblox_examples_bringup', 'config/sensors/zed_common.yaml')

    lighting = str(evaluated_args.zed_lighting).strip().lower()
    if lighting not in _ZED_LIGHTING_PRESETS:
        raise ValueError(
            f'zed_lighting must be one of {_ZED_LIGHTING_PRESETS}, got {evaluated_args.zed_lighting!r}'
        )

    parameters_files = [str(config_file_common), str(config_file_camera)]
    if lighting == 'low_light':
        parameters_files.append(
            str(
                lu.get_path(
                    'nvblox_examples_bringup', 'config/sensors/zed2_low_light.yaml')))

    zed_node = ComposableNode(
        package='zed_components',
        namespace=ZED_CAMERA_NAME,
        name='zed_node',
        plugin='stereolabs::ZedCamera',
        parameters=parameters_files + [{'general.camera_name': ZED_CAMERA_NAME}])

    actions: List[Action] = []
    if lu.is_true(evaluated_args.run_standalone):
        actions.append(lu.component_container(container_name))
    actions.append(lu.load_composable_nodes(container_name, [zed_node]))
    return actions


def generate_launch_description() -> LaunchDescription:
    args = lu.ArgumentContainer()
    args.add_arg('container_name', NVBLOX_CONTAINER_NAME)
    args.add_arg('run_standalone', 'False')
    args.add_arg(
        'zed_lighting',
        'default',
        description='default: zed_common + zed2. low_light: append zed2_low_light.yaml (see cuVSLAM TROUBLESHOOTING).')
    args.add_opaque_function(add_zed_camera)

    xacro_path = lu.get_path('zed_wrapper', 'urdf/zed_descr.urdf.xacro')
    actions: List[Action] = [
        Node(
            package='robot_state_publisher',
            namespace=ZED_CAMERA_NAME,
            executable='robot_state_publisher',
            name='zed_state_publisher',
            output='screen',
            parameters=[{
                'robot_description': Command([
                    'xacro',
                    ' ',
                    str(xacro_path),
                    ' ',
                    'camera_name:=',
                    ZED_CAMERA_NAME,
                    ' ',
                    'camera_model:=',
                    ZED_MODEL,
                ])
            }]),
    ]
    actions.extend(args.get_launch_actions())
    return LaunchDescription(actions)
