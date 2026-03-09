# Rena Isaac-Ros-Nvblox

`isaac-ros-nvblox` depends on `isaac-ros`. `isaac-ros` is tested on ros2 `jazzy`. However Rena robot is setup with Ubuntu 22 and Ros2 Humble. Hence this fork facilitate running nvblox on your laptop while communicating with rena AGX box (e.g., reading image stream, sending nav2 commands).

## Prereqruisites

- Ubuntu 24
- Ros2 Jazzy

## Setup

follow original `nvblox-isaac-ros` [readme](https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_nvblox/blob/main/README.md) to setup project.

Assuming camera connected to your laptop, launch the SLAM and mapping (cuvslam and nvblox):

```bash
# on laptop
ros2 launch nvblox_examples_bringup realsense_example.launch.py slam:=cuvslam num_cameras:=1 camera_serial_numbers:=<camera_serial_numbers> run_realsense:=True navigation:=True
```

## Fast_LIO

Since CuVSLAM does not yield accurate Odometry, one can run nvblox with FAST_LIO. First we need to forwar topics from rena robot to our laptop (make sure you update the ip addresses in the following command):

```bash
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


```bash
# on rena robot, make sure hardware is already launched
export ROS_DOMAIN_ID=42
ros2 launch rena_navigation fast_lio.launch.py
# on laptop, make sure /Odometry topic is published
export ROS_DOMAIN_ID=42
ros2 topic list | grep Odometry
ros2 launch nvblox_examples_bringup realsense_example.launch.py slam:=fast_lio num_cameras:=1 camera_serial_numbers:=<camera_serial_numbers> run_realsense:=True navigation:=True
```

## Camera Connected to Rena Robot (TODO)

One can connect cameras to Rena robot. We need to be able to see camera topics on our laptop. On Rena robot create this [camera launch file](nvblox_examples/nvblox_examples_bringup/launch/multicam.launch.py) (in rena_bringup directory), launch it, and make sure you can see camera topics on your laptop:

```bash
# on rena robot
export ROS_DOMAIN_ID=42
ros2 launch rena_bringup multicam.launch.py camera_serials:=<camera_serial_numbers>
# on laptop
export ROS_DOMAIN_ID=42
ros2 topic list | grep camera
```

Finally run SLAM and mapping:

```bash
# on laptop
export ROS_DOMAIN_ID=42
ros2 launch nvblox_examples_bringup realsense_example.launch.py slam:=cuvslam num_cameras:=1 camera_serial_numbers:=<camera_serial_numbers> run_realsense:=False navigation:=True
```
