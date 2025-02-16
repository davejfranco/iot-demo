#!/usr/bin/env python3
"""
AWS IoT Device SDK Python v2 - PubSub Sample (Modified)
This sample connects to AWS IoT, subscribes to a topic, and publishes custom messages.
"""

import argparse
import sys
import time
import json
import threading
import uuid

from awscrt import mqtt, http
from awsiot import mqtt_connection_builder

# Global variables to track received messages
received_count = 0
received_all_event = threading.Event()
global_message_count = 0  # will be set from command-line input

# Callback when connection is interrupted.
def on_connection_interrupted(connection, error, **kwargs):
    print("Connection interrupted. error: {}".format(error))

# Callback when an interrupted connection is re-established.
def on_connection_resumed(connection, return_code, session_present, **kwargs):
    print("Connection resumed. return_code: {} session_present: {}".format(return_code, session_present))
    if return_code == mqtt.ConnectReturnCode.ACCEPTED and not session_present:
        print("Session did not persist. Resubscribing to existing topics...")
        resubscribe_future, _ = connection.resubscribe_existing_topics()
        resubscribe_future.add_done_callback(on_resubscribe_complete)

def on_resubscribe_complete(resubscribe_future):
    resubscribe_results = resubscribe_future.result()
    print("Resubscribe results: {}".format(resubscribe_results))
    for topic, qos in resubscribe_results['topics']:
        if qos is None:
            sys.exit("Server rejected resubscribe to topic: {}".format(topic))

# Callback when a message is received on the subscribed topic.
def on_message_received(topic, payload, dup, qos, retain, **kwargs):
    global received_count
    print("Received message from topic '{}': {}".format(topic, payload))
    received_count += 1
    if received_count == global_message_count:
        received_all_event.set()

# Callback when the connection is successfully established.
def on_connection_success(connection, callback_data):
    print("Connection Successful with return code: {} session present: {}".format(callback_data.return_code, callback_data.session_present))

# Callback when a connection attempt fails.
def on_connection_failure(connection, callback_data):
    print("Connection failed with error code: {}".format(callback_data.error))

# Callback when the connection has been closed.
def on_connection_closed(connection, callback_data):
    print("Connection closed")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="AWS IoT Device SDK Python v2 - PubSub Sample")
    parser.add_argument('--endpoint', required=True, help="Your AWS IoT custom endpoint")
    parser.add_argument('--port', type=int, default=8883, help="Port to use (default: 8883)")
    parser.add_argument('--cert', required=True, help="Path to your certificate file")
    parser.add_argument('--key', required=True, help="Path to your private key file")
    parser.add_argument('--root-ca', required=True, help="Path to your root CA file")
    parser.add_argument('--client-id', default=str(uuid.uuid4()), help="Client ID for the connection")
    parser.add_argument('--topic', default="sdk/test/Python", help="Topic to publish/subscribe to")
    parser.add_argument('--mode', choices=['publish', 'subscribe', 'both'], default='both', help="Operation mode")
    parser.add_argument('--count', type=int, default=10, help="Number of messages to publish (if publishing)")
    parser.add_argument('--message', default="Hello World", help="Custom message to publish")
    parser.add_argument('--proxy-host', help="Optional proxy host")
    parser.add_argument('--proxy-port', type=int, default=0, help="Optional proxy port")
    parser.add_argument('--ci', action='store_true', help="Run in CI mode")
    args = parser.parse_args()

    # Set the global message count so the on_message_received callback can use it.
    global_message_count = args.count

    # Set up proxy options if provided.
    proxy_options = None
    if args.proxy_host and args.proxy_port:
        proxy_options = http.HttpProxyOptions(
            host_name=args.proxy_host,
            port=args.proxy_port)

    # Create an MQTT connection using mTLS authentication.
    mqtt_connection = mqtt_connection_builder.mtls_from_path(
        endpoint=args.endpoint,
        port=args.port,
        cert_filepath=args.cert,
        pri_key_filepath=args.key,
        ca_filepath=args.root_ca,
        client_id=args.client_id,
        clean_session=False,
        keep_alive_secs=30,
        http_proxy_options=proxy_options,
        on_connection_interrupted=on_connection_interrupted,
        on_connection_resumed=on_connection_resumed,
        on_connection_success=on_connection_success,
        on_connection_failure=on_connection_failure,
        on_connection_closed=on_connection_closed)

    if not args.ci:
        print("Connecting to {} with client ID '{}'...".format(args.endpoint, args.client_id))
    else:
        print("Connecting to endpoint with client ID")
    connect_future = mqtt_connection.connect()
    connect_future.result()
    print("Connected!")

    message_topic = args.topic
    message_count = args.count
    message_string = args.message

    # Subscribe if mode is "subscribe" or "both".
    if args.mode in ['subscribe', 'both']:
        print("Subscribing to topic '{}'...".format(message_topic))
        subscribe_future, packet_id = mqtt_connection.subscribe(
            topic=message_topic,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=on_message_received)
        subscribe_result = subscribe_future.result()
        print("Subscribed with QoS: {}".format(subscribe_result['qos']))

    # Publish if mode is "publish" or "both" and if a message is provided.
    if args.mode in ['publish', 'both'] and message_string:
        if message_count == 0:
            print("Sending messages until program is terminated")
        else:
            print("Sending {} message(s)".format(message_count))
        
        publish_count = 1
        while (publish_count <= message_count) or (message_count == 0):
            # Create a message by appending the count.
            message = "{} [{}]".format(message_string, publish_count)
            message_json = json.dumps(message)
            print("Publishing message to topic '{}': {}".format(message_topic, message))
            mqtt_connection.publish(
                topic=message_topic,
                payload=message_json,
                qos=mqtt.QoS.AT_LEAST_ONCE)
            time.sleep(1)
            publish_count += 1

    # Wait for all messages to be received if a finite count was specified.
    if message_count != 0 and not received_all_event.is_set():
        print("Waiting for all messages to be received...")
    received_all_event.wait()
    print("{} message(s) received.".format(received_count))

    print("Disconnecting...")
    disconnect_future = mqtt_connection.disconnect()
    disconnect_future.result()
    print("Disconnected!")
