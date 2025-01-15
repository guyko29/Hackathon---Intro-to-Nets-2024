import socket
import threading
import struct
import time
import logging
from typing import Tuple
from colorama import Fore, Style, init

init()

MAGIC_COOKIE = 0xabcddcba
OFFER_MESSAGE_TYPE = 0x2
REQUEST_MESSAGE_TYPE = 0x3
PAYLOAD_MESSAGE_TYPE = 0x4

class SpeedTestServer:
    def __init__(self):
        self.udp_port = 13117  # Port for client requests
        self.broadcast_port = 13118  # Port for broadcasting offers
        self.tcp_port = 12345  # Port for TCP connections
        self.running = False
        self.clients = set()
        self.ip_address = self.get_ip()
        logging.basicConfig(
            level=logging.INFO,
            format=f'{Fore.CYAN}[%(asctime)s] %(message)s{Style.RESET_ALL}',
            datefmt='%H:%M:%S'
        )

    def start(self):
        """Start the server and initialize all necessary sockets"""
        self.running = True
        # Start UDP broadcast thread
        self.broadcast_thread = threading.Thread(target=self.broadcast_offers)
        self.broadcast_thread.daemon = True
        self.broadcast_thread.start()
        # Start TCP listener
        self.tcp_thread = threading.Thread(target=self._handle_tcp_connections)
        self.tcp_thread.daemon = True
        self.tcp_thread.start()
        # Start UDP listener
        self.udp_thread = threading.Thread(target=self._handle_udp_connections)
        self.udp_thread.daemon = True
        self.udp_thread.start()
        # Get server's IP address
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        logging.info(f"""
            === Server ===
            {Fore.GREEN}Server started, listening on IP address {ip_address}{Style.RESET_ALL}
        """)

    def get_ip(self):
        """Get the server's IP address"""
        try:

            # Try to get the non-localhost IP
            # WE have done it beacuse it is a good practice to get the ip for comunication with external env
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            # Fallback to hostname
            return socket.gethostbyname(socket.gethostname())

    def broadcast_offers(self):
        """Continuously broadcast offer messages via UDP"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Prepare the offer message
        offer_message = struct.pack('!IbHH', MAGIC_COOKIE, OFFER_MESSAGE_TYPE, self.udp_port, self.tcp_port)
        while self.running:
            try:
                sock.sendto(offer_message, ('<broadcast>', self.broadcast_port))
                time.sleep(1)
            except Exception as e:
                logging.error(f"Error in broadcasting: {e}")

    def _handle_tcp_connections(self):
        """Handle incoming TCP connections"""
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.bind(('', self.tcp_port))
        tcp_socket.listen()
        while self.running:
            try:
                client_socket, addr = tcp_socket.accept()
                client_thread = threading.Thread(
                    target=self._handle_tcp_client,
                    args=(client_socket, addr)
                )
                client_thread.daemon = True
                client_thread.start()
            except Exception as e:
                logging.error(f"Error in TCP connection: {e}")

    def _handle_tcp_client(self, client_socket: socket.socket, addr: Tuple[str, int]):
        """Handle individual TCP client connections"""
        try:
            data = client_socket.recv(1024).decode() # Receive file size request from client socket
            file_size = int(data.strip())
            # Send data in efficient chunks
            chunk_size = 4096  # Efficient buffer size
            remaining = file_size
            while remaining > 0:
                send_size = min(chunk_size, remaining)
                client_socket.send(b'0' * send_size)
                remaining -= send_size
            logging.info(f"{Fore.YELLOW}TCP transfer completed for {addr}{Style.RESET_ALL}")
        except Exception as e:
            logging.error(f"Error in TCP client {addr}: {e}")
        finally:
            client_socket.close()

    def _handle_udp_connections(self):
        """Handle incoming UDP connections"""
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp_socket.bind(('', self.udp_port))
        while self.running:
            try:
                data, addr = udp_socket.recvfrom(1024)
                if len(data) < 13:  # Magic cookie (4) + msg type (1) + file size (8)
                    continue
                magic_cookie, msg_type, file_size = struct.unpack('!IbQ', data[:13]) # format for magic, msg, size
                if magic_cookie != MAGIC_COOKIE or msg_type != REQUEST_MESSAGE_TYPE:
                    continue
                udp_thread = threading.Thread(
                    target=self._handle_udp_client,
                    args=(udp_socket, addr, file_size)
                )
                udp_thread.daemon = True
                udp_thread.start()
            except struct.error:
                # Ingore from error in udp
                continue
            except Exception as e:
                logging.error(f"Error in UDP connection: {e}")

    def _handle_udp_client(self, udp_socket: socket.socket, addr: Tuple[str, int], file_size: int):
        """Handle individual UDP client requests"""
        try:
            chunk_size = 1024  # UDP size
            segments = file_size // chunk_size
            if file_size % chunk_size != 0:
                segments += 1
            for i in range(segments):
                payload_size = min(chunk_size, file_size - (i * chunk_size))
                payload = b'0' * payload_size
                header = struct.pack('!IbQQ', MAGIC_COOKIE, PAYLOAD_MESSAGE_TYPE, segments, i)
                message = header + payload
                udp_socket.sendto(message, addr)
                time.sleep(0.001)
            logging.info(f"{Fore.YELLOW}UDP transfer completed for {addr}{Style.RESET_ALL}")
        except Exception as e:
            logging.error(f"Error in UDP client {addr}: {e}")


if __name__ == "__main__":
    server = SpeedTestServer()
    server.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down server")
        server.running = False
