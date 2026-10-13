import os
import socket
from datetime import datetime

class SocketServer:
    def __init__(self):
        self.bufsize = 1024
        with open('./response.bin', 'rb') as file:
            self.RESPONSE = file.read()

        self.DIR_PATH = './request'
        self.createDir(self.DIR_PATH)

    def createDir(self, path):
        try:
            if not os.path.exists(path):
                os.makedirs(path)
        except OSError:
            print("Error: Failed to create the directory.")

    def recv_request(self, clnt_sock):
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = clnt_sock.recv(self.bufsize)
            if not chunk:
                return data
            data += chunk

        header_end = data.index(b"\r\n\r\n") + 4
        header_text = data[:header_end].decode("utf-8", errors="replace")

        content_length = 0
        for line in header_text.split("\r\n"):
            if line.lower().startswith("content-length:"):
                content_length = int(line.split(":", 1)[1].strip())

        while len(data) - header_end < content_length:
            chunk = clnt_sock.recv(self.bufsize)
            if not chunk:
                break
            data += chunk
        return data

    def save_request(self, data, timestamp):
        path = os.path.join(self.DIR_PATH, timestamp + ".bin")
        with open(path, "wb") as f:
            f.write(data)
        print(f"Saved request: {path}")

    def run(self, ip, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((ip, port))
        self.sock.listen(10)
        print("Start the socket server...")
        print("\"Ctrl+C\" for stopping the server!\r\n")

        try:
            while True:
                clnt_sock, req_addr = self.sock.accept()
                clnt_sock.settimeout(5.0)
                print("Request message...\r\n")

                try:
                    data = self.recv_request(clnt_sock)
                    if data:
                        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                        self.save_request(data, timestamp)
                except socket.timeout:
                    print("Timeout while receiving request.")

                clnt_sock.sendall(self.RESPONSE)
                clnt_sock.close()
        except KeyboardInterrupt:
            print("\r\nStop the server...")

        self.sock.close()

if __name__ == "__main__":
    server = SocketServer()
    server.run("0.0.0.0", 9000)