from ib_insync import IB
import os
import time
import random
from contextlib import contextmanager


@contextmanager
def connect_to_ib(clientId: int = None):
    """
    A context manager to handle connection to Interactive Brokers (IB) Gateway.

    Args:
        clientId (int, optional): A unique client ID for the IB connection. If not provided, a random ID is used.

    Yields:
        ib: The connected IB instance for use within the context.
    """
    ib = IB()  # Create an IB instance
    connected = False  # Track connection status
    max_retries = 5  # Maximum number of retries
    retry_count = 0  # Track how many attempts have been made

    # If no clientId is provided, generate a random clientId
    if not clientId:
        clientId = random.randint(1, 32767)

    # Retry logic for connecting to IB Gateway
    while not connected and retry_count < max_retries:
        try:
            # Attempt to connect to IB Gateway using environment variables or default values
            ib.connect(
                os.getenv(
                    "IB_GATEWAY_IP", "host.docker.internal"
                ),  # Get the gateway IP or default to localhost
                os.getenv(
                    "IB_GATEWAY_PORT", 4002
                ),  # Get the gateway port or default to 4002
                clientId=clientId,  # Use the provided or generated clientId
            )
            connected = True  # Mark as connected
            print(f"Connected with clientId {clientId}")
        except Exception as e:
            # If the connection fails, increment the clientId and retry
            print(f"ClientId {clientId} failed. Retrying with new clientId...")
            clientId += 1  # Increment the clientId to avoid duplication issues
            retry_count += 1  # Increase the retry count
            time.sleep(1)  # Wait before retrying

    # If connection fails after all retries, raise an exception
    if not connected:
        raise Exception("Failed to connect after multiple attempts.")

    try:
        yield ib  # Provide the connected IB instance for use within the context block
    finally:
        # Ensure the IB connection is properly closed at the end of the context
        if connected:
            print(f"Disconnecting clientId {clientId}")
            ib.disconnect()  # Disconnect IB instance
