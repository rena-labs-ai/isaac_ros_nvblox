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

import isaac_ros_launch_utils.all_types as lut
import isaac_ros_launch_utils as lu

from nvblox_ros_python_utils.nvblox_launch_utils import NvbloxMode
from nvblox_ros_python_utils.nvblox_constants import NVBLOX_CONTAINER_NAME

# Use separate container for Nav2 to avoid overloading nvblox_container (ZED/nvblox)
# when running navigation launch separately from sensor/mapping launch
NAV2_CONTAINER_NAME = 'nav2_container'


def add_nvblox_carter_navigation(args: lu.ArgumentContainer) -> List[lut.Action]:
    # Nav2 base parameter file
    actions = []
    nav_config = args.nav_config
    nav_params_path = lu.get_path('nvblox_examples_bringup', f'config/navigation/{nav_config}')
    actions.append(lut.SetParametersFromFile(str(nav_params_path)))
    actions.append(lut.SetParameter('use_sim_time', False))
    # Enabling nav2
    actions.append(
        lu.set_parameter(
            namespace='/local_costmap/local_costmap',
            parameter='plugins',
            value=['nvblox_layer', 'inflation_layer'],
        ))
    actions.append(
        lu.set_parameter(
            namespace='/global_costmap/global_costmap',
            parameter='plugins',
            value=['nvblox_layer', 'inflation_layer'],
        ))

    # Modifying nav2 parameters depending on nvblox mode
    mode = NvbloxMode[args.mode]
    if mode is NvbloxMode.static:
        costmap_topic_name = '/nvblox_node/static_map_slice'
    elif mode in [NvbloxMode.dynamic, NvbloxMode.people_segmentation]:
        costmap_topic_name = '/nvblox_node/combined_map_slice'
    else:
        raise Exception(f'Navigation in mode {mode} not implemented.')

    actions.append(
        lu.set_parameter(
            namespace='/global_costmap/global_costmap',
            parameter='nvblox_layer.nvblox_map_slice_topic',
            value=costmap_topic_name,
        ))
    actions.append(
        lu.set_parameter(
            namespace='/local_costmap/local_costmap',
            parameter='nvblox_layer.nvblox_map_slice_topic',
            value=costmap_topic_name,
        ))

    # Nav2 runs in its own container to avoid overloading nvblox_container when
    # launched separately (e.g. ZED + nvblox in one terminal, Nav2 in another)
    actions.append(lu.component_container(NAV2_CONTAINER_NAME))
    actions.append(
        lu.include(
            'nav2_bringup',
            'launch/navigation_launch.py',
            launch_arguments={
                'params_file': str(nav_params_path),
                'container_name': NAV2_CONTAINER_NAME,
                'use_composition': 'True',
                'use_sim_time': 'False',
            },
        ))
    # ZED publishes map->odom from its SLAM; other configs need static transform
    if nav_config != 'zed_nav2.yaml':
        actions.append(lu.static_transform('map', 'odom'))

    actions.append(
        lut.Node(
            package='nvblox_examples_bringup',
            executable='cmd_vel_relay.py',
            name='cmd_vel_relay',
            output='screen',
        ))

    return actions


def generate_launch_description() -> lut.LaunchDescription:
    args = lu.ArgumentContainer()
    args.add_arg('mode')
    args.add_arg('container_name', NVBLOX_CONTAINER_NAME)
    args.add_arg(
        'nav_config', 'carter_nav2.yaml',
        description='Nav2 config file: carter_nav2.yaml, rena_nav2.yaml, or zed_nav2.yaml',
        cli=True)

    args.add_opaque_function(add_nvblox_carter_navigation)
    return lut.LaunchDescription(args.get_launch_actions())
