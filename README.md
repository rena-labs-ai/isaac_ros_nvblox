# Rena Isaac-Ros-Nvblox

`isaac-ros-nvblox` depends on `isaac-ros`. `isaac-ros` is tested on ros2 `jazzy`. However Rena robot is setup with Ubuntu 22 and Ros2 Humble. Hence this fork facilitate running nvblox on your laptop while communicating with rena AGX box (e.g., reading image stream, sending nav2 commands).

## Prereqruisites

- Ubuntu 24
- Ros2 Jazzy

## Setup

follow original `nvblox-isaac-ros` [readme](https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_nvblox/blob/main/README.md) to setup project.

To send a nav_goal, since nav2 publishes to a locla topic on your laptop, we need to forward it to rena robot. To do so we can use CycloneDDS to forward all topics from / to rena robot to / from our laptop (make sure you update the ip addresses in the following command):

```bash
# on both laptop and rena robot
mkdir -p ~/.cyclonedds && cat > ~/.cyclonedds/rena_robot.office.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8" ?>
<CycloneDDS xmlns="https://cdds.io/config" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="https://cdds.io/config https://raw.githubusercontent.com/eclipse-cyclonedds/cyclonedds/master/etc/cyclonedds.xsd">
    <Domain id="any">
        <General>
            <AllowMulticast>false</AllowMulticast>
            <MaxMessageSize>65500B</MaxMessageSize>
            <FragmentSize>4000B</FragmentSize>
            <Transport>udp</Transport>
        </General>
        <Discovery>
            <Peers>
                <Peer address="<ROBOT_IP_ADDRESS>"/>
                <Peer address="<LAPTOP_IP_ADDRESS>"/>
            </Peers>
            <MaxAutoParticipantIndex>100</MaxAutoParticipantIndex>
            <ParticipantIndex>auto</ParticipantIndex>
        </Discovery>
        <Internal>
            <Watermarks>
                <WhcHigh>500kB</WhcHigh>
            </Watermarks>
        </Internal>
        <Tracing>
            <Verbosity>severe</Verbosity>
            <OutputFile>stdout</OutputFile>
        </Tracing>
    </Domain>
</CycloneDDS>
EOF
```

Assuming camera connected to your laptop, launch the SLAM and mapping (cuvslam and nvblox):

```bash
# on rena robot, launch hardware
export ROS_DOMAIN_ID=42
ros2 launch rena_bringup rena_base_hardware.launch.py robot_id:=<robot-id

# on laptop
export ROS_DOMAIN_ID=42
ros2 launch nvblox_examples_bringup realsense_example.launch.py slam:=cuvslam num_cameras:=1 camera_serial_numbers:=<front_camera_serial_number> run_realsense:=True navigation:=True
```

## Fast_LIO

Since CuVSLAM does not yield accurate Odometry, one can run nvblox with FAST_LIO. 


```bash
# on rena robot, make sure hardware is already launched
export ROS_DOMAIN_ID=42
ros2 launch rena_navigation fast_lio.launch.py
# on laptop, make sure /Odometry topic is published
export ROS_DOMAIN_ID=42
ros2 topic list | grep Odometry
ros2 launch nvblox_examples_bringup realsense_example.launch.py slam:=fast_lio num_cameras:=1 camera_serial_numbers:=<front_camera_serial_number> run_realsense:=True navigation:=True
```

## MultiCamera Mode

Given the front-left-right 3D-printed rig, one can use all three cameras for both nvblox and cuVSLAM. It uses realsense builtin emitter-on-off mode to use one frame for nvblox (i.e., rgbd) and next frame for cuVSLAM (i.e., IR):

```bash
# on laptop
export ROS_DOMAIN_ID=42
ros2 launch nvblox_examples_bringup realsense_example.launch.py slam:=cuvslam num_cameras:=3 camera_serial_numbers:=<front_camera_serial_number>,<left_camera_serial_number>,<right_camera_serial_number> run_realsense:=True navigation:=True
```
