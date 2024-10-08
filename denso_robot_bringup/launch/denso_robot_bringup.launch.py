# Copyright 2021 Stogl Robotics Consulting UG (haftungsbeschränkt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch.launch_description_sources import PythonLaunchDescriptionSource

from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

from ament_index_python.packages import get_package_share_directory

import xacro

def generate_launch_description():
    # Declare arguments
    declared_arguments = []
    declared_arguments.append(
        DeclareLaunchArgument(
            "namespace",
            default_value="/",
            description="Namespace of controller manager and controllers. This is useful for \
        multi-robot scenarios.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "runtime_config_package",
            default_value="denso_robot_bringup",
            description='Package with the controller\'s configuration in "config" folder. \
        Usually the argument is not set, it enables use of a custom setup.',
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "controllers_file",
            default_value="denso_robot_controllers.yaml",
            description="YAML file with the controllers configuration.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "description_package",
            default_value="denso_robot_description",
            description="Description package with robot URDF/xacro files. Usually the argument \
        is not set, it enables use of a custom description.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "description_file",
            default_value="denso_robot.urdf.xacro",
            description="URDF/XACRO description file with the robot.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "prefix",
            default_value='""',
            description="Prefix of the joint names, useful for \
        multi-robot setup. If changed than also joint names in the controllers' configuration \
        have to be updated.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "sim_gazebo",
            default_value="false",
            description="Start robot in Gazebo simulation.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "robot_ip",
            default_value="192.168.0.13",
            description="The Denso Controller IP Address. Default is 192.168.0.1. \
                You can change it to control multy robots.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "robot_port",
            default_value="5007",
            description="The Denso Controller Port. Default is 5007.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "controller_manager_name",
            default_value="/controller_manager",
            description="Full name of the controller manager. This values should be set if \
        controller manager is used under a namespace.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "robot_controller",
            default_value="trajectory_controller",
            description="Robot controller to start.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "start_rviz",
            default_value="false",
            description="Start RViz2 automatically with this launch file.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "denso_config_package",
            default_value="denso_robot_core",
            description="Denso Controller package.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "denso_config_file",
            default_value="config.xml",
            description="Control cmd for denso.",
        )
    )
    # Initialize Arguments
    namespace = LaunchConfiguration("namespace")
    runtime_config_package = LaunchConfiguration("runtime_config_package")
    controllers_file = LaunchConfiguration("controllers_file")
    description_package = LaunchConfiguration("description_package")
    description_file = LaunchConfiguration("description_file")
    denso_config_package = LaunchConfiguration("denso_config_package")
    denso_config_file = LaunchConfiguration("denso_config_file")
    prefix = LaunchConfiguration("prefix")
    robot_ip = LaunchConfiguration("robot_ip")
    robot_port = LaunchConfiguration("robot_port")
    sim_gazebo = LaunchConfiguration("sim_gazebo")
    controller_manager_name = LaunchConfiguration("controller_manager_name")
    robot_controller = LaunchConfiguration("robot_controller")
    start_rviz = LaunchConfiguration("start_rviz")

    # Get URDF via xacro
    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution(
                [FindPackageShare(description_package), "urdf", description_file]
            ),
            " ",
            "prefix:=",
            prefix,
            " ",
            "sim_gazebo:=",
            sim_gazebo,
            " ",
            "robot_ip:=",
            robot_ip,
            " "
            "robot_port:=",
            robot_port,
            " "
            "config_file:=",
            PathJoinSubstitution(
                [FindPackageShare(denso_config_package), "config", denso_config_file]
            ),
            " ",
        ]
    )
    robot_description = {"robot_description": robot_description_content}

    robot_controllers = PathJoinSubstitution(
        [
            FindPackageShare(runtime_config_package),
            "config",
            controllers_file,
        ]
    )
    rviz_config_file = PathJoinSubstitution(
        [FindPackageShare(description_package), "config", "rrbot.rviz"]
    )

    control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[robot_description, robot_controllers],
        namespace=namespace,
        prefix=['stdbuf -o L'],
        output="both",
        condition=IfCondition(PythonExpression(["'", sim_gazebo, "' == 'false'"])),
    )

    robot_state_pub_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        namespace=namespace,
        output="both",
        parameters=[robot_description],
    )
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        namespace=namespace,
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config_file],
        condition=IfCondition(start_rviz),
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        namespace=namespace,
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", controller_manager_name],
    )

    robot_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        namespace=namespace,
        arguments=[robot_controller, "-c", controller_manager_name],
    )

    # Gazebo
    gz_ros2_control_demos_path = os.path.join(
        get_package_share_directory('denso_robot_description'))

    xacro_file = os.path.join(gz_ros2_control_demos_path, "urdf", "denso_robot.urdf.xacro")

    doc = xacro.parse(open(xacro_file))
    xacro.process_doc(doc)
    
    gazebo_node = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                [os.path.join(get_package_share_directory('ros_gz_sim'),
                              'launch', 'gz_sim.launch.py')]),
            launch_arguments=[('gz_args', [' -r -v 4 empty.sdf'])],
            condition=IfCondition(sim_gazebo),
    )

    gz_spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=['-string', doc.toxml(),
                   '-name', 'Denso',
                   '-allow_renaming', 'true'],
        condition=IfCondition(sim_gazebo),
    )

    # Delay rviz start after `joint_state_broadcaster`
    delay_rviz_after_joint_state_broadcaster_spawner = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[rviz_node],
        )
    )

    # Delay start of robot_controller after `joint_state_broadcaster`
    delay_robot_controller_spawner_after_joint_state_broadcaster_spawner = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[robot_controller_spawner],
        )
    )

    nodes = [
        control_node,
        robot_state_pub_node,
        joint_state_broadcaster_spawner,
        delay_rviz_after_joint_state_broadcaster_spawner,
        delay_robot_controller_spawner_after_joint_state_broadcaster_spawner,
        # For Gazebo
        gazebo_node,
        gz_spawn_entity,
    ]

    return LaunchDescription(declared_arguments + nodes)
