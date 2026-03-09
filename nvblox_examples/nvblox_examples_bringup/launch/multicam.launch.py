"""Launch RealSense cameras for multicam rig.

Topics per camera (i = index in serials list):
  /camera{i}/color/image_raw
  /camera{i}/color/camera_info
  /camera{i}/depth/camera_info
  /camera{i}/realsense_splitter_node/output/depth  (remapped from depth/image_rect_raw)

Usage:
  ros2 launch rena_bringup multicam.launch.py
  ros2 launch rena_bringup multicam.launch.py camera_serials:="339522301389,242422303248,146222250568"
"""

import os
import tempfile
import yaml

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    OpaqueFunction,
)
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import SetRemap
from launch_ros.substitutions import FindPackageShare

DEFAULT_CAMERA_SERIALS = "339522301389,242422303248"


def _launch_cameras(context, *args, **kwargs):
    serials_str = LaunchConfiguration("camera_serials").perform(context)
    serials = [s.strip() for s in serials_str.split(",") if s.strip()]
    if not serials:
        raise ValueError("camera_serials must contain at least one serial number")

    config_dir = os.path.join(tempfile.gettempdir(), "rena_configs")
    os.makedirs(config_dir, exist_ok=True)

    nodes = []
    for i, serial in enumerate(serials):
        config_path = os.path.join(config_dir, f"realsense_multicam_{serial}.yaml")
        with open(config_path, "w") as f:
            yaml.dump({"serial_no": serial}, f, default_flow_style=False)

        cam = f"camera{i}"
        nodes.append(
            GroupAction([
                SetRemap(
                    src=f"/{cam}/depth/image_rect_raw",
                    dst=f"/{cam}/realsense_splitter_node/output/depth",
                ),
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource(
                        [FindPackageShare("realsense2_camera"), "/launch/rs_launch.py"]
                    ),
                    launch_arguments={
                        "camera_namespace": "",
                        "camera_name": cam,
                        "config_file": config_path,
                        # RGB
                        "rgb_camera.color_profile": "640x480x15",
                        "rgb_camera.profile": "640x480x15",
                        "color_info_qos": "SENSOR_DATA",
                        "color_qos": "SENSOR_DATA",
                        # Depth
                        "depth_module.depth_profile": "640x480x30",
                        "depth_module.infra_profile": "1280x800x30",
                        "depth_module.profile": "640x480x30",
                        "depth_module.emitter_enabled": "1",
                        "depth_module.emitter_on_off": "false",
                        "depth_qos": "SENSOR_DATA",
                        "depth_info_qos": "SENSOR_DATA",
                        # Infra
                        "infra_qos": "SENSOR_DATA",
                        # Stream toggles
                        "enable_accel": "false",
                        "enable_color": "false",
                        "enable_depth": "false",
                        "enable_gyro": "false",
                        "enable_infra1": "true",
                        "enable_infra2": "true",
                        # Pointcloud
                        "pointcloud.enable": "false",
                        "pointcloud_texture_index": "0",
                        "pointcloud_texture_stream": "RS2_STREAM_ANY",
                        # Sync / align
                        "enable_sync": "false",
                        "align_depth.enable": "false",
                        # IMU
                        "gyro_fps": "200",
                        "accel_fps": "200",
                        "unite_imu_method": "2",
                    }.items(),
                ),
            ])
        )
    return nodes


def generate_launch_description():
    camera_serials_arg = DeclareLaunchArgument(
        "camera_serials",
        default_value=DEFAULT_CAMERA_SERIALS,
        description="Comma-separated serial numbers (e.g. 339522301389,242422303248)",
    )
    return LaunchDescription([
        camera_serials_arg,
        OpaqueFunction(function=_launch_cameras),
    ])
