import socket
import threading
import struct
import time
import logging
from enum import Enum
from colorama import Fore, Style, init

init()

MAGIC_COOKIE = 0xabcddcba
OFFER_MESSAGE_TYPE = 0x2
REQUEST_MESSAGE_TYPE = 0x3
PAYLOAD_MESSAGE_TYPE = 0x4


class ClientState(Enum):
    STARTUP = 1
    LOOKING_FOR_SERVER = 2
    SPEED_TEST = 3
    PROMPT_CONTINUE = 4


class SpeedTestClient:
    def __init__(self):
        self.state = ClientState.STARTUP
        self.running = False
        self.current_server = None
        self.broadcast_listen_port = 13118  # Port for listening to broadcast offers

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format=f'{Fore.CYAN}[%(asctime)s] %(message)s{Style.RESET_ALL}',
            datefmt='%H:%M:%S'
        )

    def start(self):
        """Start the client application"""
        self.running = True
        while self.running:
            try:
                if self.state == ClientState.STARTUP:
                    self._handle_startup()
                elif self.state == ClientState.LOOKING_FOR_SERVER:
                    self._look_for_server()
                elif self.state == ClientState.SPEED_TEST:
                    self._perform_speed_test()
                elif self.state == ClientState.PROMPT_CONTINUE:
                    self._prompt_continue()
            except KeyboardInterrupt:
                self.running = False
            except Exception as e:
                logging.error(f"Error in main loop: {e}")
                time.sleep(1)

    def _handle_startup(self):
        """Handle the startup state - get user parameters"""
        try:
            print(f"\n{Fore.GREEN}=== Client ==={Style.RESET_ALL}")
            self.file_size = int(input("Enter file size (in bytes): "))
            self.tcp_connections = int(input("Enter number of TCP connections: "))
            self.udp_connections = int(input("Enter number of UDP connections: "))
            if self.file_size <= 0 or self.tcp_connections < 0 or self.udp_connections < 0:
                raise ValueError("Invalid input values")
            self.state = ClientState.LOOKING_FOR_SERVER
            logging.info(f"{Fore.GREEN}Client started, listening for offer requests...{Style.RESET_ALL}")
        except ValueError as e:
            logging.error(f"Invalid input: {e}")
            return

    def _look_for_server(self):
        """Listen for server offers"""
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp_socket.bind(('', self.broadcast_listen_port))
        while self.state == ClientState.LOOKING_FOR_SERVER:
            try:
                data, addr = udp_socket.recvfrom(1024)
                if len(data) < 9:  # Magic cookie (4) + msg type (1) + ports (2+2)
                    continue
                magic_cookie, msg_type, udp_port, tcp_port = struct.unpack('!IbHH', data)
                if magic_cookie != MAGIC_COOKIE or msg_type != OFFER_MESSAGE_TYPE:
                    continue
                server_ip = addr[0]
                logging.info(f"{Fore.YELLOW}Received offer from {server_ip}{Style.RESET_ALL}")
                self.current_server = (server_ip, udp_port, tcp_port)
                self.state = ClientState.SPEED_TEST
                break
            except struct.error:
                # Ingore from error in udp
                continue
            except Exception as e:
                logging.error(f"Error while looking for server: {e}")
                time.sleep(1)
        udp_socket.close()

    def _perform_speed_test(self):
        """Perform the speed test with TCP and UDP connections"""
        if not self.current_server:
            self.state = ClientState.LOOKING_FOR_SERVER
            return
        server_ip, udp_port, tcp_port = self.current_server
        threads = []
        # Start TCP connections
        for i in range(self.tcp_connections):
            thread = threading.Thread(
                target=self._handle_tcp_connection,
                args=(server_ip, tcp_port, i + 1)
            )
            thread.start()
            threads.append(thread)
        # Start UDP connections
        for i in range(self.udp_connections):
            thread = threading.Thread(
                target=self._handle_udp_connection,
                args=(server_ip, udp_port, i + 1)
            )
            thread.start()
            threads.append(thread)
        # Wait for all transfers to complete
        for thread in threads:
            thread.join()
        logging.info(f"{Fore.GREEN}All transfers complete, listening to offer requests{Style.RESET_ALL}")
        self.state = ClientState.PROMPT_CONTINUE

    def _handle_tcp_connection(self, server_ip: str, tcp_port: int, connection_id: int):
        """Handle single TCP connection"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((server_ip, tcp_port))
            start_time = time.time()
            sock.send(f"{self.file_size}\n".encode())
            received = 0
            while received < self.file_size:
                chunk = sock.recv(4096)  # Efficient buffer size
                if not chunk:
                    break
                received += len(chunk)
            end_time = time.time()
            duration = end_time - start_time
            speed = (self.file_size * 8) / duration  # bits per second
            logging.info(
                f"{Fore.GREEN}TCP transfer #{connection_id} finished, "
                f"total time: {duration:.2f} seconds, "
                f"total speed: {speed:.2f} bits/second{Style.RESET_ALL}"
            )
        except Exception as e:
            logging.error(f"Error in TCP connection #{connection_id}: {e}")
        finally:
            sock.close()

    def _handle_udp_connection(self, server_ip: str, udp_port: int, connection_id: int):
        """Handle single UDP connection"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)  # Set timeout for detecting end of transfer
            # Send request
            request = struct.pack('!IbQ', MAGIC_COOKIE, REQUEST_MESSAGE_TYPE, self.file_size)
            start_time = time.time()
            sock.sendto(request, (server_ip, udp_port))
            received_segments = set()
            total_segments = None
            received_bytes = 0
            last_packet_time = time.time()
            while True:
                try:
                    data, _ = sock.recvfrom(2048)  # size for UDP
                    last_packet_time = time.time()
                    header_size = struct.calcsize('!IbQQ')
                    header = data[:header_size]
                    magic_cookie, msg_type, total_segs, current_seg = struct.unpack('!IbQQ', header)
                    if magic_cookie != MAGIC_COOKIE or msg_type != PAYLOAD_MESSAGE_TYPE:
                        continue
                    total_segments = total_segs
                    received_segments.add(current_seg)
                    received_bytes += len(data) - header_size
                    # Check if we received all segments
                    if total_segments and len(received_segments) == total_segments:
                        break
                except socket.timeout:
                    # assume transfer is complete
                    if time.time() - last_packet_time >= 1.0:
                        break
            end_time = time.time()
            duration = end_time - start_time
            speed = (received_bytes * 8) / duration  # bits per second
            success_rate = (len(received_segments) / total_segments * 100) if total_segments else 0
            logging.info(
                f"{Fore.YELLOW}UDP transfer #{connection_id} finished, "
                f"total time: {duration:.2f} seconds, "
                f"total speed: {speed:.2f} bits/second, "
                f"percentage of packets received successfully: {success_rate:.1f}%{Style.RESET_ALL}"
            )
        except Exception as e:
            logging.error(f"Error in UDP connection #{connection_id}: {e}")
        finally:
            sock.close()

    def _prompt_continue(self):
        """Ask user if they want to perform another test"""
        try:
            choice = input(f"\n{Fore.YELLOW}Do you want to perform another test? (y/n): {Style.RESET_ALL}").lower()
            if choice == 'y':
                self.state = ClientState.STARTUP
            else:
                self.running = False
        except Exception as e:
            logging.error(f"Error in prompt: {e}")
            self.running = False


if __name__ == "__main__":
    client = SpeedTestClient()
    client.start()

