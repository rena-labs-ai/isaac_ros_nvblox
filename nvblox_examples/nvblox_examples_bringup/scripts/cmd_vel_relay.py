#!/usr/bin/env python3
"""Relays Twist messages from one topic to another."""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


class CmdVelRelay(Node):

    def __init__(self):
        super().__init__('cmd_vel_relay')
        self.declare_parameter('input_topic', '/cmd_vel_nav')
        self.declare_parameter('output_topic', '/drive_controller/cmd_vel_unstamped')

        input_topic = self.get_parameter('input_topic').value
        output_topic = self.get_parameter('output_topic').value

        self._pub = self.create_publisher(Twist, output_topic, 10)
        self.create_subscription(Twist, input_topic, self._callback, 10)
        self.get_logger().info(f'Relaying {input_topic} -> {output_topic}')

    def _callback(self, msg: Twist):
        self._pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = CmdVelRelay()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
